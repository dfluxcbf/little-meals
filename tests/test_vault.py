from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from little_meals.vault import VaultDecryptionFailed, VaultUnavailable, decrypt_key_file


def _encrypt(tmp_path: Path, plaintext: str, passphrase: str) -> Path:
    plain_path = tmp_path / "plain.txt"
    plain_path.write_text(plaintext)
    enc_path = tmp_path / "secret.enc"
    subprocess.run(
        [
            "openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt",
            "-in", str(plain_path), "-out", str(enc_path), "-pass", "stdin",
        ],
        input=passphrase.encode(),
        check=True,
    )
    return enc_path


def test_decrypts_with_correct_passphrase(tmp_path):
    path = _encrypt(tmp_path, "abc123spoonacularkey", "correct-horse")
    assert decrypt_key_file(path, "correct-horse") == "abc123spoonacularkey"


def test_wrong_passphrase_raises_decryption_failed(tmp_path):
    path = _encrypt(tmp_path, "abc123spoonacularkey", "correct-horse")
    with pytest.raises(VaultDecryptionFailed):
        decrypt_key_file(path, "wrong-passphrase")


def test_non_openssl_file_raises_decryption_failed(tmp_path):
    path = tmp_path / "not-encrypted.txt"
    path.write_text("just plaintext, not an openssl envelope")
    with pytest.raises(VaultDecryptionFailed):
        decrypt_key_file(path, "whatever")


def test_missing_openssl_raises_unavailable(tmp_path, monkeypatch):
    import little_meals.vault as vault_module

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("openssl")

    monkeypatch.setattr(vault_module.subprocess, "run", fake_run)
    with pytest.raises(VaultUnavailable):
        decrypt_key_file(tmp_path / "whatever.enc", "pass")
