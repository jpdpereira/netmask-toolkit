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

## Fase 3 - Testes e CI (feito)
- Round-trip testado para os 8 vendors (cisco, aruba-switch, aruba-cx,
  comware, juniper, fortios, checkpoint, unifi) -- 12 testes pytest no total
- pyproject.toml com config do ruff (ignora EXE002, irrelevante neste ambiente)
- GitHub Actions (.github/workflows/ci.yml): corre ruff + pytest em Python
  3.10 e 3.12, em cada push/PR para main

Nota: as amostras de teste sao sinteticas (escritas a partir do
conhecimento da sintaxe de cada plataforma), nao capturas reais. Se
quiseres reforcar a confianca, o proximo passo natural e substituir por
fixtures anonimizadas a partir de outputs reais do teu ambiente (usando o
proprio netmask.py para as gerar em seguranca).

## Fase 4 - Robustez (feito)
- vendors.detect_vendor(): heuristica por assinaturas regex, `--vendor auto`
  no CLI, testada para os 8 vendors + caso de texto irreconhecivel
- Modo diretorio: `-i pasta/ -o pasta/` processa todos os *.txt com um
  unico Masker partilhado (mesmo valor -> mesmo token em todo o lote)
- Suporte a stdin/stdout: `-i -` / `-o -` para uso em pipe
- crypto_utils.py: encriptacao opcional do mapping.json com `--encrypt`
  (Fernet + PBKDF2-HMAC-SHA256, 480k iteracoes, password nunca gravada em
  disco); deteccao automatica de ficheiro cifrado no unmask
- 26 testes pytest no total (12 core + 8 deteccao de vendor + 1 caso
  negativo + 5 de encriptacao)

Nota: a heuristica de deteccao de vendor e probabilistica -- funciona bem
nas amostras sinteticas testadas, mas com equipamento real pode precisar
de afinacao das assinaturas em `VENDOR_SIGNATURES` (vendors.py).

## Fase 5 - Documentacao
- README completo (feito, a rever com a evolucao do projeto)
- Diagrama do pipeline mask -> IA -> unmask

## Fase 5.1 - imc_mask.py (feito)
Ferramenta separada de `netmask.py`, para exports CSV do HPE IMC
(projeto de validacao de inventario). Diferente do motor de texto livre:
trabalha por coluna, com uma regra por campo.

- `IP Address` -> mascara so os 2 primeiros octetos, mapeamento
  consistente por prefixo (10.45.x.x -> 10.1.x.x sempre)
- `Location` -> codigo sequencial (SITE-A, SITE-B, ...)
- `Serial Number` -> token sequencial (SN-0001, ...), mesma serie real =
  mesmo token sempre (critico para nao contar o mesmo equipamento 2x)
- `Rack` -> token sequencial (RACK-01, ...)
- `Contact` -> coluna removida por completo (dado pessoal)
- restantes colunas mantidas intactas
- mapping (`imc_mapping.json`) persistente entre execucoes -- um export
  do mes seguinte reutiliza os mesmos tokens para os mesmos equipamentos
- deteta automaticamente `,` vs `;` como separador (exports Excel PT)
- 9 testes pytest (36 no total do projeto)

Nota: cobre por agora o export de dispositivos (File 1). O export de
alarmes (File 2), com mascaramento de IPs embutidos no campo
`Description`, fica para uma proxima iteracao -- ainda nao foram
fornecidos os cabecalhos desse ficheiro.
