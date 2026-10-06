package main

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

// Contrato expone los hitos electorales como transacciones de Fabric. Cada función recibe un
// único argumento JSON con los mismos campos que el outbox de la aplicación.
type Contrato struct {
	contractapi.Contract
}

// Historial es una versión anterior del estado de una mesa, con su transacción.
type Historial struct {
	TxID    string `json:"tx_id"`
	Momento string `json:"momento"`
	Estado  string `json:"estado"`
}

func clave(ctx contractapi.TransactionContextInterface, global, mesa string) (string, error) {
	return ctx.GetStub().CreateCompositeKey("MESA", []string{global, mesa})
}

func momento(ctx contractapi.TransactionContextInterface) (string, error) {
	ts, err := ctx.GetStub().GetTxTimestamp()
	if err != nil {
		return "", err
	}
	return ts.AsTime().UTC().Format(time.RFC3339), nil
}

func leer(ctx contractapi.TransactionContextInterface, global, mesa string) (*Mesa, error) {
	if err := validarIdentidad(global, mesa); err != nil {
		return nil, err
	}
	k, err := clave(ctx, global, mesa)
	if err != nil {
		return nil, err
	}
	datos, err := ctx.GetStub().GetState(k)
	if err != nil {
		return nil, err
	}
	if datos == nil {
		return nil, invalido("la mesa %s de la elección %s no está registrada", mesa, global)
	}
	var m Mesa
	if err := json.Unmarshal(datos, &m); err != nil {
		return nil, err
	}
	return &m, nil
}

func guardar(ctx contractapi.TransactionContextInterface, m *Mesa) error {
	k, err := clave(ctx, m.EleccionGlobal, m.Mesa)
	if err != nil {
		return err
	}
	datos, err := json.Marshal(m)
	if err != nil {
		return err
	}
	return ctx.GetStub().PutState(k, datos)
}

func decodificar(argsJSON string, destino any) error {
	if err := json.Unmarshal([]byte(argsJSON), destino); err != nil {
		return invalido("argumentos JSON inválidos: %v", err)
	}
	return nil
}

// RegistrarEleccion ancla la instalación de una mesa (definición, clave y equipo).
func (c *Contrato) RegistrarEleccion(ctx contractapi.TransactionContextInterface, argsJSON string) error {
	var a ArgsEleccion
	if err := decodificar(argsJSON, &a); err != nil {
		return err
	}
	if existente, err := leer(ctx, a.EleccionGlobal, a.Mesa); err == nil {
		if existente.MismoRegistro(a) {
			return nil // reintento idempotente
		}
		return invalido("la mesa %s ya está registrada con otros datos", a.Mesa)
	}
	ahora, err := momento(ctx)
	if err != nil {
		return err
	}
	m, err := NuevaMesa(a, ahora)
	if err != nil {
		return err
	}
	return guardar(ctx, m)
}

// aplicar lee la mesa, aplica el hito y guarda solo si hubo cambios.
func aplicar(ctx contractapi.TransactionContextInterface, global, mesa string,
	paso func(m *Mesa, ahora string) (bool, error)) error {
	m, err := leer(ctx, global, mesa)
	if err != nil {
		return err
	}
	ahora, err := momento(ctx)
	if err != nil {
		return err
	}
	cambio, err := paso(m, ahora)
	if err != nil || !cambio {
		return err
	}
	return guardar(ctx, m)
}

// RegistrarApertura ancla el hash de la zerésima y el compromiso del padrón.
func (c *Contrato) RegistrarApertura(ctx contractapi.TransactionContextInterface, argsJSON string) error {
	var a ArgsApertura
	if err := decodificar(argsJSON, &a); err != nil {
		return err
	}
	return aplicar(ctx, a.EleccionGlobal, a.Mesa, func(m *Mesa, t string) (bool, error) { return m.Abrir(a, t) })
}

// RegistrarCheckpoint ancla el conteo y la raíz de Merkle de la urna cada N votos.
func (c *Contrato) RegistrarCheckpoint(ctx contractapi.TransactionContextInterface, argsJSON string) error {
	var a ArgsCheckpoint
	if err := decodificar(argsJSON, &a); err != nil {
		return err
	}
	return aplicar(ctx, a.EleccionGlobal, a.Mesa, func(m *Mesa, _ string) (bool, error) {
		return m.AgregarCheckpoint(a.Checkpoint)
	})
}

// RegistrarCierre ancla los totales, la raíz final y el hash del acta de cierre.
func (c *Contrato) RegistrarCierre(ctx contractapi.TransactionContextInterface, argsJSON string) error {
	var a ArgsCierre
	if err := decodificar(argsJSON, &a); err != nil {
		return err
	}
	return aplicar(ctx, a.EleccionGlobal, a.Mesa, func(m *Mesa, t string) (bool, error) { return m.Cerrar(a, t) })
}

// RegistrarEscrutinio ancla los resultados y el hash del acta de escrutinio.
func (c *Contrato) RegistrarEscrutinio(ctx contractapi.TransactionContextInterface, argsJSON string) error {
	var a ArgsEscrutinio
	if err := decodificar(argsJSON, &a); err != nil {
		return err
	}
	return aplicar(ctx, a.EleccionGlobal, a.Mesa, func(m *Mesa, t string) (bool, error) { return m.Escrutar(a, t) })
}

// RegistrarExportacion ancla el hash del manifiesto del paquete USB.
func (c *Contrato) RegistrarExportacion(ctx contractapi.TransactionContextInterface, argsJSON string) error {
	var a ArgsExportacion
	if err := decodificar(argsJSON, &a); err != nil {
		return err
	}
	return aplicar(ctx, a.EleccionGlobal, a.Mesa, func(m *Mesa, t string) (bool, error) { return m.Exportar(a, t) })
}

// ConsultarMesa devuelve el estado anclado de una mesa como JSON. Se devuelve texto (y no el
// struct) porque el esquema del contract API exigiría campos que aún no existen en mesas abiertas.
func (c *Contrato) ConsultarMesa(ctx contractapi.TransactionContextInterface, global, mesa string) (string, error) {
	m, err := leer(ctx, global, mesa)
	if err != nil {
		return "", err
	}
	datos, err := json.Marshal(m)
	return string(datos), err
}

// ConsultarHistorial devuelve todas las versiones del estado de la mesa, con su transacción,
// en orden cronológico.
func (c *Contrato) ConsultarHistorial(ctx contractapi.TransactionContextInterface, global, mesa string) (string, error) {
	historial, err := historial(ctx, global, mesa)
	if err != nil {
		return "", err
	}
	datos, err := json.Marshal(historial)
	return string(datos), err
}

func historial(ctx contractapi.TransactionContextInterface, global, mesa string) ([]Historial, error) {
	if err := validarIdentidad(global, mesa); err != nil {
		return nil, err
	}
	k, err := clave(ctx, global, mesa)
	if err != nil {
		return nil, err
	}
	iter, err := ctx.GetStub().GetHistoryForKey(k)
	if err != nil {
		return nil, err
	}
	defer iter.Close()
	historial := []Historial{}
	for iter.HasNext() {
		r, err := iter.Next()
		if err != nil {
			return nil, err
		}
		var m Mesa
		if err := json.Unmarshal(r.Value, &m); err != nil {
			return nil, fmt.Errorf("historial ilegible: %w", err)
		}
		historial = append(historial, Historial{r.TxId, r.Timestamp.AsTime().UTC().Format(time.RFC3339), m.Estado})
	}
	// Fabric 2.x entrega el historial del más reciente al más antiguo; se invierte a orden cronológico.
	for i, j := 0, len(historial)-1; i < j; i, j = i+1, j-1 {
		historial[i], historial[j] = historial[j], historial[i]
	}
	return historial, nil
}
