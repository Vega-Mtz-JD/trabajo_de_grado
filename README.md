# VOTO SEGURO

**Sistema de Votación Electrónica Offline con Blockchain para Auditoría y Verificación Multinivel de Resultados**

Proyecto de Grado — Carrera de Ingeniería de Sistemas, Universidad Pública de El Alto (UPEA).

## Qué es

Sistema de votación presencial que opera **sin red**:

- Autenticación del votante con **CI + huella dactilar (1:1)**.
- Voto en pantalla en **modo kiosco**, con comprobante en papel (**VVPAT**) que el votante deposita en una urna.
- Votos **cifrados con la clave pública de la elección**; la clave privada está repartida
  (**Shamir 3-de-5**) entre custodios y solo se reconstruye en el escrutinio.
- Hitos de la elección anclados en **Hyperledger Fabric 2.5**.
- **Auditoría triple**: papel (VVPAT + actas) ↔ USB cifrado ↔ ledger.

## Estructura

```
docs/         Vault de Obsidian: propuesta v5, ADRs, informe (Art. 48), bitácora, normativa
app/          Aplicación Python (paquete votoseguro) y pruebas
blockchain/   Red Fabric, chaincode Go y puente Go
scripts/      Instalación, hardening y kiosco
```

## Documentación clave

- [Propuesta v5](docs/propuesta_v5.md)
- [Decisiones de arquitectura (ADR)](docs/decisiones/README.md)
- [Guía de Obsidian del proyecto](docs/Guia-Obsidian.md)
- [Contexto para Claude Code](CLAUDE.md)

## Uso rápido

```bash
cd app && . .venv/bin/activate
export VOTOSEGURO_DSN='dbname=votoseguro'
votoseguro-ui                    # panel de mesa + kiosco (hardware simulado)
votoseguro demo --mesas 3        # simulación completa por línea de comandos
```

## Desarrollo

```bash
cd app
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Licencia

Apache 2.0 — ver [LICENSE](LICENSE).
