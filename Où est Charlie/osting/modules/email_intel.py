"""Reconnaissance autour d'une adresse e-mail (sources publiques).

- Validation du format et extraction du domaine.
- Vérification des enregistrements MX (le domaine peut-il recevoir du mail ?).
- Gravatar associé (l'e-mail a-t-il un avatar public ?).
- Variantes de pseudo dérivées, à recouper avec le module `username`.
- HaveIBeenPwned si une clé API est fournie (OSTING_HIBP_KEY).
"""

from __future__ import annotations

import hashlib
import os
import re

import dns.resolver
from rich.table import Table

from ..core import console, make_session

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _mx_records(domain: str) -> list[str]:
    try:
        answers = dns.resolver.resolve(domain, "MX")
        return sorted(str(r.exchange).rstrip(".") for r in answers)
    except Exception:
        return []


def _gravatar(email: str) -> str | None:
    digest = hashlib.md5(email.strip().lower().encode()).hexdigest()
    url = f"https://www.gravatar.com/avatar/{digest}?d=404"
    session = make_session()
    try:
        resp = session.get(url, timeout=10)
        if resp.status_code == 200:
            return f"https://www.gravatar.com/avatar/{digest}"
    except Exception:
        pass
    return None


def _hibp(email: str) -> list[str] | str | None:
    key = os.environ.get("OSTING_HIBP_KEY")
    if not key:
        return None
    session = make_session()
    session.headers.update({"hibp-api-key": key})
    url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}?truncateResponse=true"
    try:
        resp = session.get(url, timeout=15)
    except Exception as exc:
        return f"erreur réseau: {type(exc).__name__}"
    if resp.status_code == 404:
        return []
    if resp.status_code == 200:
        return [b["Name"] for b in resp.json()]
    return f"HTTP {resp.status_code}"


def _username_variants(local: str) -> list[str]:
    base = re.sub(r"[._-]", "", local)
    variants = {local, base, local.replace(".", "_"), local.replace(".", "-")}
    return sorted(v for v in variants if v)


def run(email: str) -> dict:
    if not _EMAIL_RE.match(email):
        console.print(f"[red]Format d'e-mail invalide :[/red] {email}")
        return {}

    local, domain = email.rsplit("@", 1)
    console.print(f"\n[bold]Investigation e-mail[/bold] : [cyan]{email}[/cyan]\n")

    mx = _mx_records(domain)
    gravatar = _gravatar(email)
    breaches = _hibp(email)
    variants = _username_variants(local)

    table = Table(show_header=False, box=None)
    table.add_column(style="bold")
    table.add_column(overflow="fold")
    table.add_row("Domaine", domain)
    table.add_row("MX (reçoit du mail ?)", ", ".join(mx) if mx else "[red]aucun MX[/red]")
    table.add_row("Gravatar", gravatar or "[dim]aucun[/dim]")
    table.add_row("Variantes de pseudo", ", ".join(variants))

    if breaches is None:
        table.add_row("HaveIBeenPwned", "[dim]clé OSTING_HIBP_KEY absente — ignoré[/dim]")
    elif isinstance(breaches, str):
        table.add_row("HaveIBeenPwned", f"[yellow]{breaches}[/yellow]")
    elif breaches:
        table.add_row("HaveIBeenPwned", f"[red]{len(breaches)} fuite(s):[/red] " + ", ".join(breaches))
    else:
        table.add_row("HaveIBeenPwned", "[green]aucune fuite connue[/green]")

    console.print(table)
    console.print(
        "\n[dim]Astuce : passe les variantes au module "
        "[bold]username[/bold] pour recouper les comptes.[/dim]"
    )

    return {
        "email": email,
        "domain": domain,
        "mx": mx,
        "gravatar": gravatar,
        "breaches": breaches,
        "variants": variants,
    }
