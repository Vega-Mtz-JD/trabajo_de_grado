package main

import (
	"context"
	"crypto/x509"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/hyperledger/fabric-gateway/pkg/client"
	"github.com/hyperledger/fabric-gateway/pkg/hash"
	"github.com/hyperledger/fabric-gateway/pkg/identity"
	"github.com/hyperledger/fabric-protos-go-apiv2/gateway"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/status"
)

// Configuracion de la conexión con el peer (ver iniciar.sh).
type Configuracion struct {
	Peer        string // p. ej. localhost:7051
	NombrePeer  string // nombre en el certificado TLS del peer
	CertTLS     string // CA TLS del peer
	MSPID       string
	Certificado string // certificado de la identidad cliente (User1)
	ClavePriv   string // directorio keystore de la identidad cliente
	Canal       string
	Chaincode   string
}

type ledgerFabric struct {
	conexion *grpc.ClientConn
	gateway  *client.Gateway
	contrato *client.Contract
}

// ConectarFabric abre la conexión gRPC (TLS) y el Gateway con la identidad del cliente.
func ConectarFabric(c Configuracion) (*ledgerFabric, error) {
	pemTLS, err := os.ReadFile(c.CertTLS)
	if err != nil {
		return nil, fmt.Errorf("CA TLS del peer: %w", err)
	}
	certTLS, err := identity.CertificateFromPEM(pemTLS)
	if err != nil {
		return nil, err
	}
	raices := x509.NewCertPool()
	raices.AddCert(certTLS)
	conexion, err := grpc.NewClient("dns:///"+c.Peer,
		grpc.WithTransportCredentials(credentials.NewClientTLSFromCert(raices, c.NombrePeer)))
	if err != nil {
		return nil, err
	}

	pemCert, err := os.ReadFile(c.Certificado)
	if err != nil {
		return nil, fmt.Errorf("certificado del cliente: %w", err)
	}
	cert, err := identity.CertificateFromPEM(pemCert)
	if err != nil {
		return nil, err
	}
	id, err := identity.NewX509Identity(c.MSPID, cert)
	if err != nil {
		return nil, err
	}
	claves, err := os.ReadDir(c.ClavePriv)
	if err != nil || len(claves) == 0 {
		return nil, fmt.Errorf("clave privada del cliente no encontrada en %s", c.ClavePriv)
	}
	pemClave, err := os.ReadFile(filepath.Join(c.ClavePriv, claves[0].Name()))
	if err != nil {
		return nil, err
	}
	clave, err := identity.PrivateKeyFromPEM(pemClave)
	if err != nil {
		return nil, err
	}
	firma, err := identity.NewPrivateKeySign(clave)
	if err != nil {
		return nil, err
	}

	gw, err := client.Connect(id, client.WithSign(firma), client.WithHash(hash.SHA256),
		client.WithClientConnection(conexion),
		client.WithEvaluateTimeout(10*time.Second), client.WithEndorseTimeout(20*time.Second),
		client.WithSubmitTimeout(10*time.Second), client.WithCommitStatusTimeout(time.Minute))
	if err != nil {
		return nil, err
	}
	return &ledgerFabric{conexion, gw, gw.GetNetwork(c.Canal).GetContract(c.Chaincode)}, nil
}

// Cerrar libera el Gateway y la conexión gRPC.
func (l *ledgerFabric) Cerrar() {
	l.gateway.Close()
	l.conexion.Close()
}

// Enviar endosa, ordena y espera la confirmación de la transacción; devuelve su identificador.
func (l *ledgerFabric) Enviar(ctx context.Context, funcion, argsJSON string) (string, error) {
	propuesta, err := l.contrato.NewProposal(funcion, client.WithArguments(argsJSON))
	if err != nil {
		return "", clasificar(err)
	}
	tx, err := propuesta.EndorseWithContext(ctx)
	if err != nil {
		return "", clasificar(err)
	}
	commit, err := tx.SubmitWithContext(ctx)
	if err != nil {
		return "", clasificar(err)
	}
	estado, err := commit.StatusWithContext(ctx)
	if err != nil {
		return "", clasificar(err)
	}
	if !estado.Successful {
		return "", fmt.Errorf("%w: transacción %s inválida (%s)", ErrRechazado, estado.TransactionID, estado.Code)
	}
	return estado.TransactionID, nil
}

// Consultar evalúa una función de solo lectura del chaincode.
func (l *ledgerFabric) Consultar(ctx context.Context, funcion string, args ...string) ([]byte, error) {
	propuesta, err := l.contrato.NewProposal(funcion, client.WithArguments(args...))
	if err != nil {
		return nil, clasificar(err)
	}
	resultado, err := propuesta.EvaluateWithContext(ctx)
	if err != nil {
		return nil, clasificar(err)
	}
	return resultado, nil
}

// clasificar traduce los errores de Fabric a los errores del puente, incluyendo el mensaje
// del chaincode (que viene en los detalles del estado gRPC).
func clasificar(err error) error {
	mensaje := err.Error()
	if s, ok := status.FromError(err); ok {
		for _, d := range s.Details() {
			if detalle, ok := d.(*gateway.ErrorDetail); ok {
				mensaje = detalle.GetMessage()
			}
		}
		switch s.Code() {
		case codes.Unavailable, codes.DeadlineExceeded:
			return fmt.Errorf("%w: %s", ErrNoDisponible, mensaje)
		}
	}
	switch {
	case strings.Contains(mensaje, "no está registrada"):
		return fmt.Errorf("%w: %s", ErrNoEncontrado, mensaje)
	case strings.Contains(mensaje, "validación"):
		return fmt.Errorf("%w: %s", ErrRechazado, mensaje)
	}
	return err
}
