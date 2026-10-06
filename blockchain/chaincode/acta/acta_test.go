package main

import (
	"encoding/json"
	"errors"
	"strings"
	"testing"
	"time"

	"github.com/hyperledger/fabric-chaincode-go/v2/shim"
	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
	"google.golang.org/protobuf/types/known/timestamppb"
)

// stubMemoria implementa solo lo que usa el contrato; el resto de la interfaz no se invoca.
type stubMemoria struct {
	shim.ChaincodeStubInterface
	estado map[string][]byte
}

func (s *stubMemoria) GetState(k string) ([]byte, error) { return s.estado[k], nil }
func (s *stubMemoria) PutState(k string, v []byte) error  { s.estado[k] = v; return nil }
func (s *stubMemoria) GetTxTimestamp() (*timestamppb.Timestamp, error) {
	return timestamppb.New(time.Date(2026, 10, 5, 12, 0, 0, 0, time.UTC)), nil
}
func (s *stubMemoria) CreateCompositeKey(tipo string, atributos []string) (string, error) {
	return "\x00" + tipo + "\x00" + strings.Join(atributos, "\x00") + "\x00", nil
}

const (
	global = "6f1c0a3e-0000-4000-8000-000000000001"
	h1     = "1111111111111111111111111111111111111111111111111111111111111111"
	h2     = "2222222222222222222222222222222222222222222222222222222222222222"
	h3     = "3333333333333333333333333333333333333333333333333333333333333333"
)

func nuevoContexto() *contractapi.TransactionContext {
	ctx := new(contractapi.TransactionContext)
	ctx.SetStub(&stubMemoria{estado: map[string][]byte{}})
	return ctx
}

func js(v any) string {
	b, _ := json.Marshal(v)
	return string(b)
}

func esValidacion(t *testing.T, err error, fragmento string) {
	t.Helper()
	if err == nil || !errors.Is(err, ErrValidacion) || !strings.Contains(err.Error(), fragmento) {
		t.Fatalf("se esperaba error de validación con %q, se obtuvo: %v", fragmento, err)
	}
}

// mesaAbierta registra y abre la mesa "01" con 10 habilitados.
func mesaAbierta(t *testing.T, c *Contrato, ctx *contractapi.TransactionContext) {
	t.Helper()
	if err := c.RegistrarEleccion(ctx, js(ArgsEleccion{global, "01", h1, h2, h3})); err != nil {
		t.Fatal(err)
	}
	if err := c.RegistrarApertura(ctx, js(ArgsApertura{global, "01", h1, h2, 10})); err != nil {
		t.Fatal(err)
	}
}

func checkpoint(seq, conteo int, raiz string) string {
	return js(ArgsCheckpoint{global, "01", Checkpoint{seq, conteo, raiz}})
}

func TestFlujoCompletoEIdempotencia(t *testing.T) {
	c, ctx := &Contrato{}, nuevoContexto()
	mesaAbierta(t, c, ctx)
	pasos := []func() error{
		func() error { return c.RegistrarCheckpoint(ctx, checkpoint(1, 5, h1)) },
		func() error { return c.RegistrarCheckpoint(ctx, checkpoint(2, 8, h2)) },
		func() error { return c.RegistrarCierre(ctx, js(ArgsCierre{global, "01", 8, 8, h2, h3})) },
		func() error {
			return c.RegistrarEscrutinio(ctx, js(ArgsEscrutinio{global, "01", map[string]int{"A": 5, "B": 3}, 8, h1}))
		},
		func() error { return c.RegistrarExportacion(ctx, js(ArgsExportacion{global, "01", h2})) },
	}
	for i, paso := range pasos {
		if err := paso(); err != nil {
			t.Fatalf("paso %d: %v", i, err)
		}
		if err := paso(); err != nil { // reenviar el mismo hito (outbox) no es error
			t.Fatalf("reintento del paso %d: %v", i, err)
		}
	}
	texto, err := c.ConsultarMesa(ctx, global, "01")
	if err != nil {
		t.Fatal(err)
	}
	var m Mesa
	if err := json.Unmarshal([]byte(texto), &m); err != nil {
		t.Fatal(err)
	}
	if m.Estado != EstadoExportada || len(m.Checkpoints) != 2 || m.Resultados["A"] != 5 || m.Momentos[EstadoCerrada] == "" {
		t.Fatalf("estado final inesperado: %+v", m)
	}
}

func TestRegistroDuplicadoConOtrosDatos(t *testing.T) {
	c, ctx := &Contrato{}, nuevoContexto()
	mesaAbierta(t, c, ctx)
	esValidacion(t, c.RegistrarEleccion(ctx, js(ArgsEleccion{global, "01", h2, h2, h3})), "ya está registrada")
}

func TestHitosFueraDeOrden(t *testing.T) {
	c, ctx := &Contrato{}, nuevoContexto()
	esValidacion(t, c.RegistrarApertura(ctx, js(ArgsApertura{global, "01", h1, h2, 10})), "no está registrada")
	if err := c.RegistrarEleccion(ctx, js(ArgsEleccion{global, "01", h1, h2, h3})); err != nil {
		t.Fatal(err)
	}
	esValidacion(t, c.RegistrarCheckpoint(ctx, checkpoint(1, 1, h1)), "se requiere ABIERTA")
	esValidacion(t, c.RegistrarCierre(ctx, js(ArgsCierre{global, "01", 0, 0, h1, h2})), "se requiere ABIERTA")
	esValidacion(t, c.RegistrarExportacion(ctx, js(ArgsExportacion{global, "01", h1})), "se requiere ESCRUTADA")
}

func TestCheckpointsInvalidos(t *testing.T) {
	c, ctx := &Contrato{}, nuevoContexto()
	mesaAbierta(t, c, ctx)
	esValidacion(t, c.RegistrarCheckpoint(ctx, checkpoint(2, 3, h1)), "se esperaba el checkpoint 1")
	if err := c.RegistrarCheckpoint(ctx, checkpoint(1, 5, h1)); err != nil {
		t.Fatal(err)
	}
	esValidacion(t, c.RegistrarCheckpoint(ctx, checkpoint(1, 6, h1)), "ya fue anclado con otros datos")
	esValidacion(t, c.RegistrarCheckpoint(ctx, checkpoint(2, 4, h2)), "fuera de rango")  // decrece
	esValidacion(t, c.RegistrarCheckpoint(ctx, checkpoint(2, 11, h2)), "fuera de rango") // > habilitados
	esValidacion(t, c.RegistrarCheckpoint(ctx, checkpoint(2, 6, "zz")), "hash SHA3-256")
}

func TestCierreDebeCoincidirConElUltimoCheckpoint(t *testing.T) {
	c, ctx := &Contrato{}, nuevoContexto()
	mesaAbierta(t, c, ctx)
	esValidacion(t, c.RegistrarCierre(ctx, js(ArgsCierre{global, "01", 0, 0, h1, h2})), "no hay checkpoints")
	if err := c.RegistrarCheckpoint(ctx, checkpoint(1, 5, h1)); err != nil {
		t.Fatal(err)
	}
	esValidacion(t, c.RegistrarCierre(ctx, js(ArgsCierre{global, "01", 6, 6, h1, h2})), "último checkpoint")
	esValidacion(t, c.RegistrarCierre(ctx, js(ArgsCierre{global, "01", 5, 5, h3, h2})), "último checkpoint")
	esValidacion(t, c.RegistrarCierre(ctx, js(ArgsCierre{global, "01", 5, 4, h1, h2})), "votantes marcados")
}

func TestEscrutinioDebeSumarElTotal(t *testing.T) {
	c, ctx := &Contrato{}, nuevoContexto()
	mesaAbierta(t, c, ctx)
	if err := c.RegistrarCheckpoint(ctx, checkpoint(1, 5, h1)); err != nil {
		t.Fatal(err)
	}
	if err := c.RegistrarCierre(ctx, js(ArgsCierre{global, "01", 5, 5, h1, h2})); err != nil {
		t.Fatal(err)
	}
	esValidacion(t, c.RegistrarEscrutinio(ctx, js(ArgsEscrutinio{global, "01", map[string]int{"A": 4}, 5, h3})), "≠ votos")
	esValidacion(t, c.RegistrarEscrutinio(ctx, js(ArgsEscrutinio{global, "01", map[string]int{"A": 6}, 6, h3})), "≠ votos")
	esValidacion(t, c.RegistrarEscrutinio(ctx, js(ArgsEscrutinio{global, "01", map[string]int{"A": 6, "B": -1}, 5, h3})), "negativo")
}

func TestIdentidadYArgumentosInvalidos(t *testing.T) {
	c, ctx := &Contrato{}, nuevoContexto()
	esValidacion(t, c.RegistrarEleccion(ctx, js(ArgsEleccion{"no-uuid", "01", h1, h2, h3})), "UUID")
	esValidacion(t, c.RegistrarEleccion(ctx, js(ArgsEleccion{global, "mesa 1", h1, h2, h3})), "mesa")
	esValidacion(t, c.RegistrarEleccion(ctx, "{no es json"), "JSON")
	esValidacion(t, c.RegistrarApertura(ctx, js(ArgsApertura{global, "01", h1, h2, 0})), "no está registrada")
	if err := c.RegistrarEleccion(ctx, js(ArgsEleccion{global, "01", h1, h2, h3})); err != nil {
		t.Fatal(err)
	}
	esValidacion(t, c.RegistrarApertura(ctx, js(ArgsApertura{global, "01", h1, h2, 0})), "habilitados")
}
