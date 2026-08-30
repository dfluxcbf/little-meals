from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


def _default_data_dir() -> Path:
    env_dir = os.environ.get("LITTLE_MEALS_DATA_DIR")
    if env_dir:
        return Path(env_dir).expanduser()
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg_data_home).expanduser() if xdg_data_home else Path.home() / ".local" / "share"
    return base / "little-meals"


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(default_factory=_default_data_dir)
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5-coder:14b"
    ollama_timeout_s: float = 120.0
    host: str = "127.0.0.1"
    port: int = 8765
    spoonacular_api_key: Optional[str] = None
    spoonacular_base_url: str = "https://api.spoonacular.com"
    spoonacular_timeout_s: float = 15.0
    # Path to an openssl-encrypted file holding the Spoonacular API key (see
    # vault.py), for the secure deployment path. Only the path is
    # env-configured; the decrypted key itself is never read from the
    # environment here - cli.py prompts for the vault passphrase and sets
    # it on a per-run Settings via dataclasses.replace(). Takes precedence
    # over spoonacular_api_key when both are configured.
    spoonacular_key_file: Optional[Path] = None

    @property
    def recipes_dir(self) -> Path:
        return self.data_dir / "recipes"

    @property
    def household_db_path(self) -> Path:
        return self.data_dir / "household.db"

    @property
    def plan_db_path(self) -> Path:
        return self.data_dir / "plan.db"

    @property
    def shopping_list_db_path(self) -> Path:
        return self.data_dir / "shopping_list.db"

    @property
    def notification_db_path(self) -> Path:
        return self.data_dir / "notification.db"

    @property
    def cook_along_db_path(self) -> Path:
        return self.data_dir / "cook_along.db"

    @classmethod
    def from_env(cls) -> "Settings":
        key_file = os.environ.get("LITTLE_MEALS_SPOONACULAR_KEY_FILE")
        return cls(
            data_dir=_default_data_dir(),
            ollama_base_url=os.environ.get("LITTLE_MEALS_OLLAMA_URL", cls.ollama_base_url),
            ollama_model=os.environ.get("LITTLE_MEALS_OLLAMA_MODEL", cls.ollama_model),
            ollama_timeout_s=float(os.environ.get("LITTLE_MEALS_OLLAMA_TIMEOUT", cls.ollama_timeout_s)),
            spoonacular_api_key=os.environ.get("LITTLE_MEALS_SPOONACULAR_API_KEY") or None,
            spoonacular_base_url=os.environ.get("LITTLE_MEALS_SPOONACULAR_BASE_URL", cls.spoonacular_base_url),
            spoonacular_timeout_s=float(
                os.environ.get("LITTLE_MEALS_SPOONACULAR_TIMEOUT", cls.spoonacular_timeout_s)
            ),
            spoonacular_key_file=Path(key_file).expanduser() if key_file else None,
        )
