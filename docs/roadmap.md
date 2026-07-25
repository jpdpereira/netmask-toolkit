# Roadmap

## Fase 1 - Ambiente (feito)
- Repositorio privado no GitHub
- .gitignore a proteger mapping.json e ficheiros com dados reais
- venv + requirements-dev.txt

## Fase 2 - Arquitetura multi-vendor (feito)
- core.py (motor generico: tokens + IP/IPv6/MAC) separado de vendors.py
- Perfis: cisco, aruba-switch, aruba-cx, comware, juniper, fortios, checkpoint, unifi, generic
- Flag --vendor no CLI para escolher o perfil
- --dry-run adicionado (mostra o que seria mascarado sem escrever ficheiros)
- logging em vez de print, com tratamento de erro para ficheiro/vendor invalido
- 8 testes pytest, incluindo round-trip completo para cisco/aruba-switch/fortios/juniper
  e validacao estrutural dos 9 perfis (todos os regex com exatamente 2 grupos)

Nota: os regex de cada vendor foram escritos a partir do conhecimento da
sintaxe tipica de cada plataforma, nao de outputs reais capturados no
terreno. Ao usar com um equipamento real, se algum campo escapar ao
mascaramento, o ajuste e sempre so em vendors.py.

## Fase 3 - Testes e CI
- Fixtures reais (anonimizadas) capturadas do teu ambiente, uma por vendor em uso
- Testes de round-trip para os restantes vendors (aruba-cx, comware, checkpoint, unifi)
- GitHub Actions (pytest + ruff em cada push)

## Fase 4 - Robustez
- Multiplos ficheiros/diretorio de uma vez, suporte a stdin/stdout
- Deteccao automatica de vendor por keywords do ficheiro
- Encriptacao opcional do mapping.json (Fernet + password)

## Fase 5 - Documentacao
- README completo (feito, a rever com a evolucao do projeto)
- Diagrama do pipeline mask -> IA -> unmask
