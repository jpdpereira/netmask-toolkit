"""Verificacao transversal: cada amostra sintetica de cada vendor tem de
ficar sem sentinelas depois de mascarada, e tem de reverter exatamente."""
import pathlib
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import Masker
from vendors import get_profile

FIXTURES = sorted((pathlib.Path(__file__).parent / "fixtures").glob("*.txt"))

SENTINELAS = [
    "SW-LAB-01", "SW-LAB-02", "exemplo.local", "COMM-TESTE",
    "CHAVE-TESTE-123", "noc@exemplo.local", "Uplink-LAB-CORE",
    "0a1b2c-3d4e5f", "0a:1b:2c:3d:4e:60", "0a1b.2c3d.4e61",
    "192.0.2.10", "198.51.100.20",
]


# Falhas conhecidas, com causa identificada -- nao sao regressoes:
XFAIL_FUGAS = {
    "aruba-cx": "colunas da tabela LLDP ainda nao tratadas (core._mask_table_columns)",
}


def _params_fugas():
    for f in FIXTURES:
        motivo = XFAIL_FUGAS.get(f.stem)
        marcas = [pytest.mark.xfail(reason=motivo, strict=True)] if motivo else []
        yield pytest.param(f, marks=marcas, id=f.stem)


@pytest.mark.parametrize("fixture", list(_params_fugas()))
def test_sem_fugas(fixture):
    texto = fixture.read_text(encoding="utf-8")
    masked = Masker().mask(texto, get_profile(fixture.stem))
    sobraram = [s for s in SENTINELAS if s in texto and s in masked]
    assert not sobraram, f"{fixture.stem}: nao mascarado -> {sobraram}"


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.stem)
def test_roundtrip_exato(fixture):
    texto = fixture.read_text(encoding="utf-8")
    masker = Masker()
    masked = masker.mask(texto, get_profile(fixture.stem))
    assert masker.unmask(masked) == texto


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.stem)
def test_idempotente(fixture):
    """Mascarar o que ja esta mascarado nao pode criar tokens novos."""
    texto = fixture.read_text(encoding="utf-8")
    perfil = get_profile(fixture.stem)
    masker = Masker()
    uma = masker.mask(texto, perfil)
    duas = masker.mask(uma, perfil)
    assert uma == duas
