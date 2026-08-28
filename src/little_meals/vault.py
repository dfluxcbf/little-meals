from __future__ import annotations

import subprocess
from pathlib import Path


class VaultError(RuntimeError):
    """Base error for problems decrypting a vault-stored secret."""


class VaultUnavailable(VaultError):
    """The `openssl` binary needed to decrypt the vault isn't installed."""


class VaultDecryptionFailed(VaultError):
    """`openssl` ran but couldn't decrypt the file (wrong passphrase, corrupt/wrong-format file)."""


def decrypt_key_file(path: Path, passphrase: str) -> str:
    """Decrypt a secret encrypted with `openssl enc -aes-256-cbc -pbkdf2`.

    The passphrase is passed to openssl over stdin (`-pass stdin`), never as
    an argv value or env var, so it never appears in `ps` output or shell
    history. Caller is responsible for discarding `passphrase` (e.g. `del`)
    once this returns - CPython can't guarantee the string's backing memory
    is scrubbed, but dropping the only reference is the practical best effort.
    """
    try:
        result = subprocess.run(
            ["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-in", str(path), "-pass", "stdin"],
            input=passphrase.encode(),
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise VaultUnavailable("openssl is not installed - install it to decrypt the vault") from exc

    if result.returncode != 0:
        raise VaultDecryptionFailed(
            "Could not decrypt the vault file - wrong passphrase, or the file isn't "
            "`openssl enc -aes-256-cbc -pbkdf2` format."
        )

    return result.stdout.decode().strip()
