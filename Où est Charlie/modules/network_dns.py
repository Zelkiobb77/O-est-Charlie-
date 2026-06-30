"""NETWORK — reconnaissance DNS RÉELLE et asynchrone (dnspython asyncresolver)."""

from __future__ import annotations

import dns.asyncresolver
import dns.resolver
from rich.table import Table

from core.base import ToolModule, ToolResult

_RECORD_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "SOA"]


class DnsRecon(ToolModule):
    name = "DNS Recon"
    category = "NETWORK"
    icon = "🌐"
    author = "Zelkiobb"
    description = (
        "Résolution DNS réelle (A/AAAA/MX/NS/TXT/SOA) en asynchrone. "
        "Chaque requête est loguée en direct."
    )
    input_label = "Domaine"
    input_placeholder = "ex: example.com"

    async def run(self, ctx) -> ToolResult:
        domain = (ctx.value or "").strip().lower().strip(".")
        if not domain:
            ctx.err("Aucun domaine fourni")
            return ToolResult(renderable="[red]Saisis un domaine.[/red]")

        ctx.set_total(len(_RECORD_TYPES))  # ← ProgressBar
        ctx.info(f"Résolution DNS de {domain}")
        resolver = dns.asyncresolver.Resolver()
        resolver.lifetime = 5.0

        table = Table(title=f"DNS — {domain}", expand=True)
        table.add_column("Type", style="bold cyan")
        table.add_column("Valeur", overflow="fold")
        records: dict[str, list[str]] = {}

        for rtype in _RECORD_TYPES:
            if ctx.cancelled:  # ← annulation coopérative (Ctrl+X)
                ctx.warn("Résolution interrompue par l'utilisateur")
                return ToolResult(
                    renderable="[#f3c969][!] Résolution DNS interrompue.[/]",
                    data={"domain": domain, "cancelled": True, "records": records},
                )
            ctx.step(f"Requête {rtype}…")
            try:
                answer = await resolver.resolve(domain, rtype)
                values = [r.to_text() for r in answer]
                records[rtype] = values
                ctx.ok(f"{rtype} · {len(values)} enregistrement(s)")
                table.add_row(rtype, "\n".join(values))
            except dns.resolver.NXDOMAIN:
                ctx.err("Domaine inexistant (NXDOMAIN)")
                return ToolResult(
                    renderable=f"[red]{domain} n'existe pas (NXDOMAIN).[/red]",
                    data={"domain": domain, "error": "NXDOMAIN"},
                )
            except dns.resolver.NoAnswer:
                ctx.step(f"{rtype} · aucune réponse")
            except Exception as exc:
                ctx.warn(f"{rtype} · {type(exc).__name__}")
            ctx.advance()  # ← +1 sur la barre par type résolu

        if not records:
            return ToolResult(
                renderable=f"[#f3c969]Aucun enregistrement résolu pour {domain}.[/]",
                data={"domain": domain, "records": {}},
            )
        ctx.ok("Résolution terminée")
        return ToolResult(renderable=table, data={"domain": domain, "records": records})
