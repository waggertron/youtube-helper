from __future__ import annotations

from pathlib import Path


class Settings:
    def __init__(self, config_dir: Path | None = None):
        self.config_dir = config_dir or Path.home() / ".youtube-helper"

    @property
    def db_path(self) -> Path:
        return self.config_dir / "youtube-helper.db"

    @property
    def credentials_path(self) -> Path:
        return self.config_dir / "credentials.json"

    @property
    def client_secret_path(self) -> Path:
        return self.config_dir / "client_secret.json"

    @property
    def token_path(self) -> Path:
        return self.config_dir / "token.pickle"

    def ensure_dirs(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
