#!/usr/bin/env python3
"""
netmask.py - CLI. Mascara e reverte informacao sensivel em ficheiros de
configuracao de rede multi-vendor (show running-config, show logs,
show cdp/lldp neighbors, etc.), para partilha segura com IA ou terceiros.

A logica generica (tokenizacao, IP/IPv6/MAC) esta em core.py.
Os padroes especificos de cada plataforma estao em vendors.py -- e la que
se adiciona suporte a um novo vendor.

Fluxo de uso seguro:
    1. mask   -> gera versao mascarada (partilhavel com qualquer IA/terceiro)
                 + ficheiro de mapping (fica SEMPRE local, nunca se partilha)
    2. Usa o ficheiro mascarado onde quiseres (Claude, ChatGPT, colegas, etc.)
    3. unmask -> reconstroi a informacao real a partir da resposta/output
                 usando o mesmo ficheiro de mapping

Uso:
    python netmask.py mask   -i config_real.txt   -o config_masked.txt -m mapping.json --vendor cisco
    python netmask.py unmask -i config_masked.txt -o config_real.txt   -m mapping.json

O mapping.json e a chave para reverter -- protege-o como uma credencial.
"""

import argparse
import logging
from pathlib import Path

from core import Masker
from vendors import VENDOR_PROFILES, get_profile

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("netmask")


def cmd_mask(args):
    input_path = Path(args.input)
    if not input_path.exists():
        log.error("Ficheiro de input nao existe: %s", input_path)
        raise SystemExit(1)

    try:
        profile = get_profile(args.vendor)
    except ValueError as exc:
        log.error(str(exc))
        raise SystemExit(1)

    text = input_path.read_text(encoding="utf-8", errors="replace")
    masker = Masker()
    masked = masker.mask(text, profile)

    if args.dry_run:
        log.info("[DRY-RUN] vendor=%s -> %d valores seriam mascarados. Nada foi escrito.", args.vendor, len(masker.mapping))
        for token, value in masker.mapping.items():
            log.info("  %s -> %s", token, value)
        return

    Path(args.output).write_text(masked, encoding="utf-8")
    masker.save_mapping(args.map)
    log.info("Ficheiro mascarado: %s", args.output)
    log.info("Mapping guardado (protege este ficheiro!): %s", args.map)
    log.info("%d valores mascarados (vendor=%s).", len(masker.mapping), args.vendor)


def cmd_unmask(args):
    map_path = Path(args.map)
    input_path = Path(args.input)
    if not map_path.exists():
        log.error("Ficheiro de mapping nao existe: %s", map_path)
        raise SystemExit(1)
    if not input_path.exists():
        log.error("Ficheiro de input nao existe: %s", input_path)
        raise SystemExit(1)

    masker = Masker()
    masker.load_mapping(args.map)
    text = input_path.read_text(encoding="utf-8", errors="replace")
    original = masker.unmask(text)
    Path(args.output).write_text(original, encoding="utf-8")
    log.info("Ficheiro revertido: %s", args.output)


def main():
    parser = argparse.ArgumentParser(description="Mascara/reverte informacao sensivel em configs de rede multi-vendor.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_mask = sub.add_parser("mask", help="Mascara um ficheiro com informacao real")
    p_mask.add_argument("-i", "--input", required=True)
    p_mask.add_argument("-o", "--output", required=True)
    p_mask.add_argument("-m", "--map", required=True, help="Ficheiro onde guardar o mapping (NUNCA partilhar)")
    p_mask.add_argument("--vendor", default="generic", choices=sorted(VENDOR_PROFILES),
                         help="Plataforma de origem do ficheiro (default: generic)")
    p_mask.add_argument("--dry-run", action="store_true",
                         help="Mostra quantos itens seriam mascarados, sem escrever ficheiros")
    p_mask.set_defaults(func=cmd_mask)

    p_unmask = sub.add_parser("unmask", help="Reverte um ficheiro mascarado para a informacao real")
    p_unmask.add_argument("-i", "--input", required=True)
    p_unmask.add_argument("-o", "--output", required=True)
    p_unmask.add_argument("-m", "--map", required=True)
    p_unmask.set_defaults(func=cmd_unmask)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
