"""Moteur d'exécution : messages temps réel, progression, annulation.

Le worker appelle ``tool.run(ctx)``. Le ``ctx`` :
  • poste des `EngineLog` (logs live) — thread-safe ;
  • poste des `EngineProgress` pour piloter la ProgressBar ;
  • expose un drapeau d'annulation coopératif (``ctx.cancelled``), complété
    côté moteur par un vrai ``Task.cancel()``.
À la fin, le worker poste un `EngineResult`.
"""

from __future__ import annotations

from textual.message import Message

from core.base import ToolResult


class EngineLog(Message):
    """Une ligne de log émise en cours d'exécution."""

    def __init__(self, level: str, text: str) -> None:
        self.level = level
        self.text = text
        super().__init__()


class EngineProgress(Message):
    """Mise à jour de la barre de progression du panneau d'exécution."""

    def __init__(self, total=None, advance=None, progress=None) -> None:
        self.total = total
        self.advance = advance
        self.progress = progress
        super().__init__()


class EngineResult(Message):
    """Résultat final d'un outil (posté quand le worker se termine)."""

    def __init__(self, tool, value, result: ToolResult) -> None:
        self.tool = tool
        self.value = value
        self.result = result
        super().__init__()


class ToolContext:
    """Passé à ``ToolModule.run`` : saisie, logs, progression, annulation.

    Orchestration : un module (playbook) peut appeler un autre module via
    ``ctx.get_tool(name)`` puis ``await sub.run(ctx.child(nouvelle_valeur))``.
    Le contexte enfant partage écran/config/annulation et forwarde les logs,
    mais NE touche PAS la barre de progression (le playbook la pilote seul).
    """

    def __init__(self, screen, value, parent=None, track_progress=True) -> None:
        self._screen = screen
        self.value = value
        self._parent = parent
        self._track_progress = track_progress
        self._cancelled = False

    @property
    def config(self):
        """Accès à l'API Vault (clés d'API) depuis un module."""
        return self._screen.app.config

    # ---- Orchestration ------------------------------------------------- #
    def child(self, value):
        """Crée un contexte enfant pour appeler un sous-module."""
        return ToolContext(self._screen, value, parent=self, track_progress=False)

    def get_tool(self, name: str):
        """Récupère une instance de module par son nom dans le registre."""
        for tools in self._screen.app.registry.values():
            for tool in tools:
                if tool.name == name:
                    return tool
        return None

    # ---- Annulation (partagée parent ⇄ enfants) ----------------------- #
    def request_cancel(self) -> None:
        """Demande coopérative d'arrêt (le module doit tester ``cancelled``)."""
        self._cancelled = True

    @property
    def cancelled(self) -> bool:
        if self._parent is not None:
            return self._parent.cancelled  # un enfant suit l'état du parent
        return self._cancelled

    # ---- Logs temps réel (toujours forwardés) ------------------------- #
    def log(self, level: str, text: str) -> None:
        self._screen.post_message(EngineLog(level, text))

    def info(self, text: str) -> None:
        self.log("info", text)

    def step(self, text: str) -> None:
        self.log("step", text)

    def ok(self, text: str) -> None:
        self.log("ok", text)

    def warn(self, text: str) -> None:
        self.log("warn", text)

    def err(self, text: str) -> None:
        self.log("err", text)

    # ---- Progression (ignorée pour un enfant) ------------------------- #
    def set_total(self, total: int) -> None:
        if self._track_progress:
            self._screen.post_message(EngineProgress(total=total, progress=0))

    def advance(self, amount: int = 1) -> None:
        if self._track_progress:
            self._screen.post_message(EngineProgress(advance=amount))

    def progress(self, current: int, total: int | None = None) -> None:
        if self._track_progress:
            self._screen.post_message(EngineProgress(total=total, progress=current))
