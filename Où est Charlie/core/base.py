"""Contrat des modules + objet résultat.

Un outil hérite de :class:`ToolModule`, déclare ses métadonnées et implémente
``run(ctx)``. Le ``ctx`` (:class:`~core.engine.ToolContext`) permet d'émettre des
logs en temps réel (``ctx.info/ok/warn/err``) pendant que le worker tourne, et
``run`` renvoie un :class:`ToolResult` (rendu rich + données exportables).

Exemple ::

    from core.base import ToolModule, ToolResult

    class MonOutil(ToolModule):
        name = "Mon Outil"
        category = "NETWORK"
        input_label = "Cible"

        def run(self, ctx):
            ctx.info(f"Connexion à {ctx.value}…")
            ...
            ctx.ok("Terminé")
            return ToolResult(renderable=table, data={"cible": ctx.value})
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from rich.console import RenderableType


@dataclass
class ToolResult:
    """Résultat d'un outil : affichage UI + données structurées pour l'export."""

    renderable: RenderableType
    data: dict = field(default_factory=dict)
    title: str = ""


class ToolModule:
    """Classe de base d'un outil affichable dans le TUI."""

    name: str = "Outil sans nom"
    category: str = "MISC"
    description: str = "Aucune description fournie."
    author: str = "anonyme"
    icon: str = "•"

    #: Si défini, l'UI affiche un champ de saisie avec ce libellé.
    input_label: Optional[str] = None
    input_placeholder: str = ""

    def run(self, ctx) -> ToolResult:
        """Exécute l'outil (dans un worker). Voir le docstring du module."""
        return ToolResult(renderable="[yellow]Module non implémenté.[/yellow]")
