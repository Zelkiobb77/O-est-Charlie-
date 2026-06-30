"""Reconnaissance de domaine : WHOIS, DNS et sous-domaines (sources publiques)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import dns.resolver
from rich.table import Table

from ..core import console

# Petite liste de sous-domaines courants pour une découverte rapide par DNS.
_COMMON_SUBDOMAINS = [
    "www", "mail", "webmail", "smtp", "imap", "pop", "ftp", "cpanel", "ns1",
    "ns2", "api", "dev", "staging", "test", "admin", "portal", "vpn", "remote",
    "blog", "shop", "store", "app", "m", "mobile", "cdn", "static", "img",
    "assets", "git", "gitlab", "jenkins", "ci", "docs", "support", "help",
    "status", "dashboard", "login", "auth", "sso", "beta", "demo",
]

_RECORD_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"]


def _resolve(name: str, rtype: str) -> list[str]:
    try:
        answers = dns.resolver.resolve(name, rtype)
        return [r.to_text() for r in answers]
    except Exception:
        return []


def _whois(domain: str) -> dict:
    try:
        import whois  # python-whois
        data = whois.whois(domain)
    except Exception as exc:
        return {"erreur": f"{type(exc).__name__}"}

    def _first(v):
        return v[0] if isinstance(v, list) and v else v

    return {
        "registrar": _first(data.get("registrar")),
        "création": _first(data.get("creation_date")),
        "expiration": _first(data.get("expiration_date")),
        "name_servers": data.get("name_servers"),
        "emails": data.get("emails"),
        "pays": _first(data.get("country")),
    }


def _scan_subdomains(domain: str, workers: int = 30) -> list[tuple[str, list[str]]]:
    found: list[tuple[str, list[str]]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_resolve, f"{sub}.{domain}", "A"): sub
            for sub in _COMMON_SUBDOMAINS
        }
        for future in as_completed(futures):
            sub = futures[future]
            ips = future.result()
            if ips:
                found.append((f"{sub}.{domain}", ips))
    found.sort()
    return found


def run(domain: str) -> dict:
    domain = domain.strip().lower().replace("https://", "").replace("http://", "").strip("/")
    console.print(f"\n[bold]Reconnaissance du domaine[/bold] : [cyan]{domain}[/cyan]\n")

    # 1) Enregistrements DNS
    dns_table = Table(title="Enregistrements DNS")
    dns_table.add_column("Type", style="bold")
    dns_table.add_column("Valeur", overflow="fold")
    records: dict[str, list[str]] = {}
    for rtype in _RECORD_TYPES:
        values = _resolve(domain, rtype)
        records[rtype] = values
        if values:
            dns_table.add_row(rtype, "\n".join(values))
    console.print(dns_table)

    # 2) WHOIS
    whois_data = _whois(domain)
    whois_table = Table(title="WHOIS", show_header=False, box=None)
    whois_table.add_column(style="bold")
    whois_table.add_column(overflow="fold")
    for key, value in whois_data.items():
        if value:
            whois_table.add_row(key, str(value))
    console.print(whois_table)

    # 3) Sous-domaines
    console.print(f"\n[bold]Scan de {len(_COMMON_SUBDOMAINS)} sous-domaines courants…[/bold]")
    subs = _scan_subdomains(domain)
    sub_table = Table(title="Sous-domaines actifs")
    sub_table.add_column("Sous-domaine", style="bold")
    sub_table.add_column("IP(s)", overflow="fold")
    for name, ips in subs:
        sub_table.add_row(name, ", ".join(ips))
    if subs:
        console.print(sub_table)
    else:
        console.print("[dim]Aucun sous-domaine courant résolu.[/dim]")

    return {"domain": domain, "dns": records, "whois": whois_data, "subdomains": subs}
