"""Detetor de fugas para o log de pre-checks de upgrade do Aruba 2930M
(AOS-Switch WC.16.10). Fixture 100% ficticio -- formatos baseados na
estrutura real dos show commands, valores inventados."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import Masker
from vendors import get_profile

FIXTURE = Path(__file__).parent / "fixtures" / "aruba2930m_prechecks_sample.log"


@pytest.fixture(scope="module")
def result():
    text = FIXTURE.read_text(encoding="utf-8")
    masker = Masker()
    masked = masker.mask(text, get_profile("aruba-switch"))
    return text, masked, masker


# (id da lacuna, valor sensivel que NAO pode aparecer no output mascarado)
LEAKS = [
    ("A-snmp-community-tabela", "lab-fake-comm"),
    ("B-tacacs-key", "fake-tacacs-key"),
    ("C-snmpv3-user", "lab-snmpv3-user"),
    ("D-system-contact", "Equipa Redes Lab"),
    ("D-system-location", "Edificio Lab Piso 1"),
    ("E-vlan-name-tabela", "LAB-USERS-PISO1"),
    ("E-port-name-tabela", "LAB-AP-03"),
    ("F-lldp-sysname-tabela", "SW-LAB-CORE-01"),
    ("F-lldp-sysname-com-portdescr-espacos", "SW-LAB-DIST-02"),
    ("F-lldp-portdescr-espacos", "Uplink to"),
    ("G-8021x-username", "lab.user01"),
    ("H-hostname-em-ficheiro", "SW-LAB-ACC-01"),
    ("I-mac-no-stack-id", "00010a1b-2c3d4e00"),
]


@pytest.mark.parametrize("gap_id,secret", LEAKS, ids=[g for g, _ in LEAKS])
def test_no_leak(result, gap_id, secret):
    _, masked, _ = result
    leaked = [ln for ln in masked.splitlines() if secret in ln]
    assert not leaked, f"[{gap_id}] '{secret}' em claro em: {leaked}"


# valores tecnicos que TEM de continuar legiveis (sem falsos positivos)
KEEP = ["WC.16.10.0009", "JL322A", "DEFAULT_VLAN", 'name "DEFAULT_VLAN"', "Commander", "LocalPort | ChassisId", "Ring", "8021X"]


@pytest.mark.parametrize("value", KEEP)
def test_no_false_positive(result, value):
    _, masked, _ = result
    assert value in masked


def test_roundtrip_is_lossless(result):
    text, masked, masker = result
    assert masker.unmask(masked) == text
