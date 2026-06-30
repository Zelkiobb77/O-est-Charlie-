"""Recherche d'un pseudo sur de nombreuses plateformes publiques.

Approche type « Sherlock » : on requête l'URL publique du profil et on déduit
sa présence du code HTTP ou d'un message d'absence connu.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from rich.table import Table

from ..core import console, make_session

_SITES_FILE = Path(__file__).resolve().parent.parent / "data" / "sites.json"


def _load_sites() -> dict:
    return json.loads(_SITES_FILE.read_text(encoding="utf-8"))


def _check_site(session, name: str, cfg: dict, username: str) -> tuple[str, bool, str]:
    url = cfg["url"].format(username)
    try:
        resp = session.get(url, timeout=10, allow_redirects=True)
    except Exception as exc:  # réseau, timeout, SSL…
        return name, False, f"erreur: {type(exc).__name__}"

    if cfg.get("check") == "message":
        present = cfg["absent"] not in resp.text
        return name, present, url if present else "—"

    # check par statut : 200 = présent, autre = absent
    present = resp.status_code == 200
    return name, present, url if present else "—"


def run(username: str, workers: int = 20) -> list[dict]:
    """Cherche `username` sur toutes les plateformes connues."""
    sites = _load_sites()
    session = make_session()
    results: list[dict] = []

    console.print(
        f"\n[bold]Recherche du pseudo[/bold] [cyan]{username}[/cyan] "
        f"sur [bold]{len(sites)}[/bold] plateformes…\n"
    )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_check_site, session, name, cfg, username): name
            for name, cfg in sites.items()
        }
        for future in as_completed(futures):
            name, present, url = future.result()
            results.append({"site": name, "found": present, "url": url})

    results.sort(key=lambda r: (not r["found"], r["site"].lower()))

    table = Table(title=f"Présence de « {username} »", show_lines=False)
    table.add_column("Plateforme", style="bold")
    table.add_column("Statut")
    table.add_column("URL", overflow="fold")
    for r in results:
        if r["found"]:
            table.add_row(r["site"], "[green]TROUVÉ[/green]", r["url"])
        else:
            table.add_row(r["site"], "[dim]absent[/dim]", "—")
    console.print(table)

    found = [r for r in results if r["found"]]
    console.print(f"\n[bold green]{len(found)}[/bold green] profil(s) trouvé(s).")
    return results
