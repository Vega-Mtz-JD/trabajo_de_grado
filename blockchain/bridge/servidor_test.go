package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

const tokenPrueba = "0123456789abcdef0123456789abcdef"

type ledgerFalso struct {
	errEnviar error
	enviados  []string
}

func (l *ledgerFalso) Enviar(_ context.Context, funcion, args string) (string, error) {
	if l.errEnviar != nil {
		return "", l.errEnviar
	}
	l.enviados = append(l.enviados, funcion+" "+args)
	return "tx-123", nil
}

func (l *ledgerFalso) Consultar(_ context.Context, funcion string, args ...string) ([]byte, error) {
	if args[1] == "99" {
		return nil, fmt.Errorf("%w: la mesa 99 no está registrada", ErrNoEncontrado)
	}
	return []byte(`{"funcion":"` + funcion + `","mesa":"` + args[1] + `"}`), nil
}

func solicitar(t *testing.T, s *Servidor, metodo, ruta, cuerpo, token string) (int, map[string]any) {
	t.Helper()
	r := httptest.NewRequest(metodo, ruta, strings.NewReader(cuerpo))
	if token != "" {
		r.Header.Set("Authorization", "Bearer "+token)
	}
	w := httptest.NewRecorder()
	s.Rutas().ServeHTTP(w, r)
	var respuesta map[string]any
	_ = json.Unmarshal(w.Body.Bytes(), &respuesta)
	return w.Code, respuesta
}

func TestSaludSinToken(t *testing.T) {
	codigo, r := solicitar(t, NuevoServidor(&ledgerFalso{}, tokenPrueba), "GET", "/salud", "", "")
	if codigo != http.StatusOK || r["estado"] != "ok" {
		t.Fatalf("salud: %d %v", codigo, r)
	}
}

func TestTokenObligatorio(t *testing.T) {
	s := NuevoServidor(&ledgerFalso{}, tokenPrueba)
	for _, token := range []string{"", "incorrecto"} {
		if codigo, _ := solicitar(t, s, "POST", "/tx/RegistrarApertura", `{}`, token); codigo != http.StatusUnauthorized {
			t.Fatalf("token %q: se esperaba 401, se obtuvo %d", token, codigo)
		}
	}
}

func TestEnviarTransaccion(t *testing.T) {
	ledger := &ledgerFalso{}
	s := NuevoServidor(ledger, tokenPrueba)
	codigo, r := solicitar(t, s, "POST", "/tx/RegistrarCheckpoint", `{"seq":1}`, tokenPrueba)
	if codigo != http.StatusOK || r["tx_id"] != "tx-123" || ledger.enviados[0] != `RegistrarCheckpoint {"seq":1}` {
		t.Fatalf("envío: %d %v %v", codigo, r, ledger.enviados)
	}
}

func TestFuncionNoPermitidaYCuerpoInvalido(t *testing.T) {
	s := NuevoServidor(&ledgerFalso{}, tokenPrueba)
	if codigo, _ := solicitar(t, s, "POST", "/tx/ConsultarMesa", `{}`, tokenPrueba); codigo != http.StatusNotFound {
		t.Fatalf("función no permitida: %d", codigo)
	}
	for _, cuerpo := range []string{"no-json", "[1,2]", strings.Repeat("x", tamanioMaximo+1)} {
		if codigo, _ := solicitar(t, s, "POST", "/tx/RegistrarCierre", cuerpo, tokenPrueba); codigo != http.StatusBadRequest {
			t.Fatalf("cuerpo %.10q: se esperaba 400, se obtuvo %d", cuerpo, codigo)
		}
	}
}

func TestClasificacionDeErrores(t *testing.T) {
	casos := map[error]int{
		fmt.Errorf("%w: el cierre no coincide", ErrRechazado): http.StatusConflict,
		fmt.Errorf("%w: conexión rechazada", ErrNoDisponible):  http.StatusServiceUnavailable,
		fmt.Errorf("otro error"):                              http.StatusBadGateway,
	}
	for err, esperado := range casos {
		s := NuevoServidor(&ledgerFalso{errEnviar: err}, tokenPrueba)
		codigo, r := solicitar(t, s, "POST", "/tx/RegistrarCierre", `{}`, tokenPrueba)
		if codigo != esperado || !strings.Contains(r["error"].(string), strings.SplitN(err.Error(), ":", 2)[0]) {
			t.Fatalf("%v: se esperaba %d, se obtuvo %d (%v)", err, esperado, codigo, r)
		}
	}
}

func TestConsultas(t *testing.T) {
	s := NuevoServidor(&ledgerFalso{}, tokenPrueba)
	codigo, r := solicitar(t, s, "GET", "/mesa/abc/01", "", tokenPrueba)
	if codigo != http.StatusOK || r["funcion"] != "ConsultarMesa" || r["mesa"] != "01" {
		t.Fatalf("mesa: %d %v", codigo, r)
	}
	if codigo, r = solicitar(t, s, "GET", "/historial/abc/02", "", tokenPrueba); r["funcion"] != "ConsultarHistorial" {
		t.Fatalf("historial: %d %v", codigo, r)
	}
	if codigo, _ = solicitar(t, s, "GET", "/mesa/abc/99", "", tokenPrueba); codigo != http.StatusNotFound {
		t.Fatalf("mesa inexistente: %d", codigo)
	}
}

func TestClasificarErroresDeFabric(t *testing.T) {
	if err := clasificar(fmt.Errorf("validación: se requiere ABIERTA")); !strings.Contains(err.Error(), ErrRechazado.Error()) {
		t.Fatalf("validación → rechazado: %v", err)
	}
	if err := clasificar(fmt.Errorf("validación: la mesa 01 de la elección x no está registrada")); !strings.Contains(err.Error(), ErrNoEncontrado.Error()) {
		t.Fatalf("no registrada → no encontrado: %v", err)
	}
}
