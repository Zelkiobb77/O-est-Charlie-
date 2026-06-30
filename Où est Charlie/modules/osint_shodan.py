"""OSINT / NETWORK — fiche Shodan complète d'une IP (l'outil premium).

Interroge l'API REST de Shodan (api.shodan.io/shodan/host/{ip}) en async via
aiohttp. La clé ``shodan_api_key`` provient de l'API Vault (Ctrl+S). Rendu
massif : identité/ISP, géolocalisation, ports + bannières, et une section
rouge listant les CVE si présentes.
"""

from __future__ import annotations

import ipaddress

import aiohttp
from rich.console import Group
from rich.panel import Panel
from rich.table import Table

from core.base import ToolModule, ToolResult

_API = "https://api.shodan.io/shodan/host/{ip}?key={key}"


def _cvss_value(info) -> float:
    if isinstance(info, dict) and info.get("cvss") is not None:
        try:
            return float(info["cvss"])
        except (TypeError, ValueError):
            return -1.0
    return -1.0


def build_report(ip: str, data: dict):
    """Construit le rendu rich massif à partir de la réponse Shodan."""
    org = data.get("org") or data.get("isp") or "—"
    isp = data.get("isp") or "—"
    asn = data.get("asn") or "—"
    country = data.get("country_name") or "?"
    city = data.get("city") or "?"
    os_ = data.get("os") or "—"
    hostnames = data.get("hostnames") or []
    last = data.get("last_update", "—")
    ports = sorted(data.get("ports", []))
    services = data.get("data", []) or []

    # --- En-tête ---
    header = Panel(
        f"[bold #58c7ff]{ip}[/]    [#3a3a48]│[/]    [bold #e8e8f2]{org}[/]    "
        f"[#3a3a48]│[/]    [bold #a970ff]{len(ports)} port(s) ouvert(s)[/]",
        border_style="#a970ff",
        padding=(0, 2),
        title="[bold #a970ff]◢ SHODAN HOST ◣[/]",
    )

    # --- Identité & géo ---
    ident = Table.grid(padding=(0, 2))
    ident.add_column(style="#7a7a8c", justify="right")
    ident.add_column(style="#e8e8f2")
    ident.add_row("Organisation", str(org))
    ident.add_row("ISP", str(isp))
    ident.add_row("ASN", str(asn))
    ident.add_row("Localisation", f"{city}, {country}")
    ident.add_row("Hostnames", ", ".join(hostnames) if hostnames else "—")
    ident.add_row("OS", str(os_))
    ident.add_row("Dernière MAJ", str(last))
    ident_panel = Panel(
        ident, title="[bold #58c7ff]IDENTITÉ & LOCALISATION[/]",
        border_style="#2a2a3a", padding=(1, 2),
    )

    # --- Ports & bannières ---
    ports_tbl = Table(title="PORTS OUVERTS & SERVICES", expand=True, title_style="bold #58c7ff")
    ports_tbl.add_column("Port", justify="right", style="bold #a970ff")
    ports_tbl.add_column("Service")
    ports_tbl.add_column("Bannière", overflow="fold", style="#7a7a8c")
    for svc in sorted(services, key=lambda s: s.get("port", 0)):
        transport = svc.get("transport", "tcp")
        product = (svc.get("product") or "").strip()
        version = (svc.get("version") or "").strip()
        label = " ".join(x for x in (product, version) if x) or "—"
        banner = (svc.get("data") or "").strip()
        banner = banner.splitlines()[0][:70] if banner else "—"
        ports_tbl.add_row(f"{svc.get('port', '?')}/{transport}", label, banner)
    if not services:
        ports_tbl.add_row("—", "—", "[#3a3a48]aucune bannière[/]")

    # --- Vulnérabilités (CVE) ---
    vulns: dict = {}
    top = data.get("vulns") or []
    if isinstance(top, dict):
        vulns.update(top)
    else:
        for cve in top:
            vulns.setdefault(cve, {})
    for svc in services:  # niveau service = plus riche (cvss, summary)
        sv = svc.get("vulns") or {}
        if isinstance(sv, dict):
            vulns.update(sv)

    if vulns:
        vt = Table(expand=True)
        vt.add_column("CVE", style="bold #ff6b6b")
        vt.add_column("CVSS", justify="center", style="bold #f3c969")
        vt.add_column("Résumé", overflow="fold", style="#c8c8d4")
        for cve, info in sorted(vulns.items(), key=lambda kv: _cvss_value(kv[1]), reverse=True):
            cvss = info.get("cvss") if isinstance(info, dict) else None
            summary = (info.get("summary") if isinstance(info, dict) else "") or ""
            vt.add_row(cve, str(cvss) if cvss is not None else "?", summary[:90] or "—")
        vuln_panel = Panel(
            vt, title=f"[bold #ff6b6b]⚠  {len(vulns)} VULNÉRABILITÉ(S) — CVE  ⚠[/]",
            border_style="#ff6b6b", padding=(1, 1),
        )
    else:
        vuln_panel = Panel(
            "[#36e07f]✓ Aucune CVE référencée par Shodan pour cet hôte.[/]",
            title="[bold]VULNÉRABILITÉS[/]", border_style="#36e07f", padding=(1, 2),
        )

    return Group(header, ident_panel, ports_tbl, vuln_panel)


class ShodanHost(ToolModule):
    name = "Shodan Host"
    category = "NETWORK"
    icon = "🔱"
    author = "Zelkiobb"
    description = (
        "Fiche Shodan complète d'une IP : ISP, géo, ports, bannières et CVE. "
        "Nécessite une clé Shodan dans l'API Vault (Ctrl+S)."
    )
    input_label = "Adresse IP"
    input_placeholder = "ex: 8.8.8.8"

    async def run(self, ctx) -> ToolResult:
        ip = (ctx.value or "").strip()
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            ctx.err("Adresse IP invalide")
            return ToolResult(renderable="[red]Adresse IP invalide.[/red]")

        # --- API Vault ---
        key = ctx.config.get("shodan_api_key")
        if not key:
            ctx.warn("Clé Shodan absente du Vault")
            return ToolResult(
                renderable=Panel(
                    "[bold #f3c969]🔑 Clé Shodan manquante.[/]\n\n"
                    "Ce module nécessite une clé API [b]Shodan[/b].\n"
                    "Configure-la via [bold #58c7ff]Ctrl+S[/] (API Vault) → champ « Shodan ».\n\n"
                    "[dim]Obtenir une clé : https://account.shodan.io[/]",
                    title="[bold]Configuration requise[/]",
                    border_style="#f3c969", padding=(1, 2),
                ),
                data={"error": "no_api_key"},
            )

        ctx.set_total(3)
        ctx.info(f"Interrogation de Shodan pour {ip}…")
        url = _API.format(ip=ip, key=key)
        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    status = resp.status
                    payload = await resp.json(content_type=None)
        except Exception as exc:
            ctx.err(f"Erreur réseau : {type(exc).__name__}")
            return ToolResult(renderable=f"[red]Erreur réseau : {exc}[/red]", data={"error": str(exc)})
        ctx.advance()

        if status == 401:
            ctx.err("Clé Shodan invalide (401)")
            return ToolResult(
                renderable="[red]Clé Shodan invalide (401). Reconfigure via Ctrl+S.[/]",
                data={"error": "invalid_key"},
            )
        if status == 404:
            ctx.warn("Aucune information pour cette IP")
            return ToolResult(
                renderable=f"[#f3c969]Aucune information Shodan disponible pour {ip}.[/]",
                data={"ip": ip, "found": False},
            )
        if status == 429:
            ctx.warn("Limite de requêtes atteinte (429)")
            return ToolResult(
                renderable="[#f3c969]Limite de requêtes Shodan atteinte (429).[/]",
                data={"error": "rate_limited"},
            )
        if status != 200:
            msg = payload.get("error") if isinstance(payload, dict) else None
            ctx.warn(f"Réponse inattendue (HTTP {status})")
            return ToolResult(
                renderable=f"[#f3c969]Shodan a répondu HTTP {status}{' · ' + msg if msg else ''}.[/]",
                data={"status": status, "error": msg},
            )

        ctx.ok("Données reçues · parsing en cours…")
        ctx.advance()

        ports = payload.get("ports", []) or []
        vulns = payload.get("vulns") or []
        for svc in payload.get("data", []) or []:
            sv = svc.get("vulns") or {}
            if isinstance(sv, dict):
                vulns = list(set(list(vulns) + list(sv.keys())))
        ctx.step(f"{len(ports)} port(s) · {len(payload.get('data', []) or [])} service(s)")
        if vulns:
            ctx.warn(f"⚠ {len(vulns)} CVE détectée(s) sur l'hôte !")
        else:
            ctx.ok("Aucune CVE référencée")
        ctx.advance()

        return ToolResult(
            renderable=build_report(ip, payload),
            data={
                "ip": ip,
                "org": payload.get("org"),
                "isp": payload.get("isp"),
                "asn": payload.get("asn"),
                "country": payload.get("country_name"),
                "ports": sorted(ports),
                "vulns": sorted(vulns),
            },
        )
