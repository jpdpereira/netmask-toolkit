#!/usr/bin/env python3
"""
netmask.py - CLI. Mascara e reverte informacao sensivel em ficheiros de
configuracao de rede multi-vendor (show running-config, show logs,
show cdp/lldp neighbors, etc.), para partilha segura com IA ou terceiros.

A logica generica (tokenizacao, IP/IPv6/MAC) esta em core.py.
Os padroes especificos de cada plataforma (e a deteccao automatica de
vendor) estao em vendors.py.
A encriptacao opcional do mapping.json esta em crypto_utils.py.

Fluxo de uso seguro:
    1. mask   -> gera versao mascarada (partilhavel com qualquer IA/terceiro)
                 + ficheiro de mapping (fica SEMPRE local, nunca se partilha)
    2. Usa o ficheiro mascarado onde quiseres (Claude, ChatGPT, colegas, etc.)
    3. unmask -> reconstroi a informacao real a partir da resposta/output
                 usando o mesmo ficheiro de mapping

Exemplos:
    # ficheiro unico, vendor explicito
    python netmask.py mask -i show_run.txt -o show_run_masked.txt -m mapping.json --vendor cisco

    # deteccao automatica de vendor
    python netmask.py mask -i show_run.txt -o show_run_masked.txt -m mapping.json --vendor auto

    # diretorio inteiro (todos os *.txt), com um mapping.json partilhado
    python netmask.py mask -i ./configs_reais/ -o ./configs_mascaradas/ -m mapping.json --vendor auto

    # pipe (stdin/stdout)
    cat show_run.txt | python netmask.py mask -i - -o - -m mapping.json --vendor cisco > masked.txt

    # mapping cifrado com password
    python netmask.py mask -i show_run.txt -o masked.txt -m mapping.json --vendor cisco --encrypt

    python netmask.py unmask -i masked.txt -o real.txt -m mapping.json

O mapping.json (ou mapping.json cifrado) e a chave para reverter --
protege-o como uma credencial.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from core import Masker
from crypto_utils import decrypt_mapping, encrypt_mapping, is_encrypted_mapping, prompt_password
from vendors import VENDOR_PROFILES, detect_vendor, get_profile

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("netmask")


# ---------- resolucao de vendor ----------
def _resolve_vendor(vendor_arg, text):
    if vendor_arg != "auto":
        return get_profile(vendor_arg), vendor_arg

    detected, score = detect_vendor(text)
    if detected is None:
        log.warning("Deteccao automatica nao encontrou nenhuma assinatura conhecida; a usar 'generic'.")
        return get_profile("generic"), "generic"

    log.info("Vendor detetado automaticamente: %s (score=%d)", detected, score)
    return get_profile(detected), detected


# ---------- I/O helpers (ficheiro unico / stdin-stdout) ----------
def _read_input(input_arg):
    if input_arg == "-":
        return sys.stdin.read()
    path = Path(input_arg)
    if not path.exists():
        log.error("Ficheiro de input nao existe: %s", path)
        raise SystemExit(1)
    return path.read_text(encoding="utf-8", errors="replace")


def _write_output(output_arg, text):
    if output_arg == "-":
        sys.stdout.write(text)
    else:
        Path(output_arg).write_text(text, encoding="utf-8")


# ---------- mask ----------
def cmd_mask(args):
    input_path = None if args.input == "-" else Path(args.input)

    if input_path is not None and input_path.is_dir():
        _mask_directory(args, input_path)
        return

    text = _read_input(args.input)
    profile, vendor_used = _resolve_vendor(args.vendor, text)

    masker = Masker()
    masked = masker.mask(text, profile)

    if args.dry_run:
        log.info("[DRY-RUN] vendor=%s -> %d valores seriam mascarados. Nada foi escrito.", vendor_used, len(masker.mapping))
        for token, value in masker.mapping.items():
            log.info("  %s -> %s", token, value)
        return

    _write_output(args.output, masked)
    _save_mapping(masker.mapping, args.map, args.encrypt)
    log.info("Ficheiro mascarado: %s", args.output)
    log.info("Mapping guardado (protege este ficheiro!): %s", args.map)
    log.info("%d valores mascarados (vendor=%s).", len(masker.mapping), vendor_used)


def _mask_directory(args, input_dir):
    files = sorted(input_dir.glob("*.txt"))
    if not files:
        log.error("Nenhum ficheiro .txt encontrado em %s", input_dir)
        raise SystemExit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # um Masker partilhado por todos os ficheiros: o mesmo valor real (ex:
    # um vizinho LLDP que aparece em varios show run) mapeia sempre para o
    # mesmo token em todo o lote.
    masker = Masker()
    total_files = 0

    for file_path in files:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        profile, vendor_used = _resolve_vendor(args.vendor, text)
        masked = masker.mask(text, profile)

        if not args.dry_run:
            (output_dir / file_path.name).write_text(masked, encoding="utf-8")
        total_files += 1
        log.info("  %s -> vendor=%s", file_path.name, vendor_used)

    if args.dry_run:
        log.info("[DRY-RUN] %d ficheiros processados, %d valores seriam mascarados no total.", total_files, len(masker.mapping))
        return

    _save_mapping(masker.mapping, args.map, args.encrypt)
    log.info("%d ficheiros mascarados em: %s", total_files, output_dir)
    log.info("Mapping guardado (protege este ficheiro!): %s", args.map)
    log.info("%d valores mascarados no total.", len(masker.mapping))


def _save_mapping(mapping, map_path, encrypt):
    if encrypt:
        password = prompt_password(confirm=True)
        encrypt_mapping(mapping, map_path, password)
    else:
        Path(map_path).write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------- unmask ----------
def _load_mapping(map_path):
    map_path = Path(map_path)
    if not map_path.exists():
        log.error("Ficheiro de mapping nao existe: %s", map_path)
        raise SystemExit(1)

    if is_encrypted_mapping(map_path):
        password = prompt_password()
        try:
            return decrypt_mapping(map_path, password)
        except ValueError as exc:
            log.error(str(exc))
            raise SystemExit(1)

    return json.loads(map_path.read_text(encoding="utf-8"))


def cmd_unmask(args):
    mapping = _load_mapping(args.map)
    masker = Masker()
    masker.mapping = mapping

    input_path = None if args.input == "-" else Path(args.input)

    if input_path is not None and input_path.is_dir():
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        files = sorted(input_path.glob("*.txt"))
        if not files:
            log.error("Nenhum ficheiro .txt encontrado em %s", input_path)
            raise SystemExit(1)
        for file_path in files:
            text = file_path.read_text(encoding="utf-8", errors="replace")
            original = masker.unmask(text)
            (output_dir / file_path.name).write_text(original, encoding="utf-8")
            log.info("  %s revertido", file_path.name)
        log.info("%d ficheiros revertidos em: %s", len(files), output_dir)
        return

    text = _read_input(args.input)
    original = masker.unmask(text)
    _write_output(args.output, original)
    log.info("Ficheiro revertido: %s", args.output)


def main():
    parser = argparse.ArgumentParser(description="Mascara/reverte informacao sensivel em configs de rede multi-vendor.")
    sub = parser.add_subparsers(dest="command", required=True)

    vendor_choices = sorted(VENDOR_PROFILES) + ["auto"]

    p_mask = sub.add_parser("mask", help="Mascara um ficheiro, diretorio, ou stdin com informacao real")
    p_mask.add_argument("-i", "--input", required=True, help="Ficheiro, diretorio (*.txt), ou '-' para stdin")
    p_mask.add_argument("-o", "--output", required=True, help="Ficheiro, diretorio, ou '-' para stdout")
    p_mask.add_argument("-m", "--map", required=True, help="Ficheiro onde guardar o mapping (NUNCA partilhar)")
    p_mask.add_argument("--vendor", default="generic", choices=vendor_choices,
                         help="Plataforma de origem ('auto' deteta automaticamente; default: generic)")
    p_mask.add_argument("--dry-run", action="store_true",
                         help="Mostra quantos itens seriam mascarados, sem escrever ficheiros")
    p_mask.add_argument("--encrypt", action="store_true",
                         help="Cifra o mapping.json com uma password (pedida interativamente)")
    p_mask.set_defaults(func=cmd_mask)

    p_unmask = sub.add_parser("unmask", help="Reverte um ficheiro, diretorio, ou stdin mascarado")
    p_unmask.add_argument("-i", "--input", required=True, help="Ficheiro, diretorio (*.txt), ou '-' para stdin")
    p_unmask.add_argument("-o", "--output", required=True, help="Ficheiro, diretorio, ou '-' para stdout")
    p_unmask.add_argument("-m", "--map", required=True,
                           help="Ficheiro de mapping (deteta automaticamente se esta cifrado)")
    p_unmask.set_defaults(func=cmd_unmask)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
