"""Reporting Engine — export du résultat d'un module vers exports/.

Trois formats : JSON (données structurées), TXT (rendu brut), Markdown (rapport).
"""

from __future__ import annotations

import io
import json
import re
from datetime import datetime
from pathlib import Path

from rich.console import Console

from core.base import ToolResult

_ROOT = Path(__file__).resolve().parent.parent
_EXPORTS = _ROOT / "exports"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "module"


def _plain_text(result: ToolResult) -> str:
    """Rend le renderable rich en texte brut (sans codes couleur)."""
    console = Console(record=True, width=100, file=io.StringIO())
    console.print(result.renderable)
    return console.export_text()


def export_result(tool_name: str, value, result: ToolResult) -> list[Path]:
    """Écrit le résultat dans exports/ aux 3 formats. Retourne les chemins."""
    _EXPORTS.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{_slug(tool_name)}_{stamp}"
    text = _plain_text(result)
    paths: list[Path] = []

    # --- JSON ---
    json_path = _EXPORTS / f"{base}.json"
    json_path.write_text(
        json.dumps(
            {
                "tool": tool_name,
                "input": value,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "data": result.data,
            },
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )
    paths.append(json_path)

    # --- TXT ---
    txt_path = _EXPORTS / f"{base}.txt"
    txt_path.write_text(text, encoding="utf-8")
    paths.append(txt_path)

    # --- Markdown ---
    md_path = _EXPORTS / f"{base}.md"
    md = (
        f"# Rapport OSTING — {tool_name}\n\n"
        f"- **Cible** : `{value}`\n"
        f"- **Date** : {datetime.now().isoformat(timespec='seconds')}\n\n"
        f"## Résultat\n\n```\n{text}\n```\n"
    )
    md_path.write_text(md, encoding="utf-8")
    paths.append(md_path)

    return paths
