package main

import (
	"log"
	"os"

	"github.com/hyperledger/fabric-chaincode-go/v2/shim"
	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

// El chaincode corre como servicio (Chaincode-as-a-Service): el peer se conecta a él, así que
// no necesita compilarlo ni descargar dependencias (operación offline, ADR-001).
func main() {
	cc, err := contractapi.NewChaincode(&Contrato{})
	if err != nil {
		log.Fatalf("no se pudo crear el chaincode: %v", err)
	}
	cc.Info.Title = "acta"
	cc.Info.Version = "1.0"
	servidor := &shim.ChaincodeServer{
		CCID:     os.Getenv("CHAINCODE_ID"),
		Address:  os.Getenv("CHAINCODE_SERVER_ADDRESS"),
		CC:       cc,
		TLSProps: shim.TLSProperties{Disabled: true}, // red Docker local del mismo equipo
	}
	if servidor.CCID == "" || servidor.Address == "" {
		log.Fatal("faltan CHAINCODE_ID y/o CHAINCODE_SERVER_ADDRESS")
	}
	log.Printf("chaincode acta escuchando en %s", servidor.Address)
	if err := servidor.Start(); err != nil {
		log.Fatalf("error del servidor de chaincode: %v", err)
	}
}
