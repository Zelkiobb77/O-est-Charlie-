"""Menu interactif coloré (rich) — le visage « joli » d'OSTING."""

from __future__ import annotations

from rich.panel import Panel
from rich.table import Table

from .core import animated_banner, build_static_banner, console, ensure_consent
from .modules import dorks, domain, email_intel, metadata, phone, username

# clé, commande, libellé, description, couleur d'accent
_OPTIONS = [
    ("1", "username", "Pseudo",   "Chercher un pseudo sur ~28 plateformes", "cyan"),
    ("2", "email",    "E-mail",   "Analyser une adresse e-mail",            "cyan"),
    ("3", "domain",   "Domaine",  "WHOIS / DNS / sous-domaines",            "green"),
    ("4", "exif",     "Image",    "Métadonnées + GPS d'une photo",          "green"),
    ("5", "phone",    "Téléphone","Infos d'un numéro de téléphone",         "yellow"),
    ("6", "dorks",    "Dorks",    "Générer des requêtes moteurs",           "yellow"),
    ("7", "full",     "Tout",     "username + email + dorks enchaînés",     "magenta"),
    ("8", "banner",   "Logo",     "Bannière arc-en-ciel qui défile",        "magenta"),
    ("0", "quit",     "Quitter",  "Fermer OSTING",                          "red"),
]

_VALUE_LABEL = {
    "username": "pseudo",
    "email": "adresse e-mail",
    "domain": "domaine (ex: example.com)",
    "exif": "chemin de l'image",
    "phone": "numéro (ex: +33612345678)",
    "dorks": "nom / pseudo / cible",
    "full": "pseudo ou e-mail",
}


def build_menu_panel() -> Panel:
    """Construit le panneau coloré du menu (réutilisable pour un aperçu)."""
    table = Table.grid(padding=(0, 2))
    table.add_column(justify="right")
    table.add_column()
    table.add_column(style="dim")
    for key, _cmd, label, desc, color in _OPTIONS:
        table.add_row(f"[bold {color}]{key}[/]", f"[bold]{label}[/]", desc)

    return Panel(
        table,
        title="[bold]MENU[/bold]",
        subtitle="[dim italic]by Zelkiobb[/dim italic]",
        border_style="magenta",
        padding=(1, 2),
    )


def _render_menu() -> None:
    console.clear()
    console.print(build_static_banner())
    console.print(build_menu_panel())


def _ask_value(cmd: str) -> str:
    label = _VALUE_LABEL.get(cmd, "cible")
    return console.input(f"   [bold green]Cible[/] [dim]({label})[/] : ").strip()


def _run(cmd: str) -> None:
    if cmd == "banner":
        console.print("\n[dim]Ctrl+C pour revenir au menu…[/dim]\n")
        animated_banner(duration=None)
        return

    value = _ask_value(cmd)
    if not value:
        console.print("[yellow]Aucune valeur saisie — annulé.[/yellow]")
        return
    console.print()
    if cmd == "username":
        username.run(value)
    elif cmd == "email":
        email_intel.run(value)
    elif cmd == "domain":
        domain.run(value)
    elif cmd == "exif":
        metadata.run(value)
    elif cmd == "phone":
        phone.run(value)
    elif cmd == "dorks":
        dorks.run(value)
    elif cmd == "full":
        username.run(value)
        if "@" in value:
            email_intel.run(value)
        dorks.run(value)


def run_menu() -> None:
    if not ensure_consent():
        return

    console.clear()
    animated_banner(duration=1.8)  # petite intro animée

    valid = {key: cmd for key, cmd, *_ in _OPTIONS}
    while True:
        _render_menu()
        try:
            choice = console.input("\n   [bold green]Ton choix[/] : ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Fermeture…[/dim]")
            return
        cmd = valid.get(choice)
        if cmd is None:
            continue
        if cmd == "quit":
            console.print("\n[bold magenta]À bientôt ![/bold magenta] [dim]— by Zelkiobb[/dim]\n")
            return
        try:
            _run(cmd)
        except KeyboardInterrupt:
            pass
        console.input("\n   [dim]Entrée pour revenir au menu…[/dim]")
