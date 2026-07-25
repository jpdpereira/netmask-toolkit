# Nota para entrevista

Como enquadrar o `netmask-toolkit` numa entrevista tecnica de
NetDevOps/Network Automation.

## O problema que resolve

Equipas de rede cada vez mais usam LLMs para analisar configs, logs e
topologias. Colar um `show running-config` real numa ferramenta externa
expoe IPs, MACs, hostnames e desenho da rede a um terceiro. Isto e um
problema de exfiltracao de dados, nao muito diferente de colar credenciais
num prompt.

## A solucao (o padrao, nao so a ferramenta)

Tokenizacao reversivel: cada valor sensivel e substituido por um token
opaco e consistente (`IP_001`, `HOSTNAME_001`, ...), guardado num mapping
que nunca sai da maquina local. A analise acontece sobre dados mascarados;
a reversao acontece so no fim, localmente. Isto e o mesmo principio usado
em pipelines de dados regulados (PCI-DSS, HIPAA) antes de dados irem para
ambientes de teste ou terceiros -- so que aplicado a configs de rede.

## Decisoes de arquitetura que valem a pena mencionar

- **Separacao core/vendors**: o motor de tokenizacao (`core.py`) nao
  conhece sintaxe de nenhuma plataforma; o conhecimento de dominio
  (Cisco, Aruba, Comware, Juniper, FortiOS, CheckPoint, UniFi) vive todo
  em `vendors.py`. Isto significa que adicionar suporte a um vendor novo
  nunca implica tocar na logica generica -- so o ficheiro de dominio.
- **Consistencia de tokens**: o mesmo valor real mapeia sempre para o
  mesmo token, mesmo em modo diretorio com varios ficheiros. Isto
  preserva relacoes (ex: um vizinho LLDP que aparece em varios `show`
  outputs continua identificavel como "o mesmo dispositivo", so que sem
  expor o nome real).
- **Seguranca por defeito**: o `.gitignore` bloqueia o mapping por
  omissao; o mapping pode ser cifrado (Fernet + PBKDF2-HMAC-SHA256,
  480k iteracoes, seguindo a recomendacao OWASP 2023); a password nunca e
  guardada em disco.
- **Testes como validacao de seguranca**: os testes nao validam so que o
  codigo "funciona" -- validam explicitamente que o texto mascarado *nao
  contem* os valores reais, e que o round-trip mask/unmask e sempre
  perfeito (nenhuma perda de informacao).

## Perguntas tipicas que isto pode gerar (e como responder)

**"Porque nao usar so uma ferramenta pronta de anonimizacao de dados?"**
Porque a estrutura de uma config de rede e muito especifica por vendor
(onde esta o hostname, onde esta a descricao de porta) -- uma ferramenta
generica de deteccao de PII nao sabe que "PortDescr" na Aruba e o mesmo
conceito que "description" na Cisco. O dominio importa.

**"Como garantes que nao ficam falsos negativos (dados sensiveis que
escapam a mascara)?"**
Nao garanto 100% -- e uma heuristica baseada em regex, nao um parser
formal da sintaxe de cada vendor. Mitigo isso com testes de round-trip
por vendor e com `--dry-run` para inspecionar antes de partilhar
qualquer coisa. Numa proxima iteracao, o passo natural seria validar
contra fixtures reais (anonimizadas) do ambiente de producao.

**"Isto escala?"**
Para o caso de uso (analise pontual, ficheiros na ordem dos KB/poucos MB)
sim -- e regex simples sobre texto, sem dependencias pesadas. Nao foi
desenhado para processar terabytes de logs; para isso a abordagem seria
diferente (streaming, ferramentas dedicadas de deteccao de PII).
