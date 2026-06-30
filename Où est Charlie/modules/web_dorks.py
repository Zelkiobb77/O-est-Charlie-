"""WEB — générateur de dorks (réellement fonctionnel, hors-ligne)."""

from __future__ import annotations

import urllib.parse

from rich.table import Table

from core.base import ToolModule, ToolResult

_TEMPLATES = [
    'site:linkedin.com/in "{q}"',
    'site:github.com "{q}"',
    '"{q}" filetype:pdf',
    '"{q}" (email OR contact OR "@")',
    'intext:"{q}" (login OR password)',
]


class DorkGenerator(ToolModule):
    name = "Dork Generator"
    category = "WEB"
    icon = "🕸"
    author = "Zelkiobb"
    description = "Génère des requêtes Google (dorks) prêtes à ouvrir pour une cible."
    input_label = "Cible (nom / pseudo / domaine)"
    input_placeholder = "ex: John Doe"

    def run(self, ctx) -> ToolResult:
        target = (ctx.value or "").strip()
        if not target:
            ctx.err("Cible vide")
            return ToolResult(renderable="[red]Saisis une cible.[/red]")
        ctx.info(f"Génération de {len(_TEMPLATES)} dorks pour « {target} »")

        table = Table(title=f"Dorks — {target}", expand=True)
        table.add_column("Requête", style="bold")
        table.add_column("URL", overflow="fold")
        dorks = []
        for template in _TEMPLATES:
            dork = template.format(q=target)
            url = "https://www.google.com/search?q=" + urllib.parse.quote(dork)
            table.add_row(dork, url)
            dorks.append({"dork": dork, "url": url})
        ctx.ok("Dorks prêts")
        return ToolResult(renderable=table, data={"target": target, "dorks": dorks})
