"""Auto-découverte des modules présents dans ``modules/``.

Le loader importe chaque fichier Python du dossier ``modules/``, repère les
classes héritant de :class:`~core.base.ToolModule`, les instancie et les
regroupe par catégorie. C'est ce qui permet le « drag & drop » d'un nouvel
outil : il suffit de déposer un fichier, sans toucher au dashboard.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from pathlib import Path

from core.base import ToolModule

# Ordre d'affichage préféré des catégories dans la sidebar.
_CATEGORY_ORDER = {"AUTOMATION": 0, "OSINT": 1, "NETWORK": 2, "DISCORD": 3, "WEB": 4}

_MODULES_DIR = Path(__file__).resolve().parent.parent / "modules"


def discover_tools() -> dict[str, list[ToolModule]]:
    """Retourne ``{catégorie: [instances de ToolModule]}`` triées."""
    registry: dict[str, list[ToolModule]] = {}

    for info in pkgutil.iter_modules([str(_MODULES_DIR)]):
        if info.name.startswith("_"):
            continue
        try:
            module = importlib.import_module(f"modules.{info.name}")
        except Exception as exc:  # un module cassé ne doit pas tuer l'app
            print(f"[loader] import échoué pour '{info.name}': {exc}")
            continue

        for _, obj in inspect.getmembers(module, inspect.isclass):
            # On ne garde que les classes définies DANS ce module et qui
            # héritent réellement de ToolModule (pas la base elle-même).
            if (
                issubclass(obj, ToolModule)
                and obj is not ToolModule
                and obj.__module__ == module.__name__
            ):
                try:
                    tool = obj()
                except Exception as exc:
                    print(f"[loader] instanciation échouée pour '{obj.__name__}': {exc}")
                    continue
                registry.setdefault(tool.category, []).append(tool)

    # Tri des outils par nom, puis des catégories selon l'ordre préféré.
    for tools in registry.values():
        tools.sort(key=lambda t: t.name.lower())

    return dict(
        sorted(registry.items(), key=lambda kv: (_CATEGORY_ORDER.get(kv[0], 99), kv[0]))
    )
