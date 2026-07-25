import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from crypto_utils import decrypt_mapping, encrypt_mapping, is_encrypted_mapping

SAMPLE_MAPPING = {"HOSTNAME_001": "SW-CORE01", "IP_001": "10.0.0.1", "MAC_001": "aa:bb:cc:dd:ee:ff"}


def test_encrypt_then_decrypt_roundtrip(tmp_path):
    path = tmp_path / "mapping.json"
    encrypt_mapping(SAMPLE_MAPPING, path, "senha-forte-123")

    assert is_encrypted_mapping(path)
    restored = decrypt_mapping(path, "senha-forte-123")
    assert restored == SAMPLE_MAPPING


def test_encrypted_file_does_not_contain_plaintext_values(tmp_path):
    path = tmp_path / "mapping.json"
    encrypt_mapping(SAMPLE_MAPPING, path, "senha-forte-123")

    raw = path.read_text()
    for value in SAMPLE_MAPPING.values():
        assert value not in raw


def test_wrong_password_raises(tmp_path):
    path = tmp_path / "mapping.json"
    encrypt_mapping(SAMPLE_MAPPING, path, "senha-certa")

    with pytest.raises(ValueError):
        decrypt_mapping(path, "senha-errada")


def test_is_encrypted_mapping_false_for_plain_json(tmp_path):
    path = tmp_path / "mapping.json"
    path.write_text('{"HOSTNAME_001": "SW-CORE01"}', encoding="utf-8")
    assert is_encrypted_mapping(path) is False


def test_is_encrypted_mapping_false_for_garbage(tmp_path):
    path = tmp_path / "mapping.json"
    path.write_text("isto nao e json valido {{{", encoding="utf-8")
    assert is_encrypted_mapping(path) is False
