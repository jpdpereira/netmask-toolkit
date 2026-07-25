# Roadmap

## Fase 1 - Ambiente (feito)
- Repositorio privado no GitHub
- .gitignore a proteger mapping.json e ficheiros com dados reais
- venv + requirements-dev.txt

## Fase 2 - Arquitetura multi-vendor
- Separar core.py (motor generico: IP/IPv6/MAC) de vendors/*.py
- Perfis: aruba-switch, aruba-cx, cisco, comware, juniper, fortios, checkpoint, unifi
- Flag --vendor para escolher o perfil

## Fase 3 - Testes e CI
- Fixture fake por vendor em tests/fixtures/
- pytest a validar round-trip mask/unmask
- GitHub Actions (pytest + ruff em cada push)

## Fase 4 - Robustez
- --dry-run, multiplos ficheiros/diretorio, stdin/stdout
- logging estruturado em vez de print
- encriptacao opcional do mapping.json (Fernet + password)

## Fase 5 - Documentacao
- README completo (feito, a rever com a evolucao do projeto)
- Diagrama do pipeline mask -> IA -> unmask
