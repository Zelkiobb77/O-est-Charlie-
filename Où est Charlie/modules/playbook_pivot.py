"""AUTOMATION — Playbook « Identity Pivot » (e-mail/pseudo → empreinte).

Démontre une orchestration différente du Host Recon : DÉRIVATION d'input
(le pseudo est déduit de l'e-mail) puis SYNTHÈSE corrélée (pas un simple
empilement). Chaîne :

    [si e-mail]  Fuites HIBP  ─┐
                               ├─► dérive un pseudo ─► Username Finder ─► Corrélation
    [si pseudo]  ──────────────┘

Le panneau de corrélation évalue l'exposition (FAIBLE / MOYEN / ÉLEVÉ).
Annulable d'un coup (Ctrl+X).
"""

from __future__ import annotations

import asyncio
import re

from rich.console import Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from core.base import ToolModule, ToolResult


def _primary_username(local: str) -> str:
    """Déduit un pseudo plausible de la partie locale d'un e-mail."""
    base = re.sub(r"[^a-z0-9._-]", "", local.lower())
    return re.sub(r"[._-]", "", base) or base


def _section(title: str, renderable) -> list:
    return [Rule(f"[bold #a970ff]{title}[/]", style="#2a2a3a"), renderable]


def _correlation(source: str, username: str, breaches, found: list) -> Panel:
    n_found = len(found)
    n_breach = len(breaches) if isinstance(breaches, list) else None

    # Score d'exposition.
    score = n_found + (n_breach or 0) * 2
    if score >= 8:
        risk, color = "ÉLEVÉ", "#ff6b6b"
    elif score >= 3:
        risk, color = "MOYEN", "#f3c969"
    else:
        risk, color = "FAIBLE", "#36e07f"

    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="#7a7a8c", justify="right")
    grid.add_column(style="#e8e8f2")
    grid.add_row("Source", source)
    grid.add_row("Pseudo pivot", f"[#58c7ff]{username}[/]")
    if n_breach is None:
        grid.add_row("Fuites", "[#7a7a8c]indisponible (clé HIBP manquante)[/]")
    else:
        grid.add_row("Fuites connues", f"[#ff6b6b]{n_breach}[/]" if n_breach else "[#36e07f]0[/]")
    grid.add_row("Profils confirmés", f"[#36e07f]{n_found}[/] · " + (", ".join(found) or "—"))
    grid.add_row("Exposition", f"[bold {color}]● {risk}[/]")

    return Panel(
        grid, title="[bold #a970ff]◢ CORRÉLATION — EMPREINTE NUMÉRIQUE ◣[/]",
        border_style=color, padding=(1, 2),
    )


class IdentityPivot(ToolModule):
    name = "Identity Pivot"
    category = "AUTOMATION"
    icon = "🧬"
    author = "Zelkiobb"
    description = (
        "Playbook : e-mail → fuites HIBP + pseudo dérivé → recherche multi-"
        "plateformes → synthèse d'exposition corrélée. Accepte aussi un pseudo."
    )
    input_label = "E-mail ou pseudo"
    input_placeholder = "ex: john.doe@example.com / torvalds"

    async def run(self, ctx) -> ToolResult:
        raw = (ctx.value or "").strip()
        if not raw:
            ctx.err("Aucune entrée fournie")
            return ToolResult(renderable="[red]Saisis un e-mail ou un pseudo.[/red]")

        is_email = "@" in raw
        plan = (["breaches"] if is_email else []) + ["username", "correlation"]
        ctx.set_total(len(plan))
        total = len(plan)
        step_no = 0

        def banner(msg: str):
            nonlocal step_no
            step_no += 1
            ctx.info(f"[Workflow] Étape {step_no}/{total} : {msg}")

        sections: list = []
        aggregate: dict = {"input": raw}
        breaches = None
        found: list = []
        username = raw

        try:
            # ----- ÉTAPE (e-mail) : fuites HIBP + dérivation -----
            if is_email:
                banner("Vérification des fuites (HIBP)")
                eb = ctx.get_tool("Email Breaches")
                if eb:
                    res = await eb.run(ctx.child(raw))
                    sections += _section("EMAIL BREACHES", res.renderable)
                    aggregate["breaches"] = res.data
                    breaches = res.data.get("breaches")
                ctx.advance()
                self._guard(ctx)
                username = _primary_username(raw.split("@", 1)[0])
                ctx.ok(f"[Workflow] Pseudo dérivé : {username}")

            # ----- ÉTAPE : recherche du pseudo -----
            banner("Recherche multi-plateformes")
            uf = ctx.get_tool("Username Finder")
            if uf:
                res = await uf.run(ctx.child(username))
                sections += _section("USERNAME FINDER", res.renderable)
                aggregate["username"] = res.data
                found = res.data.get("found", []) or []
            ctx.advance()
            self._guard(ctx)

            # ----- ÉTAPE : corrélation -----
            banner("Corrélation & scoring d'exposition")
            correlation = _correlation(raw, username, breaches, found)
            ctx.advance()

        except asyncio.CancelledError:
            ctx.warn("[Workflow] Pivot interrompu par l'utilisateur")
            partial = _correlation(raw, username, breaches, found)
            return self._build(raw, partial, sections, aggregate, interrupted=True)

        ctx.ok("[Workflow] Pivot terminé")
        return self._build(raw, correlation, sections, aggregate, interrupted=False)

    @staticmethod
    def _guard(ctx):
        if ctx.cancelled:
            raise asyncio.CancelledError

    @staticmethod
    def _build(source, correlation, sections, aggregate, interrupted):
        status = "[#f3c969]⚠ INTERROMPU[/]" if interrupted else "[#36e07f]✓ COMPLET[/]"
        header = Panel(
            f"[bold #a970ff]🧬 IDENTITY PIVOT[/]   [#3a3a48]│[/]   [bold #58c7ff]{source}[/]\n"
            f"[#7a7a8c]Statut :[/] {status}",
            title="[bold]RAPPORT D'EMPREINTE[/]", border_style="#a970ff", padding=(1, 2),
        )
        return ToolResult(
            renderable=Group(header, Text(), correlation, Text(), *sections),
            data={**aggregate, "interrupted": interrupted},
        )
