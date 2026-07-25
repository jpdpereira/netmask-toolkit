#!/usr/bin/env python3
"""
netmask.py - Mascara e reverte informacao sensivel em ficheiros de configuracao
de rede (show running-config, show logs, show cdp/lldp neighbors, etc.)

Fluxo de uso seguro:
    1. mask   -> gera versao mascarada (partilhavel com qualquer IA/terceiro)
                 + ficheiro de mapping (fica SEMPRE local, nunca se partilha)
    2. Usa o ficheiro mascarado onde quiseres (Claude, ChatGPT, colegas, etc.)
    3. unmask -> reconstroi a informacao real a partir da resposta/output
                 usando o mesmo ficheiro de mapping

Uso:
    python netmask.py mask   -i config_real.txt   -o config_masked.txt -m mapping.json
    python netmask.py unmask -i config_masked.txt -o config_real.txt   -m mapping.json

O mapping.json e a chave para reverter -- protege-o como uma credencial.
"""

import re
import json
import argparse
import ipaddress
from pathlib import Path


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

    # ---------- padroes simples (aplicados em qualquer sitio do texto) ----------
    SIMPLE_PATTERNS = [
        ("MAC", re.compile(r"\b[0-9A-Fa-f]{2}([:-][0-9A-Fa-f]{2}){5}\b")),
        ("MAC", re.compile(r"\b[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4}\b")),
        # candidato amplo (inclui notacao comprimida "::"); valida-se a seguir com ipaddress
        ("IPV6", re.compile(r"\b[0-9A-Fa-f]{0,4}(?::[0-9A-Fa-f]{0,4}){2,7}(?:/\d{1,3})?\b")),
        ("IP", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b")),
    ]

    def _mask_simple_patterns(self, text):
        for category, pattern in self.SIMPLE_PATTERNS:
            def repl(m, category=category):
                val = m.group(0)
                # valida antes de mascarar, para evitar falsos positivos
                # (ex: versoes de firmware tipo 16.11.0029)
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

    # ---------- padroes contextuais (linha inteira) ----------
    LINE_PATTERNS = [
        ("HOSTNAME", re.compile(r"^(\s*(?:hostname|sysname)\s+)(\S+)", re.MULTILINE | re.IGNORECASE)),
        ("DESC", re.compile(r"^(\s*description\s+)(.+)$", re.MULTILINE | re.IGNORECASE)),
        ("NEIGHBOR", re.compile(r"^(\s*(?:System Name|Device ID)\s*[:\-]\s*)(\S+)", re.MULTILINE | re.IGNORECASE)),
        ("PORTID", re.compile(r"^(\s*Port (?:ID|Description)\s*[:\-]\s*)(.+)$", re.MULTILINE | re.IGNORECASE)),
    ]

    def _mask_line_patterns(self, text):
        for category, pattern in self.LINE_PATTERNS:
            def repl(m, category=category):
                prefix, val = m.group(1), m.group(2).strip()
                token = self._get_token(category, val)
                return f"{prefix}{token}"
            text = pattern.sub(repl, text)
        return text

    def _mask_known_hostname(self, text):
        """Depois de identificar o hostname principal (via 'hostname'/'sysname'),
        substitui-o tambem onde aparecer solto -- prompts (SW01#), banners, etc."""
        hostnames = [v for tok, v in self.mapping.items() if tok.startswith("HOSTNAME_")]
        for hostname in hostnames:
            token = self.reverse[hostname]
            pattern = re.compile(r"\b" + re.escape(hostname) + r"\b")
            text = pattern.sub(token, text)
        return text

    # ---------- API publica ----------
    def mask(self, text):
        text = self._mask_line_patterns(text)    # 1. contexto: hostname/desc/lldp
        text = self._mask_known_hostname(text)    # 2. propaga hostname a prompts/banners
        text = self._mask_simple_patterns(text)   # 3. IP/MAC genericos
        return text

    def unmask(self, text):
        for token, value in self.mapping.items():
            text = re.sub(r"\b" + re.escape(token) + r"\b", lambda m, v=value: v, text)
        return text

    def save_mapping(self, path):
        Path(path).write_text(json.dumps(self.mapping, indent=2, ensure_ascii=False), encoding="utf-8")

    def load_mapping(self, path):
        self.mapping = json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Mascara/reverte informacao sensivel em configs de rede.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_mask = sub.add_parser("mask", help="Mascara um ficheiro com informacao real")
    p_mask.add_argument("-i", "--input", required=True)
    p_mask.add_argument("-o", "--output", required=True)
    p_mask.add_argument("-m", "--map", required=True, help="Ficheiro onde guardar o mapping (NUNCA partilhar)")

    p_unmask = sub.add_parser("unmask", help="Reverte um ficheiro mascarado para a informacao real")
    p_unmask.add_argument("-i", "--input", required=True)
    p_unmask.add_argument("-o", "--output", required=True)
    p_unmask.add_argument("-m", "--map", required=True)

    args = parser.parse_args()

    if args.command == "mask":
        text = Path(args.input).read_text(encoding="utf-8", errors="replace")
        masker = Masker()
        masked = masker.mask(text)
        Path(args.output).write_text(masked, encoding="utf-8")
        masker.save_mapping(args.map)
        print(f"[OK] Ficheiro mascarado: {args.output}")
        print(f"[OK] Mapping guardado (protege este ficheiro!): {args.map}")
        print(f"[INFO] {len(masker.mapping)} valores mascarados.")

    elif args.command == "unmask":
        masker = Masker()
        masker.load_mapping(args.map)
        text = Path(args.input).read_text(encoding="utf-8", errors="replace")
        original = masker.unmask(text)
        Path(args.output).write_text(original, encoding="utf-8")
        print(f"[OK] Ficheiro revertido: {args.output}")


if __name__ == "__main__":
    main()
