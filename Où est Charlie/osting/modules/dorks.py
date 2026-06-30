"""Générateur de « dorks » (requêtes ciblées) pour moteurs de recherche.

Ne lance aucune requête : produit des URLs prêtes à ouvrir manuellement,
pour exploiter des contenus déjà indexés et publics.
"""

from __future__ import annotations

import urllib.parse

from rich.table import Table

from ..core import console

# Modèles de dorks. {q} = la cible (nom, pseudo, e-mail, domaine).
_TEMPLATES = {
    "Profils sociaux": [
        'site:linkedin.com/in "{q}"',
        'site:twitter.com OR site:x.com "{q}"',
        'site:facebook.com "{q}"',
        'site:instagram.com "{q}"',
    ],
    "Documents & fuites": [
        '"{q}" filetype:pdf',
        '"{q}" filetype:xlsx OR filetype:csv',
        '"{q}" (resume OR cv OR curriculum)',
        'intext:"{q}" (password OR mot de passe)',
    ],
    "Pastes & forums": [
        'site:pastebin.com "{q}"',
        'site:github.com "{q}"',
        'site:reddit.com "{q}"',
    ],
    "Coordonnées": [
        '"{q}" (email OR mail OR "@")',
        '"{q}" (phone OR tel OR "+33")',
    ],
}

_ENGINES = {
    "Google": "https://www.google.com/search?q=",
    "Bing": "https://www.bing.com/search?q=",
    "DuckDuckGo": "https://duckduckgo.com/?q=",
}


def run(query: str, engine: str = "Google") -> list[dict]:
    base = _ENGINES.get(engine, _ENGINES["Google"])
    console.print(f"\n[bold]Dorks pour[/bold] [cyan]{query}[/cyan] [dim](moteur : {engine})[/dim]\n")

    out: list[dict] = []
    for category, templates in _TEMPLATES.items():
        table = Table(title=category)
        table.add_column("Requête", style="bold", overflow="fold")
        table.add_column("URL", overflow="fold")
        for tmpl in templates:
            dork = tmpl.format(q=query)
            url = base + urllib.parse.quote(dork)
            table.add_row(dork, url)
            out.append({"category": category, "dork": dork, "url": url})
        console.print(table)

    console.print("\n[dim]Ouvre les URLs manuellement — aucune requête n'est envoyée automatiquement.[/dim]")
    return out
