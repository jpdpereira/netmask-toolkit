# netmask-toolkit

Mascara e reverte informacao sensivel (IPs, MACs, hostnames, descricoes de
porta, vizinhos LLDP/CDP) em ficheiros de configuracao de rede
(`show running-config`, `show logs`, `show cdp/lldp neighbors`, etc.),
para que possam ser partilhados com ferramentas de IA ou terceiros sem
expor dados reais.

## Fluxo de uso

```bash
python netmask.py mask   -i show_run.txt         -o show_run_masked.txt -m mapping.json
# partilha-se show_run_masked.txt com a IA / terceiro
python netmask.py unmask -i resposta_recebida.txt -o resposta_real.txt  -m mapping.json
```

O ficheiro `mapping.json` e a chave de reversao. **Nunca o commitar nem
partilhar** — trata-o como uma credencial. O `.gitignore` ja o bloqueia.

## O que e mascarado

- Enderecos IPv4 e IPv6 (incluindo notacao comprimida `::` e `/prefixo`)
- Enderecos MAC (`:`, `-`, `.`)
- Hostname do dispositivo (e propagado a prompts/banners)
- Descricoes de interface (`description ...`)
- Campos LLDP/CDP (`System Name`, `Device ID`, `Port ID`)

## Roadmap

Ver `docs/roadmap.md` (ou a conversa original) — planeado suporte
multi-vendor (Aruba AOS-Switch, Aruba AOS-CX, Cisco, HPE Comware,
CheckPoint, FortiOS, Juniper, UniFi), testes pytest por vendor, e CI via
GitHub Actions.

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
