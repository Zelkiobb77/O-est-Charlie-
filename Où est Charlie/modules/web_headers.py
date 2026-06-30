"""WEB — audit des en-têtes HTTP de sécurité (démo, logs temps réel)."""

from __future__ import annotations

import time

from rich.table import Table

from core.base import ToolModule, ToolResult

_SECURITY_HEADERS = [
    "Strict-Transport-Security",
    "Content-Security-Policy",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Referrer-Policy",
    "Permissions-Policy",
]
_PRESENT = {"X-Content-Type-Options", "X-Frame-Options"}


class HeaderGrabber(ToolModule):
    name = "HTTP Header Audit"
    category = "WEB"
    icon = "🧱"
    author = "Zelkiobb"
    description = "Audite la présence des en-têtes HTTP de sécurité d'un site."
    input_label = "URL"
    input_placeholder = "ex: https://example.com"

    def run(self, ctx) -> ToolResult:
        url = (ctx.value or "https://example.com").strip()
        ctx.info(f"Requête vers {url}")
        time.sleep(0.4)
        ctx.ok("Réponse 200 OK · analyse des en-têtes")

        table = Table(title=f"En-têtes de sécurité — {url}", expand=True)
        table.add_column("En-tête", style="bold")
        table.add_column("Présent", justify="center")
        missing = []
        for header in _SECURITY_HEADERS:
            present = header in _PRESENT
            if present:
                table.add_row(header, "[green]✓[/]")
            else:
                ctx.warn(f"Manquant : {header}")
                table.add_row(header, "[red]✗ manquant[/]")
                missing.append(header)

        return ToolResult(renderable=table, data={"url": url, "missing": missing})
