"""OSINT — vérification de fuites d'un e-mail via HaveIBeenPwned (HIBP).

Cas d'usage parfait de l'API Vault : la clé ``hibp_api_key`` est lue depuis la
config (Ctrl+S). Si elle est absente, le module ne crashe pas : il renvoie un
panneau stylisé invitant à la configurer.
"""

from __future__ import annotations

import re
from urllib.parse import quote

import aiohttp
from rich.panel import Panel
from rich.table import Table

from core.base import ToolModule, ToolResult

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_API = "https://haveibeenpwned.com/api/v3/breachedaccount/{email}?truncateResponse=false"


class EmailBreaches(ToolModule):
    name = "Email Breaches"
    category = "OSINT"
    icon = "✉"
    author = "Zelkiobb"
    description = (
        "Vérifie si un e-mail apparaît dans des fuites connues (HaveIBeenPwned). "
        "Nécessite une clé API configurée dans l'API Vault (Ctrl+S)."
    )
    input_label = "Adresse e-mail"
    input_placeholder = "ex: test@example.com"

    async def run(self, ctx) -> ToolResult:
        email = (ctx.value or "").strip()
        if not _EMAIL_RE.match(email):
            ctx.err("Format d'e-mail invalide")
            return ToolResult(renderable="[red]Format d'e-mail invalide.[/red]")

        # --- API Vault : récupération de la clé ---
        key = ctx.config.get("hibp_api_key")
        if not key:
            ctx.warn("Clé HIBP absente du Vault")
            return ToolResult(
                renderable=Panel(
                    "[bold #f3c969]🔑 Clé HIBP manquante.[/]\n\n"
                    "Ce module nécessite une clé API [b]HaveIBeenPwned[/b].\n"
                    "Configure-la via [bold #58c7ff]Ctrl+S[/] (API Vault) → champ "
                    "« HaveIBeenPwned ».\n\n"
                    "[dim]Obtenir une clé : https://haveibeenpwned.com/API/Key[/]",
                    title="[bold]Configuration requise[/]",
                    border_style="#f3c969",
                    padding=(1, 2),
                ),
                data={"error": "no_api_key"},
            )

        ctx.info(f"Interrogation de HIBP pour {email}…")
        url = _API.format(email=quote(email))
        headers = {"hibp-api-key": key, "User-Agent": "OSTING-OSINT"}

        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as resp:
                    status = resp.status
                    payload = await resp.json(content_type=None) if status == 200 else None
        except Exception as exc:
            ctx.err(f"Erreur réseau : {type(exc).__name__}")
            return ToolResult(
                renderable=f"[red]Erreur réseau : {exc}[/red]",
                data={"email": email, "error": str(exc)},
            )

        # --- Codes de retour HIBP ---
        if status == 404:
            ctx.ok("Aucune fuite connue")
            return ToolResult(
                renderable=Panel(
                    f"[#36e07f]✓ Aucune fuite connue pour [b]{email}[/b].[/]",
                    border_style="#36e07f", padding=(1, 2),
                ),
                data={"email": email, "breaches": []},
            )
        if status == 401:
            ctx.err("Clé HIBP invalide (401)")
            return ToolResult(
                renderable="[red]Clé HIBP invalide ou expirée (401). Reconfigure via Ctrl+S.[/]",
                data={"error": "invalid_key"},
            )
        if status == 429:
            ctx.warn("Limite de requêtes atteinte (429)")
            return ToolResult(
                renderable="[#f3c969]Limite de requêtes HIBP atteinte (429). Réessaie plus tard.[/]",
                data={"error": "rate_limited"},
            )
        if status != 200:
            ctx.warn(f"Réponse inattendue (HTTP {status})")
            return ToolResult(
                renderable=f"[#f3c969]Réponse inattendue de HIBP (HTTP {status}).[/]",
                data={"status": status},
            )

        breaches = payload or []
        ctx.warn(f"⚠ {len(breaches)} fuite(s) trouvée(s) pour {email} !")

        table = Table(title=f"Fuites — {email}", expand=True)
        table.add_column("Fuite", style="bold #ff6b6b")
        table.add_column("Date", justify="center")
        table.add_column("Données compromises", overflow="fold")
        for breach in sorted(breaches, key=lambda b: b.get("BreachDate", ""), reverse=True):
            title = breach.get("Title") or breach.get("Name", "?")
            date = breach.get("BreachDate", "?")
            data_classes = ", ".join(breach.get("DataClasses", []))
            ctx.step(f"{title} ({date})")
            table.add_row(title, date, data_classes)

        return ToolResult(
            renderable=table,
            data={
                "email": email,
                "count": len(breaches),
                "breaches": [b.get("Name") for b in breaches],
            },
        )
