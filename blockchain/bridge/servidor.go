// Package main implementa el puente entre la aplicación Python y Hyperledger Fabric (ADR-002).
//
// Expone una API REST mínima solo en 127.0.0.1, protegida con un token local:
//
//	GET  /salud                       estado del puente (sin token)
//	POST /tx/{funcion}                envía un hito al chaincode (cuerpo: argumentos JSON)
//	GET  /mesa/{global}/{mesa}        estado anclado de una mesa
//	GET  /historial/{global}/{mesa}   versiones del estado con su transacción
package main

import (
	"context"
	"crypto/subtle"
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"strings"
	"time"
)

// Ledger abstrae Fabric para poder probar el servidor sin una red real.
type Ledger interface {
	Enviar(ctx context.Context, funcion, argsJSON string) (txID string, err error)
	Consultar(ctx context.Context, funcion string, args ...string) ([]byte, error)
}

var (
	// ErrRechazado: el chaincode rechazó el hito (incoherente con lo ya anclado). HTTP 409.
	ErrRechazado = errors.New("rechazado por el chaincode")
	// ErrNoDisponible: Fabric no responde (modo degradado). HTTP 503.
	ErrNoDisponible = errors.New("fabric no disponible")
	// ErrNoEncontrado: la mesa no está registrada en el ledger. HTTP 404.
	ErrNoEncontrado = errors.New("no encontrado")
)

// Funciones del chaincode que se pueden invocar por /tx (lista blanca).
var funcionesPermitidas = map[string]bool{
	"RegistrarEleccion": true, "RegistrarApertura": true, "RegistrarCheckpoint": true,
	"RegistrarCierre": true, "RegistrarEscrutinio": true, "RegistrarExportacion": true,
}

const tamanioMaximo = 64 << 10 // 64 KiB por solicitud

// Servidor atiende la API REST del puente.
type Servidor struct {
	ledger  Ledger
	token   []byte
	timeout time.Duration
}

// NuevoServidor crea el servidor con el token compartido con la aplicación.
func NuevoServidor(ledger Ledger, token string) *Servidor {
	return &Servidor{ledger: ledger, token: []byte(token), timeout: 90 * time.Second}
}

// Rutas devuelve el enrutador HTTP.
func (s *Servidor) Rutas() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /salud", func(w http.ResponseWriter, _ *http.Request) {
		responder(w, http.StatusOK, map[string]string{"estado": "ok"})
	})
	mux.HandleFunc("POST /tx/{funcion}", s.autenticado(s.enviar))
	mux.HandleFunc("GET /mesa/{global}/{mesa}", s.autenticado(s.consultar("ConsultarMesa")))
	mux.HandleFunc("GET /historial/{global}/{mesa}", s.autenticado(s.consultar("ConsultarHistorial")))
	return mux
}

func (s *Servidor) autenticado(siguiente http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		recibido := []byte(strings.TrimPrefix(r.Header.Get("Authorization"), "Bearer "))
		if subtle.ConstantTimeCompare(recibido, s.token) != 1 {
			responder(w, http.StatusUnauthorized, map[string]string{"error": "token inválido"})
			return
		}
		siguiente(w, r)
	}
}

func (s *Servidor) enviar(w http.ResponseWriter, r *http.Request) {
	funcion := r.PathValue("funcion")
	if !funcionesPermitidas[funcion] {
		responder(w, http.StatusNotFound, map[string]string{"error": "función no permitida: " + funcion})
		return
	}
	cuerpo, err := io.ReadAll(http.MaxBytesReader(w, r.Body, tamanioMaximo))
	var objeto map[string]any
	if err != nil || json.Unmarshal(cuerpo, &objeto) != nil {
		responder(w, http.StatusBadRequest, map[string]string{"error": "se esperaba un objeto JSON"})
		return
	}
	ctx, cancelar := context.WithTimeout(r.Context(), s.timeout)
	defer cancelar()
	txID, err := s.ledger.Enviar(ctx, funcion, string(cuerpo))
	if err != nil {
		responderError(w, funcion, err)
		return
	}
	log.Printf("%s confirmada (tx %s)", funcion, txID)
	responder(w, http.StatusOK, map[string]string{"tx_id": txID})
}

func (s *Servidor) consultar(funcion string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ctx, cancelar := context.WithTimeout(r.Context(), 15*time.Second)
		defer cancelar()
		datos, err := s.ledger.Consultar(ctx, funcion, r.PathValue("global"), r.PathValue("mesa"))
		if err != nil {
			responderError(w, funcion, err)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write(datos)
	}
}

func responderError(w http.ResponseWriter, funcion string, err error) {
	codigo := http.StatusBadGateway
	switch {
	case errors.Is(err, ErrNoEncontrado):
		codigo = http.StatusNotFound
	case errors.Is(err, ErrRechazado):
		codigo = http.StatusConflict
	case errors.Is(err, ErrNoDisponible):
		codigo = http.StatusServiceUnavailable
	}
	log.Printf("%s falló (%d): %v", funcion, codigo, err)
	responder(w, codigo, map[string]string{"error": err.Error()})
}

func responder(w http.ResponseWriter, codigo int, cuerpo any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(codigo)
	_ = json.NewEncoder(w).Encode(cuerpo)
}
