#!/usr/bin/env python3
"""
imc_mask.py - Pseudonimizacao ESTRUTURAL e determinista de exports CSV do
HPE IMC (Intelligent Management Center), para o projeto de validacao de
inventario (Fase 0).

Diferente do netmask.py (que mascara texto livre de configs de rede),
este script trabalha por COLUNA de um CSV, com uma regra por campo:

- IP Address     -> mascara so os 2 primeiros octetos (mantem 3o/4o),
                     mapeamento consistente por prefixo /16
                     (10.45.12.7 -> 10.1.12.7, sempre o mesmo 10.45. -> 10.1.)
- Location       -> substitui por codigo sequencial (SITE-A, SITE-B, ...)
- Serial Number  -> substitui por token sequencial (SN-0001, SN-0002, ...)
- Rack           -> substitui por token sequencial (RACK-01, RACK-02, ...)
- Contact        -> REMOVIDA por completo (dados pessoais, sem valor analitico)
- todas as outras colunas (Status, Model, Vendor, CPU/Memory Usage,
  datas, etc.) -> mantidas 100% intactas

O mapping (imc_mapping.json) e PERSISTENTE entre execucoes: se voltares a
correr o script com um export mais recente, o mesmo IP/site/serial
mantem sempre o mesmo valor mascarado. Nunca partilhes esse ficheiro --
e a tabela de correspondencia para traduzires as conclusoes de volta.

Uso:
    python3 imc_mask.py mask -i devices.csv -o devices_masked.csv -m imc_mapping.json
"""

import argparse
import csv
import json
import logging
import re
import string
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("imc_mask")

# Coluna removida por completo (nao mascarada -- apagada do output)
DROP_COLUMNS = ["Contact"]

# Colunas conhecidas que devem ficar 100% intactas (usado so para aviso
# de colunas "nao previstas" na especificacao -- nao bloqueia nada)
KNOWN_KEEP_COLUMNS = {
    "Status", "Model", "Vendor", "Device Category",
    "CPU Usage (%)", "Memory Usage (%)", "Response Time of Device (ms)",
    "Device Unreachability Proportion (%)",
    "IP Datagram Receiving Rate (datagrams/s)",
    "IP Datagram Forwarding Rate (datagrams/s)",
    "Discarded Proportion of Input IP Datagrams (%)",
    "Discarded Proportion of Output IP Datagrams (%)",
    "Software Version",
}

IP_COLUMN = "IP Address"

# "Device Label" traz por vezes IPs colados ao hostname, ex:
# "10.77.1.6( SW-LAB-CORE-01)(10.77.1.8)" -- gap real encontrado em export.
# Mascara-se so os IPs embutidos, o hostname fica intacto (pedido explicito).
DEVICE_LABEL_COLUMN = "Device Label"
_IPV4_REGEX = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")


def _site_code(n):
    """n e 1-based: 1->SITE-A, 2->SITE-B, ..., 26->SITE-Z, 27->SITE-AA, ..."""
    letters = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters = string.ascii_uppercase[rem] + letters
    return f"SITE-{letters}"


def _detect_dialect(path):
    """Deteta se o CSV usa ',' ou ';' como separador (Excel PT usa ';')."""
    with open(path, encoding="utf-8-sig") as f:
        sample = f.read(4096)
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        log.warning("Nao foi possivel detetar o separador do CSV, a assumir ','.")
        return csv.excel


class IMCMapper:
    """Guarda e persiste o mapeamento entre valores reais e mascarados."""

    def __init__(self):
        self.ip_prefix_map = {}
        self.location_map = {}
        self.serial_map = {}
        self.rack_map = {}
        self._counters = {"ip_prefix": 0, "location": 0, "serial": 0, "rack": 0}

    # ---------- persistencia ----------
    def load(self, path):
        path = Path(path)
        if not path.exists():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        self.ip_prefix_map = data.get("ip_prefix_map", {})
        self.location_map = data.get("location_map", {})
        self.serial_map = data.get("serial_map", {})
        self.rack_map = data.get("rack_map", {})
        self._counters = data.get("_counters", self._counters)

    def save(self, path):
        data = {
            "ip_prefix_map": self.ip_prefix_map,
            "location_map": self.location_map,
            "serial_map": self.serial_map,
            "rack_map": self.rack_map,
            "_counters": self._counters,
        }
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # ---------- IP (mascaramento parcial: so os 2 primeiros octetos) ----------
    def mask_ip(self, value):
        value = value.strip()
        if not value:
            return value
        parts = value.split(".")
        if len(parts) != 4 or not all(p.isdigit() for p in parts):
            log.warning("Valor em '%s' nao parece IPv4 valido, mantido tal e qual: %r", IP_COLUMN, value)
            return value

        prefix = f"{parts[0]}.{parts[1]}"
        if prefix not in self.ip_prefix_map:
            self._counters["ip_prefix"] += 1
            self.ip_prefix_map[prefix] = f"10.{self._counters['ip_prefix']}"
        masked_prefix = self.ip_prefix_map[prefix]
        return f"{masked_prefix}.{parts[2]}.{parts[3]}"

    def mask_embedded_ips(self, text):
        """Mascara qualquer IPv4 embutido num texto livre (ex: 'Device Label'
        que traz IPs colados ao hostname), usando o mesmo mapeamento de
        prefixo da coluna IP Address (consistente com ela). O resto do
        texto (hostname, parenteses, etc.) fica intacto."""
        if not text:
            return text
        return _IPV4_REGEX.sub(lambda m: self.mask_ip(m.group(0)), text)

    # ---------- campos genericos (tokenizacao sequencial e consistente) ----------
    def _get_or_create(self, mapping, counter_key, value, formatter):
        if value not in mapping:
            self._counters[counter_key] += 1
            mapping[value] = formatter(self._counters[counter_key])
        return mapping[value]

    def mask_location(self, value):
        value = value.strip()
        if not value:
            return value
        return self._get_or_create(self.location_map, "location", value, _site_code)

    def mask_serial(self, value):
        value = value.strip()
        if not value:
            return value
        return self._get_or_create(self.serial_map, "serial", value, lambda n: f"SN-{n:04d}")

    def mask_rack(self, value):
        value = value.strip()
        if not value:
            return value
        return self._get_or_create(self.rack_map, "rack", value, lambda n: f"RACK-{n:02d}")


FIELD_MASKERS = {
    "Location": IMCMapper.mask_location,
    "Serial Number": IMCMapper.mask_serial,
    "Rack": IMCMapper.mask_rack,
}


def _skip_preamble_lines(f, delimiter):
    """Salta linhas iniciais que nao parecem CSV valido -- alguns exports do
    IMC colam uma linha de resumo antes do cabecalho real, ex:
    'Exported 402 records.' -- gap real encontrado ao testar com export real."""
    while True:
        pos = f.tell()
        line = f.readline()
        if not line:
            f.seek(pos)
            return
        if delimiter in line:
            f.seek(pos)
            return
        log.warning("Linha ignorada antes do cabecalho (nao parece CSV): %r", line.strip())


def mask_devices_csv(input_path, output_path, mapper):
    dialect = _detect_dialect(input_path)

    with open(input_path, newline="", encoding="utf-8-sig") as f_in:
        _skip_preamble_lines(f_in, dialect.delimiter)
        reader = csv.DictReader(f_in, dialect=dialect)
        fieldnames_in = reader.fieldnames or []

        unknown = [
            c for c in fieldnames_in
            if c not in DROP_COLUMNS and c not in FIELD_MASKERS
            and c != IP_COLUMN and c != DEVICE_LABEL_COLUMN and c not in KNOWN_KEEP_COLUMNS
        ]
        if unknown:
            log.warning("Colunas nao previstas na especificacao (mantidas tal e qual, revê a checklist): %s", unknown)

        fieldnames_out = [c for c in fieldnames_in if c not in DROP_COLUMNS]

        rows_out = []
        for row in reader:
            new_row = {}
            for col in fieldnames_out:
                value = row.get(col, "") or ""
                if col == IP_COLUMN:
                    new_row[col] = mapper.mask_ip(value)
                elif col == DEVICE_LABEL_COLUMN:
                    new_row[col] = mapper.mask_embedded_ips(value)
                elif col in FIELD_MASKERS:
                    new_row[col] = FIELD_MASKERS[col](mapper, value)
                else:
                    new_row[col] = value
            rows_out.append(new_row)

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames_out, delimiter=dialect.delimiter)
        writer.writeheader()
        writer.writerows(rows_out)

    return len(rows_out)


def main():
    parser = argparse.ArgumentParser(description="Pseudonimizacao estrutural de exports CSV do HPE IMC.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_mask = sub.add_parser("mask", help="Mascara um export de dispositivos do IMC")
    p_mask.add_argument("-i", "--input", required=True)
    p_mask.add_argument("-o", "--output", required=True)
    p_mask.add_argument("-m", "--map", required=True, help="Ficheiro de mapping (persistente entre execucoes -- NUNCA partilhar)")
    args = parser.parse_args()

    if args.command == "mask":
        input_path = Path(args.input)
        if not input_path.exists():
            log.error("Ficheiro de input nao existe: %s", input_path)
            raise SystemExit(1)

        mapper = IMCMapper()
        mapper.load(args.map)

        n_rows = mask_devices_csv(input_path, args.output, mapper)

        mapper.save(args.map)
        log.info("Ficheiro mascarado: %s (%d linhas)", args.output, n_rows)
        log.info("Mapping atualizado (protege este ficheiro!): %s", args.map)
        log.info(
            "Totais acumulados -> prefixos IP: %d | sites: %d | series: %d | racks: %d",
            len(mapper.ip_prefix_map), len(mapper.location_map),
            len(mapper.serial_map), len(mapper.rack_map),
        )


if __name__ == "__main__":
    main()
