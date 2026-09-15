# Cheatsheet — mascarar configs com o netmask-toolkit

Guia de apoio rápido para o dia a dia. Não cobre instalação (já está
feita) — só os passos que se repetem sempre que precisas de mascarar uma
config real antes de a partilhares com uma IA ou terceiro.

---

## 0. Abrir o projeto no início da sessão

No VS Code: **File → Open Recent → netmask-toolkit**

Ou, a partir de um terminal WSL:

```bash
cd ~/netmask-toolkit
code .
```

Confirma sempre, no canto inferior esquerdo do VS Code, que aparece
**"WSL: Ubuntu"** — se aparecer só o nome de uma pasta sem isso, o
terminal integrado vai abrir em PowerShell, não em bash. Corrige com:

```
Ctrl+Shift+P → "WSL: Reopen Folder in WSL"
```

Abre o terminal integrado com `Ctrl+\`` (crase, tecla ao lado do "1").

---

## 1. Onde guardar os ficheiros de teste

**Sempre em `~/netmask-testes/`** — nunca no Desktop nem noutro sítio
aleatório, para não teres de andar à procura depois com `find`.

Se já tiveres um ficheiro `.txt` noutro lado (ex: Desktop), o caminho
equivalente dentro do WSL é:

```
/mnt/c/Users/jpdp/Desktop/nome-do-ficheiro.txt
```

(troca `Desktop` pela pasta onde realmente está)

Se perderes o rasto de um ficheiro:

```bash
find ~ -iname "*nome-parcial*" 2>/dev/null
find /mnt/c/Users/jpdp -iname "*nome-parcial*" 2>/dev/null
```

**Criar um ficheiro novo e colar conteúdo, direto no VS Code:**

`Ctrl+K` `Ctrl+O` → escreve o caminho completo, ex:
`/home/jpdp/netmask-testes/switch01.txt` → cola o conteúdo → `Ctrl+S`

---

## 2. Fluxo completo de mascaramento

### Passo 1 — Dry-run (não escreve nada, só mostra o que seria mascarado)

```bash
python3 netmask.py mask -i ~/netmask-testes/FICHEIRO.txt -o /dev/null -m /dev/null --vendor auto --dry-run
```

Confirma:
- o vendor detetado (linha `Vendor detetado automaticamente: ...`)
- a contagem de valores faz sentido (se for muito baixa, pode ter escapado algo)

Se souberes o vendor de certeza, usa-o direto em vez de `auto` (mais rápido, sem ambiguidade):

```bash
--vendor cisco | aruba-switch | aruba-cx | comware | juniper | fortios | checkpoint | unifi | generic
```

### Passo 2 — Gerar o ficheiro mascarado

```bash
python3 netmask.py mask -i ~/netmask-testes/FICHEIRO.txt -o ~/netmask-testes/FICHEIRO_masked.txt -m ~/netmask-testes/mapping_FICHEIRO.json --vendor VENDOR
```

### Passo 3 — Inspecionar ANTES de partilhar (obrigatório)

```bash
code ~/netmask-testes/FICHEIRO_masked.txt
```

Confirma a olho nu, com atenção especial a estas zonas de risco já
conhecidas (histórico de gaps encontrados):
- `snmp-server` / `snmp-agent` (community, contact, location, securityname) — são credenciais
- Tabelas resumo de LLDP sem `campo : valor` explícito (ex: `show lldp info remote-device` sem porta) — **não suportado**, usa sempre o comando detalhado por porta
- `ChassisId` em formato MAC separado por espaços (`ec eb b8 a8 99 00`)
- `vlan` com `name` e `description` como campos distintos (Comware)

### Passo 4 — Só depois de confirmares o passo 3, partilha o conteúdo mascarado

### Passo 5 — Reverter uma resposta recebida

```bash
python3 netmask.py unmask -i ~/netmask-testes/resposta.txt -o ~/netmask-testes/resposta_real.txt -m ~/netmask-testes/mapping_FICHEIRO.json
```

### Passo 6 — Confirmar round-trip (opcional mas recomendado em ficheiros novos/vendors novos)

```bash
python3 netmask.py unmask -i ~/netmask-testes/FICHEIRO_masked.txt -o ~/netmask-testes/FICHEIRO_restored.txt -m ~/netmask-testes/mapping_FICHEIRO.json
diff ~/netmask-testes/FICHEIRO.txt ~/netmask-testes/FICHEIRO_restored.txt && echo "OK: identico ao original"
```

Ou no VS Code: abre os dois ficheiros (`Ctrl+P` ou `Ctrl+K Ctrl+O`), botão
direito num separador → **"Select for Compare"**, botão direito no outro →
**"Compare with Selected"**.

---

## 2.1 IMC — mascarar CSVs de inventário (`imc_mask.py`)

Ferramenta separada, para exports CSV do IMC (dispositivos). Não usa o
`netmask.py` — é outro script, no mesmo repositório.

```bash
python3 imc_mask.py mask -i ~/netmask-testes/devices.csv -o ~/netmask-testes/devices_masked.csv -m ~/netmask-testes/imc_mapping.json
```

- `-i` — CSV real exportado do IMC
- `-o` — CSV mascarado (este é o que podes partilhar)
- `-m` — mapping persistente (nunca partilhar; guarda sempre no mesmo
  caminho para reaproveitar os tokens em exports futuros do mesmo
  inventário)

Regras aplicadas: IP (só 2 primeiros octetos mascarados), `Location` →
`SITE-A/B/...`, `Serial Number` → `SN-0001/...` (consistente por série
real), `Rack` → `RACK-01/...`, `Contact` removida por completo. Todas as
outras colunas ficam intactas.

Inspeciona sempre o `_masked.csv` antes de partilhar (mesma regra de
ouro do ponto 6). Cobre por agora só o export de dispositivos — o de
alarmes ainda não foi construído.

---

## 3. Modo diretório (vários ficheiros de uma vez)

```bash
python3 netmask.py mask -i ~/netmask-testes/pasta_real/ -o ~/netmask-testes/pasta_masked/ -m ~/netmask-testes/mapping_lote.json --vendor auto
```

Processa todos os `*.txt` da pasta com um mapping partilhado — o mesmo
valor real (ex: o mesmo vizinho LLDP) fica sempre com o mesmo token em
todos os ficheiros do lote. Só olha para ficheiros na própria pasta, não
em subpastas.

---

## 4. Mapping cifrado (opcional, se o ficheiro `.json` for ficar guardado por muito tempo)

```bash
python3 netmask.py mask -i FICHEIRO.txt -o FICHEIRO_masked.txt -m mapping.json --vendor VENDOR --encrypt
```

Pede uma password interativamente. No `unmask`, deteta sozinho se está cifrado.

---

## 5. Git — guardar as alterações

```bash
cd ~/netmask-toolkit
git status                    # ver o que mudou
git add -A
git commit -m "descrição curta da alteração"
git push
```

**Se aparecer erro `index.lock` / "Unable to create '.git/...lock': File exists"**:

```bash
rm -f .git/index.lock .git/HEAD.lock
```

e repete o `git add`/`commit`.

Alternativa sem comandos: painel **Source Control** no VS Code (ícone do
garfo na barra lateral) — escreves a mensagem no topo, `Ctrl+Enter` para
commitar, botão de sincronizar para dar push.

---

## 6. Regras de ouro (nunca esquecer)

1. O `mapping*.json` **nunca sai da tua máquina** — é a chave que reverte tudo. Nunca o cometas nem o coles em lado nenhum.
2. **Inspeciona sempre** o ficheiro mascarado antes de o partilhares — a ferramenta é uma ajuda, não uma garantia 100%.
3. Se encontrares algo que devia ter sido mascarado e não foi, é um gap real de regex em `vendors.py` — não uses esse ficheiro até corrigires.
4. Ficheiros de teste ficam em `~/netmask-testes/`, sempre.

---

## 7. Referência rápida — onde está o quê no projeto

```
core.py          -> motor generico (tokens, IP/IPv6/MAC)
vendors.py       -> padroes por plataforma + deteccao automatica (VENDOR_SIGNATURES)
crypto_utils.py  -> encriptacao do mapping.json
netmask.py       -> CLI (o que corres no terminal)
imc_mask.py      -> CLI separado, mascaramento de CSVs de inventario IMC
tests/           -> testes automaticos (pytest)
docs/roadmap.md          -> historico e proximos passos do projeto
docs/interview-notes.md  -> como falar deste projeto numa entrevista
docs/cheatsheet.md       -> este ficheiro
```
