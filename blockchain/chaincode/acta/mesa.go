// Package main implementa el chaincode "acta" de VOTO SEGURO (ADR-001).
//
// El chaincode ancla los hitos de cada mesa de votación: registro, apertura (zerésima),
// checkpoints, cierre, escrutinio y exportación. Valida que los hitos lleguen en el orden de
// la máquina de estados y que los conteos sean coherentes. Nunca recibe datos personales:
// solo hashes, conteos y raíces de Merkle.
//
// Este archivo contiene la lógica pura (sin dependencias de Fabric), para probarla con
// pruebas unitarias simples.
package main

import (
	"errors"
	"fmt"
	"regexp"
)

// Estados de una mesa en el ledger.
const (
	EstadoRegistrada = "REGISTRADA"
	EstadoAbierta    = "ABIERTA"
	EstadoCerrada    = "CERRADA"
	EstadoEscrutada  = "ESCRUTADA"
	EstadoExportada  = "EXPORTADA"
)

// ErrValidacion indica que el hito no es coherente con lo ya anclado.
var ErrValidacion = errors.New("validación")

var (
	reHash = regexp.MustCompile(`^[0-9a-f]{64}$`)
	reUUID = regexp.MustCompile(`^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`)
	reMesa = regexp.MustCompile(`^[A-Z0-9-]{1,10}$`)
)

// Checkpoint resume la urna en un momento: cuántos votos había y su raíz de Merkle.
type Checkpoint struct {
	Seq        int    `json:"seq"`
	Conteo     int    `json:"conteo"`
	RaizMerkle string `json:"raiz_merkle"`
}

// Mesa es el estado anclado de una mesa de una elección.
type Mesa struct {
	EleccionGlobal      string            `json:"eleccion_global"`
	Mesa                string            `json:"mesa"`
	Estado              string            `json:"estado"`
	HashConfiguracion   string            `json:"hash_configuracion"`
	HuellaClaveEleccion string            `json:"huella_clave_eleccion"`
	HuellaDispositivo   string            `json:"huella_dispositivo"`
	HashZeresima        string            `json:"hash_zeresima,omitempty"`
	CompromisoPadron    string            `json:"compromiso_padron,omitempty"`
	Habilitados         int               `json:"habilitados,omitempty"`
	Checkpoints         []Checkpoint      `json:"checkpoints"`
	TotalVotos          int               `json:"total_votos,omitempty"`
	TotalVotantes       int               `json:"total_votantes,omitempty"`
	RaizMerkle          string            `json:"raiz_merkle,omitempty"`
	HashActaCierre      string            `json:"hash_acta_cierre,omitempty"`
	Resultados          map[string]int    `json:"resultados,omitempty"`
	Total               int               `json:"total,omitempty"`
	HashActaEscrutinio  string            `json:"hash_acta_escrutinio,omitempty"`
	HashManifiesto      string            `json:"hash_manifiesto,omitempty"`
	Momentos            map[string]string `json:"momentos"`
}

// Argumentos de cada hito (mismos nombres que el outbox de la aplicación Python).
type (
	ArgsEleccion struct {
		EleccionGlobal      string `json:"eleccion_global"`
		Mesa                string `json:"mesa"`
		HashConfiguracion   string `json:"hash_configuracion"`
		HuellaClaveEleccion string `json:"huella_clave_eleccion"`
		HuellaDispositivo   string `json:"huella_dispositivo"`
	}
	ArgsApertura struct {
		EleccionGlobal   string `json:"eleccion_global"`
		Mesa             string `json:"mesa"`
		HashZeresima     string `json:"hash_zeresima"`
		CompromisoPadron string `json:"compromiso_padron"`
		Habilitados      int    `json:"habilitados"`
	}
	ArgsCheckpoint struct {
		EleccionGlobal string `json:"eleccion_global"`
		Mesa           string `json:"mesa"`
		Checkpoint
	}
	ArgsCierre struct {
		EleccionGlobal string `json:"eleccion_global"`
		Mesa           string `json:"mesa"`
		TotalVotos     int    `json:"total_votos"`
		TotalVotantes  int    `json:"total_votantes"`
		RaizMerkle     string `json:"raiz_merkle"`
		HashActa       string `json:"hash_acta"`
	}
	ArgsEscrutinio struct {
		EleccionGlobal string         `json:"eleccion_global"`
		Mesa           string         `json:"mesa"`
		Resultados     map[string]int `json:"resultados"`
		Total          int            `json:"total"`
		HashActa       string         `json:"hash_acta"`
	}
	ArgsExportacion struct {
		EleccionGlobal string `json:"eleccion_global"`
		Mesa           string `json:"mesa"`
		HashManifiesto string `json:"hash_manifiesto"`
	}
)

func invalido(formato string, a ...any) error {
	return fmt.Errorf("%w: %s", ErrValidacion, fmt.Sprintf(formato, a...))
}

func validarIdentidad(global, mesa string) error {
	if !reUUID.MatchString(global) {
		return invalido("eleccion_global no es un UUID válido")
	}
	if !reMesa.MatchString(mesa) {
		return invalido("código de mesa inválido")
	}
	return nil
}

func validarHashes(hashes map[string]string) error {
	for nombre, h := range hashes {
		if !reHash.MatchString(h) {
			return invalido("%s debe ser un hash SHA3-256 en hexadecimal", nombre)
		}
	}
	return nil
}

func exigirEstado(m *Mesa, esperado string) error {
	if m.Estado != esperado {
		return invalido("la mesa está en %s; se requiere %s", m.Estado, esperado)
	}
	return nil
}

// NuevaMesa crea el estado inicial a partir del registro de la elección.
func NuevaMesa(a ArgsEleccion, momento string) (*Mesa, error) {
	if err := validarIdentidad(a.EleccionGlobal, a.Mesa); err != nil {
		return nil, err
	}
	if err := validarHashes(map[string]string{"hash_configuracion": a.HashConfiguracion,
		"huella_clave_eleccion": a.HuellaClaveEleccion, "huella_dispositivo": a.HuellaDispositivo}); err != nil {
		return nil, err
	}
	return &Mesa{
		EleccionGlobal: a.EleccionGlobal, Mesa: a.Mesa, Estado: EstadoRegistrada,
		HashConfiguracion: a.HashConfiguracion, HuellaClaveEleccion: a.HuellaClaveEleccion,
		HuellaDispositivo: a.HuellaDispositivo, Checkpoints: []Checkpoint{},
		Momentos: map[string]string{EstadoRegistrada: momento},
	}, nil
}

// MismoRegistro indica si un nuevo registro es idéntico al existente (reintento idempotente).
func (m *Mesa) MismoRegistro(a ArgsEleccion) bool {
	return m.HashConfiguracion == a.HashConfiguracion && m.HuellaClaveEleccion == a.HuellaClaveEleccion &&
		m.HuellaDispositivo == a.HuellaDispositivo
}

// Abrir ancla la zerésima. Devuelve (cambió, error); un reintento idéntico no es error.
func (m *Mesa) Abrir(a ArgsApertura, momento string) (bool, error) {
	if m.Estado != EstadoRegistrada && m.HashZeresima == a.HashZeresima {
		return false, nil
	}
	if err := exigirEstado(m, EstadoRegistrada); err != nil {
		return false, err
	}
	if err := validarHashes(map[string]string{"hash_zeresima": a.HashZeresima,
		"compromiso_padron": a.CompromisoPadron}); err != nil {
		return false, err
	}
	if a.Habilitados <= 0 {
		return false, invalido("el padrón debe tener votantes habilitados")
	}
	m.HashZeresima, m.CompromisoPadron, m.Habilitados = a.HashZeresima, a.CompromisoPadron, a.Habilitados
	m.Estado, m.Momentos[EstadoAbierta] = EstadoAbierta, momento
	return true, nil
}

// AgregarCheckpoint exige secuencia consecutiva y conteo creciente y acotado por el padrón.
func (m *Mesa) AgregarCheckpoint(c Checkpoint) (bool, error) {
	if c.Seq >= 1 && c.Seq <= len(m.Checkpoints) {
		if m.Checkpoints[c.Seq-1] == c {
			return false, nil // reintento idempotente
		}
		return false, invalido("el checkpoint %d ya fue anclado con otros datos", c.Seq)
	}
	if err := exigirEstado(m, EstadoAbierta); err != nil {
		return false, err
	}
	if c.Seq != len(m.Checkpoints)+1 {
		return false, invalido("se esperaba el checkpoint %d y llegó el %d", len(m.Checkpoints)+1, c.Seq)
	}
	if err := validarHashes(map[string]string{"raiz_merkle": c.RaizMerkle}); err != nil {
		return false, err
	}
	anterior := 0
	if len(m.Checkpoints) > 0 {
		anterior = m.Checkpoints[len(m.Checkpoints)-1].Conteo
	}
	if c.Conteo < anterior || c.Conteo > m.Habilitados {
		return false, invalido("conteo %d fuera de rango (anterior %d, habilitados %d)", c.Conteo, anterior, m.Habilitados)
	}
	m.Checkpoints = append(m.Checkpoints, c)
	return true, nil
}

// Cerrar exige que el total coincida con el último checkpoint y con los votantes marcados.
func (m *Mesa) Cerrar(a ArgsCierre, momento string) (bool, error) {
	if m.Estado != EstadoAbierta && m.HashActaCierre == a.HashActa {
		return false, nil
	}
	if err := exigirEstado(m, EstadoAbierta); err != nil {
		return false, err
	}
	if err := validarHashes(map[string]string{"raiz_merkle": a.RaizMerkle, "hash_acta": a.HashActa}); err != nil {
		return false, err
	}
	if len(m.Checkpoints) == 0 {
		return false, invalido("no hay checkpoints anclados")
	}
	ultimo := m.Checkpoints[len(m.Checkpoints)-1]
	if a.TotalVotos != a.TotalVotantes {
		return false, invalido("votos (%d) ≠ votantes marcados (%d)", a.TotalVotos, a.TotalVotantes)
	}
	if a.TotalVotos != ultimo.Conteo || a.RaizMerkle != ultimo.RaizMerkle {
		return false, invalido("el cierre no coincide con el último checkpoint anclado")
	}
	m.TotalVotos, m.TotalVotantes, m.RaizMerkle, m.HashActaCierre = a.TotalVotos, a.TotalVotantes, a.RaizMerkle, a.HashActa
	m.Estado, m.Momentos[EstadoCerrada] = EstadoCerrada, momento
	return true, nil
}

// Escrutar exige que la suma de los resultados sea el total de votos del cierre.
func (m *Mesa) Escrutar(a ArgsEscrutinio, momento string) (bool, error) {
	if m.Estado != EstadoCerrada && m.HashActaEscrutinio == a.HashActa {
		return false, nil
	}
	if err := exigirEstado(m, EstadoCerrada); err != nil {
		return false, err
	}
	if err := validarHashes(map[string]string{"hash_acta": a.HashActa}); err != nil {
		return false, err
	}
	suma := 0
	for opcion, n := range a.Resultados {
		if n < 0 {
			return false, invalido("resultado negativo para %s", opcion)
		}
		suma += n
	}
	if suma != a.Total || a.Total != m.TotalVotos {
		return false, invalido("resultados (suma %d, total %d) ≠ votos del cierre (%d)", suma, a.Total, m.TotalVotos)
	}
	m.Resultados, m.Total, m.HashActaEscrutinio = a.Resultados, a.Total, a.HashActa
	m.Estado, m.Momentos[EstadoEscrutada] = EstadoEscrutada, momento
	return true, nil
}

// Exportar ancla el hash del manifiesto del paquete USB.
func (m *Mesa) Exportar(a ArgsExportacion, momento string) (bool, error) {
	if m.Estado == EstadoExportada && m.HashManifiesto == a.HashManifiesto {
		return false, nil
	}
	if err := exigirEstado(m, EstadoEscrutada); err != nil {
		return false, err
	}
	if err := validarHashes(map[string]string{"hash_manifiesto": a.HashManifiesto}); err != nil {
		return false, err
	}
	m.HashManifiesto = a.HashManifiesto
	m.Estado, m.Momentos[EstadoExportada] = EstadoExportada, momento
	return true, nil
}
