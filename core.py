"""
core.py - motor generico de mascaramento/reversao de dados sensiveis.

Este modulo NAO conhece sintaxe de nenhum vendor especifico. Contem apenas:
- gestao de tokens (Masker): garante que o mesmo valor real mapeia sempre
  para o mesmo token, e vice-versa na reversao.
- padroes "simples", universais a qualquer plataforma: IPv4, IPv6, MAC.
- a API publica mask()/unmask(), que recebe os padroes especificos de
  vendor (hostname, description, LLDP/CDP) definidos em vendors.py.

Separar isto de vendors.py e o que permite adicionar suporte a uma nova
plataforma sem tocar neste ficheiro.
"""

import ipaddress
import json
import re
from pathlib import Path
from typing import ClassVar


class Masker:
    def __init__(self):
        self.mapping = {}   # token -> valor real
        self.reverse = {}   # valor real -> token
        self.counters = {}  # categoria -> proximo numero

    # ---------- gestao de tokens ----------
    def _next_token(self, category):
        n = self.counters.get(category, 0) + 1
        self.counters[category] = n
        return f"{category}_{n:03d}"

    def _get_token(self, category, value):
        if value in self.reverse:
            return self.reverse[value]
        token = self._next_token(category)
        self.reverse[value] = token
        self.mapping[token] = value
        return token

    # ---------- padroes simples (universais, qualquer vendor) ----------
    # valores default/tecnicos que nunca sao mascarados (evita ruido)
    KEEP_VALUES: ClassVar[frozenset] = frozenset({"DEFAULT_VLAN"})
    # categorias cujo valor, aprendido numa linha com contexto, e propagado
    # ao resto do texto (tabelas de show, prompts, nomes de ficheiro)
    PROPAGATE_CATEGORIES: ClassVar[frozenset] = frozenset({
        "HOSTNAME", "DESC", "NEIGHBOR", "SNMP_COMMUNITY", "SNMP_CONTACT",
        "SNMP_LOCATION", "SNMPV3_USER", "USERNAME", "AAA_KEY",
    })
    PROPAGATE_MIN_LEN: ClassVar[int] = 4  # evita propagar nomes curtos/genericos

    # tabelas de largura fixa sem "Campo :" para ancorar regex:
    # (regex do cabecalho, {nome da coluna: categoria do token})
    TABLE_COLUMNS: ClassVar[list] = [
        # AOS-Switch: show lldp info remote-device (resumo)
        (re.compile(r"^[ \t]*LocalPort[ \t]*\|.*\bSysName\b"), {"PortDescr": "PORTID", "SysName": "NEIGHBOR"}),
    ]

    SIMPLE_PATTERNS: ClassVar[list] = [
        ("MAC", re.compile(r"\b[0-9A-Fa-f]{2}([:-][0-9A-Fa-f]{2}){5}\b")),
        ("MAC", re.compile(r"\b[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4}\b")),
        ("MAC", re.compile(r"\b[0-9A-Fa-f]{6}-[0-9A-Fa-f]{6}\b")),  # HPE AOS-Switch: xxxxxx-xxxxxx
        ("STACK_ID", re.compile(r"\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{8}\b")),  # show stacking WC.16.10: 0001+MAC em 8-8
        # formato separado por espacos, comum em ChassisId de HP/Aruba (ex: "ec eb b8 a8 99 00")
        ("MAC", re.compile(r"\b[0-9A-Fa-f]{2}(?: [0-9A-Fa-f]{2}){5}\b")),
        # candidato amplo para IPv6 (inclui notacao comprimida "::");
        # valida-se a seguir com o modulo ipaddress para evitar falsos positivos
        ("IPV6", re.compile(r"\b[0-9A-Fa-f]{0,4}(?::[0-9A-Fa-f]{0,4}){2,7}(?:/\d{1,3})?\b")),
        ("IP", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b")),
    ]

    def _mask_simple_patterns(self, text):
        for category, pattern in self.SIMPLE_PATTERNS:
            def repl(m, category=category):
                val = m.group(0)
                if category == "IP":
                    try:
                        ipaddress.IPv4Address(val.split("/")[0])
                    except ValueError:
                        return val
                if category == "IPV6":
                    try:
                        ipaddress.IPv6Address(val.split("/")[0])
                    except ValueError:
                        return val
                return self._get_token(category, val)
            text = pattern.sub(repl, text)
        return text

    # ---------- padroes contextuais especificos de vendor ----------
    def _mask_line_patterns(self, text, line_patterns):
        """
        line_patterns: lista de tuplos (categoria, regex_compilado, usa_aspas)
        vinda de vendors.py. O regex tem sempre 2 grupos: prefixo e valor
        (sem aspas, mesmo quando usa_aspas=True -- as aspas sao geridas aqui).
        """
        for category, pattern, wrap_quotes in line_patterns:
            def repl(m, category=category, wrap_quotes=wrap_quotes):
                prefix, val = m.group(1), m.group(2).strip()
                if val in self.KEEP_VALUES:
                    return m.group(0)
                token = self._get_token(category, val)
                if wrap_quotes:
                    return f'{prefix}"{token}"'
                return f"{prefix}{token}"
            text = pattern.sub(repl, text)
        return text

    def _mask_table_columns(self, text):
        """Mascara colunas de tabelas de largura fixa (ex: SysName no resumo do
        show lldp info remote-device). Fronteiras das colunas vem da linha
        separadora ('--- + ---'), com fallback para as posicoes do cabecalho.
        Linhas de dados lidas ate a primeira linha vazia (ou sem '|', se o
        cabecalho o tiver). Colunas da direita para a esquerda, para que a
        troca valor->token nao desloque os offsets das restantes."""
        lines = text.split("\n")
        i = 0
        while i < len(lines):
            spec = next((cols for hdr, cols in self.TABLE_COLUMNS if hdr.match(lines[i])), None)
            if spec is None or i + 1 >= len(lines):
                i += 1
                continue
            header = list(re.finditer(r"\S+", lines[i]))
            sep = lines[i + 1]
            is_sep = bool(sep.strip()) and set(sep.strip()) <= set("-+ ")
            groups = list(re.finditer(r"\S+", sep)) if is_sep else []
            bounds = groups if len(groups) == len(header) else header
            starts = [b.start() for b in bounds]
            spans = [
                (starts[idx], starts[idx + 1] if idx + 1 < len(starts) else None, spec[h.group(0)])
                for idx, h in enumerate(header)
                if h.group(0) in spec
            ]
            needs_pipe = "|" in lines[i]
            j = i + (2 if is_sep else 1)
            while j < len(lines) and lines[j].strip() and (not needs_pipe or "|" in lines[j]):
                row = lines[j]
                for start, end, category in sorted(spans, reverse=True):
                    cell = row[start:end]
                    value = cell.strip()
                    if not value or value in self.KEEP_VALUES:
                        continue
                    token = self._get_token(category, value)
                    tail = row[end:] if end is not None else ""
                    row = row[:start] + cell.replace(value, token, 1) + tail
                lines[j] = row
                j += 1
            i = j
        return "\n".join(lines)

    def _propagate_known_values(self, text):
        """Propaga valores ja aprendidos em linhas com contexto (hostname,
        nomes de porta/VLAN, communities, users, keys) a qualquer outro sitio
        onde aparecam soltos -- tabelas de show, prompts, nomes de ficheiro.
        Fronteira: nao colado a alfanumerico nem '-'; o '_' conta como
        separador (ex: 'SW-X_running.cfg')."""
        values = [
            v for tok, v in self.mapping.items()
            if tok.rsplit("_", 1)[0] in self.PROPAGATE_CATEGORIES
            and (len(v) >= self.PROPAGATE_MIN_LEN or tok.startswith("HOSTNAME_"))  # hostname curto (SW1) tambem
            and v not in self.KEEP_VALUES
        ]
        for value in sorted(values, key=len, reverse=True):  # longos primeiro
            token = self.reverse[value]
            pattern = re.compile(r"(?<![A-Za-z0-9-])" + re.escape(value) + r"(?![A-Za-z0-9-])")
            text = pattern.sub(lambda m, t=token: t, text)
        return text

    # ---------- API publica ----------
    def mask(self, text, line_patterns):
        text = self._mask_line_patterns(text, line_patterns)  # 1. contexto do vendor
        text = self._mask_table_columns(text)                 # 1b. tabelas de largura fixa
        text = self._propagate_known_values(text)             # 2. propaga valores aprendidos
        text = self._mask_simple_patterns(text)                 # 3. IP/MAC genericos
        return text

    def unmask(self, text):
        # tokens longos primeiro; fronteira aceita '_' (ex: HOSTNAME_001_running.cfg)
        for token in sorted(self.mapping, key=len, reverse=True):
            value = self.mapping[token]
            text = re.sub(r"(?<![A-Za-z0-9])" + re.escape(token) + r"(?!\d)", lambda m, v=value: v, text)
        return text

    def save_mapping(self, path):
        Path(path).write_text(json.dumps(self.mapping, indent=2, ensure_ascii=False), encoding="utf-8")

    def load_mapping(self, path):
        self.mapping = json.loads(Path(path).read_text(encoding="utf-8"))
