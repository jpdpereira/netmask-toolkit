# netmask-toolkit

Mascara e reverte informacao sensivel (IPs, MACs, hostnames, descricoes de
porta, vizinhos LLDP/CDP) em ficheiros de configuracao de rede
(`show running-config`, `show logs`, `show cdp/lldp neighbors`, etc.),
para que possam ser partilhados com ferramentas de IA ou terceiros sem
expor dados reais.

## Fluxo de uso

```bash
python netmask.py mask   -i show_run.txt         -o show_run_masked.txt -m mapping.json --vendor cisco
# partilha-se show_run_masked.txt com a IA / terceiro
python netmask.py unmask -i resposta_recebida.txt -o resposta_real.txt  -m mapping.json
```

O ficheiro `mapping.json` e a chave de reversao. **Nunca o commitar nem
partilhar** — trata-o como uma credencial. O `.gitignore` ja o bloqueia.

Usa `--dry-run` para veres quantos itens seriam mascarados sem escrever
nada em disco — util para validar um ficheiro novo antes de confiar cegamente
no regex.

## Vendors suportados (`--vendor`)

| Flag | Plataforma |
|---|---|
| `cisco` | Cisco IOS / IOS-XE |
| `aruba-switch` | HPE Aruba AOS-Switch (ex-ProVision/ProCurve: 2530, 2920, 2930) |
| `aruba-cx` | HPE Aruba AOS-CX |
| `comware` | HPE Comware |
| `juniper` | Juniper JunOS (sintaxe `set`) |
| `fortios` | Fortinet FortiOS |
| `checkpoint` | Check Point Gaia (clish) |
| `unifi` | UniFi/Ubiquiti (EdgeOS/vyatta-style) |
| `generic` | Fallback universal (default, quando nao se especifica `--vendor`) |

Os padroes de cada vendor estao em `vendors.py` — e o unico ficheiro a
tocar para adicionar uma plataforma nova ou afinar um regex ao teu
equipamento real. `core.py` (motor generico) nao precisa de ser alterado.

## O que e mascarado

- Enderecos IPv4 e IPv6 (incluindo notacao comprimida `::` e `/prefixo`)
- Enderecos MAC (`:`, `-`, `.`)
- Hostname do dispositivo (e propagado a prompts/banners)
- Descricoes de interface (nome varia por vendor: `description`, `name`, `alias`)
- Campos LLDP/CDP (nome varia por vendor: `System Name`, `Device ID`, `SysName`, `PortDescr`, etc.)

## Arquitetura

```
core.py      -> motor generico: gestao de tokens, IP/IPv6/MAC (nao conhece vendors)
vendors.py   -> padroes especificos por plataforma (hostname, descricao, LLDP/CDP)
netmask.py   -> CLI (argparse), liga core + vendors
```

## Roadmap

Ver `docs/roadmap.md` — Fase 2 (multi-vendor) feita. Falta: CI no GitHub
Actions, fixtures/testes para todos os 8 vendors, encriptacao do
mapping.json, deteccao automatica de vendor.

## Instalacao

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Testes

```bash
pytest
```
