"""Detetor de fugas para log de pre-checks Comware v7 (HPE 5710, 7.1.070).
Fixture 100% ficticio, tabelas geradas com alinhamento exato."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import Masker
from vendors import get_profile

FIXTURE = Path(__file__).parent / "fixtures" / "comware5710_prechecks_sample.log"


@pytest.fixture(scope="module")
def result():
    text = FIXTURE.read_text(encoding="utf-8")
    masker = Masker()
    return text, masker.mask(text, get_profile("comware")), masker


LEAKS = [
    ("vlan-name-propagada-vlan-brief", "LAB-SRV-PRODUCAO-DC1"),
    ("desc-truncada-interface-brief", "LAB-UPLINK-PARA"),
    ("vpn-instance", "LAB-VRF-CLIENTE"),
    ("domain", "lab-dominio"),
    ("local-user-e-log", "lab.operador"),
    ("log-user-desconhecido", "lab.intruso"),
    ("password-hash", "fakehash"),
    ("serial-number", "CN00LAB001"),
    ("lldp-list-system-name", "LAB-CORE-VIZINHO-01"),
]


@pytest.mark.parametrize("gap_id,secret", LEAKS, ids=[g for g, _ in LEAKS])
def test_no_leak(result, gap_id, secret):
    _, masked, _ = result
    leaked = [ln for ln in masked.splitlines() if secret in ln]
    assert not leaked, f"[{gap_id}] '{secret}' em claro em: {leaked}"


# decisoes explicitas: defaults e ASN privado ficam legiveis
KEEP = ["DEVICE_SERIAL_NUMBER : NONE", "domain system", "bgp 65001", "network-admin", "VLAN 0001", "Description", "System Name",
        "display link-aggregation verbose Bridge-Aggregation1"]


@pytest.mark.parametrize("value", KEEP)
def test_no_false_positive(result, value):
    _, masked, _ = result
    assert value in masked


def test_roundtrip_is_lossless(result):
    text, masked, masker = result
    assert masker.unmask(masked) == text
