package main

import (
	"log"
	"net"
	"net/http"
	"os"
	"time"
)

func entorno(nombre, porDefecto string) string {
	if v := os.Getenv(nombre); v != "" {
		return v
	}
	return porDefecto
}

func main() {
	token := os.Getenv("VOTOSEGURO_PUENTE_TOKEN")
	if len(token) < 32 {
		log.Fatal("VOTOSEGURO_PUENTE_TOKEN debe tener al menos 32 caracteres")
	}
	escucha := entorno("PUENTE_ESCUCHA", "127.0.0.1:8770")
	host, _, err := net.SplitHostPort(escucha)
	if err != nil {
		log.Fatalf("PUENTE_ESCUCHA inválida: %v", err)
	}
	if ip := net.ParseIP(host); host != "localhost" && (ip == nil || !ip.IsLoopback()) {
		log.Fatalf("el puente solo puede escuchar en la interfaz local (127.0.0.1), no en %s", host)
	}
	ledger, err := ConectarFabric(Configuracion{
		Peer:        entorno("FABRIC_PEER", "localhost:7051"),
		NombrePeer:  entorno("FABRIC_PEER_NOMBRE", "peer0.mesa.votoseguro.local"),
		CertTLS:     os.Getenv("FABRIC_TLS_CA"),
		MSPID:       entorno("FABRIC_MSPID", "MesaMSP"),
		Certificado: os.Getenv("FABRIC_CERT"),
		ClavePriv:   os.Getenv("FABRIC_KEYSTORE"),
		Canal:       entorno("FABRIC_CANAL", "elecciones"),
		Chaincode:   entorno("FABRIC_CHAINCODE", "acta"),
	})
	if err != nil {
		log.Fatalf("no se pudo conectar con Fabric: %v", err)
	}
	defer ledger.Cerrar()
	servidor := &http.Server{
		Addr: escucha, Handler: NuevoServidor(ledger, token).Rutas(),
		ReadHeaderTimeout: 5 * time.Second, WriteTimeout: 2 * time.Minute,
	}
	log.Printf("puente VOTO SEGURO escuchando en http://%s", escucha)
	log.Fatal(servidor.ListenAndServe())
}
