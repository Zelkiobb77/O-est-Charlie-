"""Dashboard d'accueil analytique : stats environnement + mini-graphe ASCII."""

from __future__ import annotations

import platform
import socket

from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text

_ACCENTS = {
    "OSINT": "#a970ff",
    "NETWORK": "#58c7ff",
    "DISCORD": "#c79bff",
    "WEB": "#f3c969",
}


def _local_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))  # ne transmet rien (UDP) : route locale
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return "127.0.0.1"


def render_home(registry: dict, worker_state: str, config=None) -> RenderableType:
    """Construit le panneau de contrôle affiché par défaut."""
    total = sum(len(tools) for tools in registry.values())

    title = Text("◢  CONTROL PANEL  ◣", style="bold #a970ff", justify="center")

    # --- Statistiques environnement ---
    stats = Table.grid(padding=(0, 3))
    stats.add_column(style="#7a7a8c", justify="right")
    stats.add_column(style="#e8e8f2")
    stats.add_row(
        "Modules chargés",
        f"[b #a970ff]{total}[/] outils · [b]{len(registry)}[/] catégories",
    )
    stats.add_row("Système", f"{platform.system()} {platform.release()}")
    stats.add_row("Hôte", socket.gethostname())
    stats.add_row("IP locale", f"[#58c7ff]{_local_ip()}[/]")
    stats.add_row("IP publique", "203.0.113.37  [#3a3a48](demo)[/]")

    if worker_state == "running":
        stats.add_row("Worker", "[b #f3c969]● RUNNING[/]  [#7a7a8c]exécution en cours…[/]")
    else:
        stats.add_row("Worker", "[b #36e07f]● IDLE[/]  [#7a7a8c]en attente[/]")

    if config is not None:
        defined = sum(1 for *_, ok in config.status() if ok)
        stats.add_row("API Vault", f"[#e8e8f2]{defined}/{len(config.KNOWN)}[/] clés configurées")

    # --- Mini-graphe : modules par catégorie ---
    graph = Text()
    max_count = max((len(t) for t in registry.values()), default=1)
    for category, tools in registry.items():
        count = len(tools)
        bar = "█" * count + "░" * (max_count - count)
        color = _ACCENTS.get(category, "#a970ff")
        graph.append(f"  {category:<9}", style="#c8c8d4")
        graph.append(bar, style=color)
        graph.append(f"  {count}\n", style="#7a7a8c")

    return Group(
        title,
        Text(),
        stats,
        Text(),
        Text("  Modules par catégorie", style="bold #58c7ff"),
        graph,
        Text(
            "  ▸ Choisis une catégorie (←), puis un module (→) pour commencer.",
            style="italic #7a7a8c",
        ),
    )
