"""
crypto_utils.py - encriptacao opcional do mapping.json com uma password.

O mapping.json e a chave de reversao de todo o processo -- se alguem lhe
tiver acesso, consegue reconstruir a informacao real a partir do ficheiro
mascarado. Este modulo permite cifra-lo em repouso com uma password,
usando Fernet (AES-128 em modo CBC + HMAC, da biblioteca `cryptography`)
com a chave derivada via PBKDF2-HMAC-SHA256.

A password NUNCA e guardada em disco. O salt (nao secreto, serve so para
a derivacao da chave) fica guardado junto do ficheiro cifrado.
"""

import base64
import getpass
import json
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Recomendacao OWASP (2023) para PBKDF2-HMAC-SHA256
_KDF_ITERATIONS = 480_000


def _derive_key(password, salt):
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=_KDF_ITERATIONS)
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def encrypt_mapping(mapping, path, password):
    """Cifra o dict de mapping e escreve-o em `path` em formato JSON
    {salt, ciphertext} -- ambos em base64, seguro para escrever em texto."""
    salt = os.urandom(16)
    key = _derive_key(password, salt)
    token = Fernet(key).encrypt(json.dumps(mapping, ensure_ascii=False).encode("utf-8"))
    payload = {
        "_netmask_encrypted": True,
        "salt": base64.b64encode(salt).decode("ascii"),
        "ciphertext": token.decode("ascii"),
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def decrypt_mapping(path, password):
    """Le um ficheiro cifrado por encrypt_mapping() e devolve o dict original."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    salt = base64.b64decode(payload["salt"])
    key = _derive_key(password, salt)
    try:
        plaintext = Fernet(key).decrypt(payload["ciphertext"].encode("ascii"))
    except InvalidToken as exc:
        raise ValueError("Password incorreta ou ficheiro de mapping corrompido/adulterado.") from exc
    return json.loads(plaintext.decode("utf-8"))


def is_encrypted_mapping(path):
    """Deteta se um ficheiro de mapping esta cifrado, sem precisar da password."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return isinstance(payload, dict) and payload.get("_netmask_encrypted") is True


def prompt_password(confirm=False):
    pw = getpass.getpass("Password para o mapping: ")
    if confirm:
        pw2 = getpass.getpass("Confirma a password: ")
        if pw != pw2:
            raise ValueError("As passwords nao coincidem.")
    return pw
