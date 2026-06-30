"""Widgets custom du dashboard : header live, logo dégradé, items, footer.

Identité visuelle « OSTING » : fond très sombre, accents violet néon / bleu
glace / doré. Les couleurs sont définies ici (côté rendu rich) et dans
``styles/dashboard.tcss`` (côté layout Textual).
"""

from __future__ import annotations

from datetime import datetime

from rich.console import RenderableType
from rich.table import Table
from rich.text import Text
from textual.widgets import Label, ListItem, Static

from core.base import ToolModule

# --- Palette (rgb) pour les rendus rich -------------------------------- #
VIOLET = (169, 112, 255)   # #a970ff
ICE = (88, 199, 255)       # #58c7ff
GOLD = (243, 201, 105)     # #f3c969
GREEN = (54, 224, 127)     # #36e07f
GREEN_DIM = (31, 125, 73)  # #1f7d49
DIM = "#7a7a8c"

CATEGORY_ICONS = {
    "AUTOMATION": "⚡",
    "OSINT": "🛰",
    "NETWORK": "🌐",
    "DISCORD": "💬",
    "WEB": "🕸",
    "MISC": "◆",
}


def _hex(rgb: tuple[int, int, int]) -> str:
    return f"rgb({rgb[0]},{rgb[1]},{rgb[2]})"


def _lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))  # type: ignore[return-value]


# --- Logo ASCII ------------------------------------------------------- #
def logo_lines() -> list[str]:
    """Retourne le logo OSTING en ASCII (font figlet 'doom'), avec repli."""
    try:
        from pyfiglet import Figlet
        art = Figlet(font="doom").renderText("OSTING")
        lines = [line for line in art.split("\n") if line.strip()]
        if lines:
            return lines
    except Exception:
        pass
    return ["O S T I N G"]


def render_logo() -> Text:
    """Logo coloré avec un dégradé vertical violet → bleu glace."""
    lines = logo_lines()
    text = Text(justify="center")
    n = max(1, len(lines) - 1)
    for i, line in enumerate(lines):
        color = _lerp(VIOLET, ICE, i / n)
        text.append(line + "\n", style=f"bold {_hex(color)}")
    return text


# Spinner braille (feedback worker).
_SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


# --- Header live ------------------------------------------------------- #
class TopBar(Static):
    """En-tête live : marque · indicateur worker animé · horloge.

    L'indicateur de droite bascule automatiquement :
      • idle   → pastille verte « ● ONLINE »
      • busy   → spinner braille doré animé « ⠹ WORKER ACTIF »
    Il lit ``self.app.busy`` (mis à jour par MainScreen) à 10 fps.
    """

    def on_mount(self) -> None:
        self._frame = 0
        self._tick()
        self.set_interval(0.1, self._tick)  # 10 fps : spinner fluide

    def _tick(self) -> None:
        self._frame += 1
        now = datetime.now()

        left = Text()
        left.append("◈ ", style=f"bold {_hex(VIOLET)}")
        left.append("OSTING", style=f"bold {_hex(VIOLET)}")
        left.append(" SUITE", style=f"bold {_hex(ICE)}")
        left.append("   ·   red-team recon framework", style=DIM)

        right = Text()
        if getattr(self.app, "busy", False):
            spin = _SPINNER[self._frame % len(_SPINNER)]
            right.append(f"{spin} ", style=f"bold {_hex(GOLD)}")
            right.append("WORKER ACTIF", style=f"bold {_hex(GOLD)}")
        else:
            dot = GREEN if (self._frame // 5) % 2 == 0 else GREEN_DIM
            right.append("● ", style=f"bold {_hex(dot)}")
            right.append("ONLINE", style=f"bold {_hex(GREEN)}")
        right.append("     ⏱ ", style=DIM)
        right.append(now.strftime("%H:%M:%S"), style=f"bold {_hex(ICE)}")
        right.append("   " + now.strftime("%d/%m/%Y"), style=DIM)

        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="right")
        grid.add_row(left, right)
        self.update(grid)


# --- Footer épuré ------------------------------------------------------ #
class StatusFooter(Static):
    """Barre de raccourcis, style 'keycaps' moderne."""

    HINTS = [
        ("↑ ↓", "Naviguer"),
        ("⏎", "Valider"),
        ("^R", "Exécuter"),
        ("^X", "Annuler"),
        ("^E", "Export"),
        ("^S", "Vault"),
        ("^Q", "Quitter"),
    ]

    def on_mount(self) -> None:
        chips = [
            f"[on #17171f] [b #a970ff]{key}[/] [/][#7a7a8c] {label}[/]"
            for key, label in self.HINTS
        ]
        self.update("   ".join(chips))


# --- Items de listes --------------------------------------------------- #
class CategoryItem(ListItem):
    def __init__(self, category: str, count: int) -> None:
        icon = CATEGORY_ICONS.get(category, "◆")
        super().__init__(Label(f" {icon}  [b]{category}[/b]  [#7a7a8c]({count})[/]"))
        self.category = category


class ToolItem(ListItem):
    def __init__(self, tool: ToolModule) -> None:
        super().__init__(Label(f" [#a970ff]{tool.icon}[/]  {tool.name}"))
        self.tool = tool


def render_tool_header(tool: ToolModule) -> RenderableType:
    """En-tête du panneau de détail pour l'outil sélectionné."""
    text = Text()
    text.append("▌ ", style=f"bold {_hex(VIOLET)}")
    text.append(f"{tool.name}\n", style="bold #e8e8f2")
    text.append("  " + tool.category, style=f"bold {_hex(ICE)}")
    text.append("  ·  ", style="#3a3a48")
    text.append(f"by {tool.author}\n\n", style=f"italic {DIM}")
    text.append("  " + tool.description, style="#b8b8c8")
    return text
