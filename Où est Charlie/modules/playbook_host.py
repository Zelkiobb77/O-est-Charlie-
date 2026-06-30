"""AUTOMATION — Playbook « Host Recon » (scan en chaîne / orchestrateur).

Ne fait PAS le travail lui-même : il pilote d'autres modules via le contexte.
Chaîne : (Résolution DNS si domaine) → Shodan → Scan de ports (conditionnel).
Le ToolResult empile les rendus des sous-modules en un rapport centralisé.

Annulation : ``ctx.cancelled`` (partagé avec les sous-modules via ctx.child)
ainsi que le Task.cancel() dur stoppent toute la chaîne d'un coup.
"""

from __future__ import annotations

import asyncio
import ipaddress

from rich.console import Group
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from core.base import ToolModule, ToolResult


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def _section(title: str, renderable) -> list:
    return [Rule(f"[bold #a970ff]{title}[/]", style="#2a2a3a"), renderable]


class HostReconPlaybook(ToolModule):
    name = "Host Recon"
    category = "AUTOMATION"
    icon = "⚡"
    author = "Zelkiobb"
    description = (
        "Playbook orchestré : DNS → Shodan → Scan de ports, agrégés en un seul "
        "rapport de Red Teamer. Annulable d'un coup (Ctrl+X)."
    )
    input_label = "Cible (IP ou domaine)"
    input_placeholder = "ex: scanme.nmap.org / 8.8.8.8"

    async def run(self, ctx) -> ToolResult:
        target = (ctx.value or "").strip().rstrip("/")
        if not target:
            ctx.err("Aucune cible fournie")
            return ToolResult(renderable="[red]Saisis une IP ou un domaine.[/red]")

        is_domain = not _is_ip(target)
        # Planification des étapes (pour la barre globale).
        plan = (["dns"] if is_domain else []) + ["shodan", "ports"]
        ctx.set_total(len(plan))
        step_no = 0
        total = len(plan)

        sections: list = []
        aggregate: dict = {"target": target}
        ip = target

        def banner(msg: str):
            nonlocal step_no
            step_no += 1
            ctx.info(f"[Workflow] Étape {step_no}/{total} : {msg}")

        try:
            # ----- ÉTAPE 1 : DNS (si domaine) -----
            if is_domain:
                banner("Résolution DNS")
                dns_tool = ctx.get_tool("DNS Recon")
                if dns_tool:
                    dns_res = await dns_tool.run(ctx.child(target))
                    sections += _section("DNS RECON", dns_res.renderable)
                    aggregate["dns"] = dns_res.data
                    a_records = (dns_res.data.get("records") or {}).get("A") or []
                    if a_records:
                        ip = a_records[0]
                        ctx.ok(f"[Workflow] {target} → {ip}")
                    else:
                        ctx.warn("[Workflow] Aucun enregistrement A — étapes IP limitées")
                        ip = None
                ctx.advance()
                self._guard(ctx)

            # ----- ÉTAPE 2 : Shodan -----
            banner("Interrogation Shodan")
            shodan_ports: list = []
            if ip is not None:
                shodan_tool = ctx.get_tool("Shodan Host")
                if shodan_tool:
                    shodan_res = await shodan_tool.run(ctx.child(ip))
                    sections += _section("SHODAN HOST", shodan_res.renderable)
                    aggregate["shodan"] = shodan_res.data
                    shodan_ports = shodan_res.data.get("ports") or []
                    ctx.ok(f"[Workflow] Shodan → {len(shodan_ports)} port(s) connu(s)")
            else:
                ctx.warn("[Workflow] Pas d'IP résolue — Shodan ignoré")
            ctx.advance()
            self._guard(ctx)

            # ----- ÉTAPE 3 : Scan de ports (conditionnel) -----
            banner("Scan de ports")
            shodan_known = bool(aggregate.get("shodan", {}).get("ip"))
            do_scan = ip is not None and (bool(shodan_ports) or not shodan_known)
            if do_scan:
                reason = "ports Shodan à confirmer" if shodan_ports else "découverte (Shodan muet)"
                ctx.info(f"[Workflow] Scan lancé · {reason}")
                ps_tool = ctx.get_tool("Port Scanner")
                if ps_tool:
                    ps_res = await ps_tool.run(ctx.child(ip))
                    sections += _section("PORT SCAN", ps_res.renderable)
                    aggregate["ports"] = ps_res.data
            else:
                ctx.step("[Workflow] Scan ignoré (Shodan fait foi, 0 port intéressant)")
            ctx.advance()
            # Un sous-module a pu absorber l'annulation dure : on revérifie le
            # drapeau coopératif pour stopper TOUTE la chaîne.
            self._guard(ctx)

        except asyncio.CancelledError:
            ctx.warn("[Workflow] Playbook interrompu par l'utilisateur")
            return self._build(target, ip, sections, aggregate, interrupted=True)

        ctx.ok("[Workflow] Playbook terminé")
        return self._build(target, ip, sections, aggregate, interrupted=False)

    @staticmethod
    def _guard(ctx):
        """Stoppe net la chaîne si l'annulation coopérative est demandée."""
        if ctx.cancelled:
            raise asyncio.CancelledError

    @staticmethod
    def _build(target, ip, sections, aggregate, interrupted):
        n_cve = len(aggregate.get("shodan", {}).get("vulns") or [])
        n_ports = len(aggregate.get("ports", {}).get("open_ports") or aggregate.get("shodan", {}).get("ports") or [])
        status = "[#f3c969]⚠ INTERROMPU[/]" if interrupted else "[#36e07f]✓ COMPLET[/]"

        header = Panel(
            f"[bold #a970ff]⚡ HOST RECON[/]   [#3a3a48]│[/]   [bold #58c7ff]{target}[/]"
            f"{f'  →  {ip}' if ip and ip != target else ''}\n"
            f"[#7a7a8c]Statut :[/] {status}   [#3a3a48]│[/]   "
            f"[#7a7a8c]Ports :[/] [bold]{n_ports}[/]   [#3a3a48]│[/]   "
            f"[#7a7a8c]CVE :[/] [bold #ff6b6b]{n_cve}[/]",
            title="[bold]RAPPORT CENTRALISÉ[/]", border_style="#a970ff", padding=(1, 2),
        )

        if not sections:
            sections = [Text("Aucune donnée collectée.", style="#7a7a8c")]

        return ToolResult(
            renderable=Group(header, Text(), *sections),
            data={**aggregate, "ip": ip, "interrupted": interrupted},
        )
