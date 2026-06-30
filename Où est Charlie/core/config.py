"""API Vault — gestion locale et sécurisée des clés/API (config.json).

Les valeurs sont lues depuis ``config.json`` (à la racine, gitignoré) avec un
repli sur les variables d'environnement. Jamais commité : ne stocke les secrets
que sur la machine de l'utilisateur.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _ROOT / "config.json"


class ConfigVault:
    """Lecture/écriture des clés d'API depuis l'UI."""

    # (clé interne, libellé affiché)
    KNOWN = [
        ("shodan_api_key", "Shodan"),
        ("virustotal_api_key", "VirusTotal"),
        ("hibp_api_key", "HaveIBeenPwned"),
        ("discord_token", "Discord Bot Token"),
        ("github_token", "GitHub"),
    ]

    def __init__(self, path: Path = _CONFIG_PATH) -> None:
        self.path = path
        self.data: dict[str, str] = self._load()

    def _load(self) -> dict[str, str]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def get_raw(self, key: str) -> str:
        """Valeur stockée dans config.json (vide si absente)."""
        return self.data.get(key, "")

    def get(self, key: str, default: str | None = None) -> str | None:
        """Valeur effective : config.json, sinon variable d'environnement."""
        return self.data.get(key) or os.environ.get(key.upper(), default)

    def set(self, key: str, value: str) -> None:
        value = (value or "").strip()
        if value:
            self.data[key] = value
        else:
            self.data.pop(key, None)

    def save(self) -> None:
        self.path.write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def status(self) -> list[tuple[str, str, bool]]:
        """Retourne [(clé, libellé, défini?)] pour l'affichage."""
        return [(k, label, bool(self.get(k))) for k, label in self.KNOWN]
