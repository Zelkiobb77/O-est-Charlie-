"""OSTING SUITE — dashboard TUI (Textual).

Démarrage : SplashScreen animé → MainScreen.

Mécanique clé (ce que tu voulais voir) :
  • L'exécution d'un outil part dans un worker thread (@work) → l'UI ne fige
    JAMAIS, même sur un scan lent ou un timeout API.
  • Le worker appelle tool.run(ctx). ctx.info/ok/warn/err postent des messages
    EngineLog (thread-safe) que MainScreen affiche EN DIRECT dans la live
    console (#console, un RichLog). En fin de course, EngineResult porte le
    résultat structuré (affiché + exportable).

Raccourcis : ^R Exécuter · ^E Export · ^S Vault · ⎋ Accueil · ^Q Quitter.
"""

from __future__ import annotations

import asyncio
import inspect
from datetime import datetime
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Input, Label, ListView, ProgressBar, RichLog, Static
from textual.worker import Worker, WorkerState

from core.base import ToolResult
from core.config import ConfigVault
from core.engine import EngineLog, EngineProgress, EngineResult, ToolContext
from core.exporter import export_result
from core.home import render_home
from core.loader import discover_tools
from core.widgets import (
    CategoryItem,
    StatusFooter,
    ToolItem,
    TopBar,
    render_logo,
    render_tool_header,
)

# Tag + couleur par niveau de log.
_LEVELS = {
    "info": ("[~]", "#58c7ff"),
    "step": ("[~]", "#6f7b8c"),
    "ok": ("[+]", "#36e07f"),
    "warn": ("[!]", "#f3c969"),
    "err": ("[✗]", "#ff6b6b"),
}


# ====================================================================== #
#  Splash screen
# ====================================================================== #
class SplashScreen(Screen):
    """Écran de démarrage : logo en fade-in + chargement des modules."""

    def compose(self) -> ComposeResult:
        with Vertical(id="splash-box"):
            yield Static(render_logo(), id="splash-logo")
            yield Static("R E D - T E A M   R E C O N   F R A M E W O R K", id="splash-tagline")
            yield Static("", id="splash-spacer")
            yield ProgressBar(total=100, show_eta=False, id="loading-bar")
            yield Static("", id="loading-status")

    def on_mount(self) -> None:
        box = self.query_one("#splash-box")
        box.styles.opacity = 0.0
        box.styles.animate("opacity", value=1.0, duration=0.9)
        self._steps = self.app.loading_steps()
        self._index = 0
        self._done = False
        self._timer = self.set_interval(0.22, self._advance)

    def _advance(self) -> None:
        if self._done:
            return
        bar = self.query_one("#loading-bar", ProgressBar)
        status = self.query_one("#loading-status", Static)
        if self._index < len(self._steps):
            status.update(f"[#58c7ff]▸[/] [#b8b8c8]{self._steps[self._index]}[/] [#3a3a48]…[/]")
            bar.advance(100 / len(self._steps))
            self._index += 1
        else:
            self._finish()

    def _finish(self) -> None:
        if self._done:
            return
        self._done = True
        self._timer.stop()
        self.query_one("#loading-bar", ProgressBar).update(progress=100)
        self.query_one("#loading-status", Static).update("[#36e07f]✓ Système prêt[/]")
        self.set_timer(0.4, lambda: self.app.switch_screen(MainScreen()))

    def on_key(self, event) -> None:
        self._finish()


# ====================================================================== #
#  API Vault (configuration)
# ====================================================================== #
class SettingsScreen(ModalScreen):
    """Onglet Settings : lecture/édition des clés d'API (config.json)."""

    BINDINGS = [Binding("escape", "close", "Fermer")]

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-box"):
            yield Static("🔐  API VAULT", id="settings-title")
            yield Static(
                "Clés stockées en local dans [b]config.json[/b] (gitignoré). "
                "Repli automatique sur les variables d'environnement.",
                id="settings-sub",
            )
            for key, label in ConfigVault.KNOWN:
                with Horizontal(classes="set-row"):
                    yield Label(label, classes="set-label")
                    yield Input(
                        value=self.app.config.get_raw(key),
                        password=True,
                        placeholder="(non défini)",
                        id=f"set-{key}",
                        classes="set-input",
                    )
            with Horizontal(id="settings-actions"):
                yield Button("💾  Enregistrer", id="save-settings")
                yield Button("✕  Fermer", id="close-settings")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-settings":
            for key, _ in ConfigVault.KNOWN:
                self.app.config.set(key, self.query_one(f"#set-{key}", Input).value)
            self.app.config.save()
            self.app.notify("API Vault enregistré ✓", title="Configuration")
            self.app.pop_screen()
        elif event.button.id == "close-settings":
            self.app.pop_screen()

    def action_close(self) -> None:
        self.app.pop_screen()


# ====================================================================== #
#  Écran principal (dashboard)
# ====================================================================== #
class MainScreen(Screen):
    BINDINGS = [
        Binding("ctrl+r", "run_tool", "Exécuter"),
        Binding("ctrl+x", "cancel", "Annuler"),
        Binding("ctrl+e", "export", "Export"),
        Binding("ctrl+s", "settings", "Vault"),
        Binding("ctrl+l", "clear_console", "Clear"),
        Binding("escape", "go_home", "Accueil"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.current_tool = None
        self._mode = "home"        # "home" | "tool"
        self._busy = False
        self._worker_state = "idle"
        self._last = None          # (tool, value, result) pour l'export
        self._worker = None        # handle du worker en cours (pour l'annulation)
        self._worker_kind = None   # "async" | "thread"
        self._ctx = None           # contexte de l'exécution en cours

    # ---- Composition -------------------------------------------------- #
    def compose(self) -> ComposeResult:
        yield TopBar(id="topbar")
        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                yield ListView(
                    *[
                        CategoryItem(category, len(tools))
                        for category, tools in self.app.registry.items()
                    ],
                    id="categories",
                )
            with Vertical(id="main"):
                yield ListView(id="tools")
                with Vertical(id="detail"):
                    yield Static(id="detail-head")
                    with Horizontal(id="controls"):
                        yield Input(id="tool-input", placeholder="")
                        yield Button("▶  EXÉCUTER", id="run-btn")
                    yield ProgressBar(id="tool-progress", show_eta=False)
                    yield RichLog(id="console", markup=True, highlight=True, wrap=True)
        yield StatusFooter(id="statusfooter")

    async def on_mount(self) -> None:
        self.query_one("#sidebar").border_title = "CATÉGORIES"
        self.query_one("#tools").border_title = "MODULES"
        self.query_one("#detail").border_title = "TABLEAU DE BORD"
        self.query_one("#console").border_title = "LIVE CONSOLE"

        self._show_home()
        console = self.query_one("#console", RichLog)
        console.write("[#36e07f][+][/] Moteur OSTING initialisé.")
        console.write("[#58c7ff][~][/] En attente d'un module… (← catégorie, → module)")

        categories = self.query_one("#categories", ListView)
        categories.focus()
        if self.app.registry:
            categories.index = 0
            await self._load_category(next(iter(self.app.registry)))

    # ---- Vues : accueil vs outil -------------------------------------- #
    def _show_home(self) -> None:
        self._mode = "home"
        self.query_one("#detail").border_title = "TABLEAU DE BORD"
        self.query_one("#detail-head", Static).update(
            render_home(self.app.registry, self._worker_state, self.app.config)
        )
        self.query_one("#controls").display = False
        self.query_one("#tool-progress").display = False

    def _show_tool(self, tool) -> None:
        self._mode = "tool"
        self.current_tool = tool
        self.query_one("#detail").border_title = "EXÉCUTION"
        self.query_one("#detail-head", Static).update(render_tool_header(tool))
        self.query_one("#controls").display = True
        self.query_one("#tool-progress").display = False
        tool_input = self.query_one("#tool-input", Input)
        if tool.input_label:
            tool_input.placeholder = tool.input_placeholder or tool.input_label
            tool_input.value = ""
            tool_input.display = True
        else:
            tool_input.display = False

    # ---- Navigation --------------------------------------------------- #
    async def _load_category(self, category: str) -> None:
        tools = self.app.registry.get(category, [])
        tool_list = self.query_one("#tools", ListView)
        await tool_list.clear()
        for tool in tools:
            await tool_list.append(ToolItem(tool))
        if tools:
            tool_list.index = 0  # n'affiche PAS l'outil tant que la liste n'a pas le focus

    async def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is None:
            return
        if event.list_view.id == "categories":
            await self._load_category(event.item.category)
            if self._mode != "home":
                self._show_home()
        elif event.list_view.id == "tools" and isinstance(event.item, ToolItem):
            if self.query_one("#tools", ListView).has_focus:
                self._show_tool(event.item.tool)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "categories":
            tools = self.query_one("#tools", ListView)
            tools.focus()
            if isinstance(tools.highlighted_child, ToolItem):
                self._show_tool(tools.highlighted_child.tool)
        elif event.list_view.id == "tools" and isinstance(event.item, ToolItem):
            self._show_tool(event.item.tool)
            if event.item.tool.input_label:
                self.query_one("#tool-input", Input).focus()
            else:
                self.action_run_tool()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "tool-input":
            self.action_run_tool()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run-btn":
            self.action_run_tool()

    # ---- Worker async + live console ---------------------------------- #
    def action_run_tool(self) -> None:
        if self._mode != "tool" or self.current_tool is None:
            return
        console = self.query_one("#console", RichLog)
        if self._busy:
            console.write("[#f3c969][!][/] Moteur occupé — attends la fin du job en cours.")
            return
        tool = self.current_tool
        value = None
        if tool.input_label:
            value = self.query_one("#tool-input", Input).value.strip()

        self._ctx = ToolContext(self, value)
        self._busy = True
        self._set_worker_state("running")

        # Barre de progression : indéterminée tant que l'outil n'a pas set_total().
        bar = self.query_one("#tool-progress", ProgressBar)
        bar.total = None
        bar.progress = 0
        bar.display = True

        kind = "async" if inspect.iscoroutinefunction(tool.run) else "thread"
        self._worker_kind = kind
        console.write(
            f"[#a970ff]┌─[/] [b]{tool.name}[/b] [#3a3a48]· worker {kind} · ^X pour annuler[/]"
        )
        if kind == "async":
            self._worker = self._run_async(tool, value, self._ctx)
        else:
            self._worker = self._run_thread(tool, value, self._ctx)

    @work
    async def _run_async(self, tool, value, ctx) -> None:
        """Outils async (asyncio/httpx) : tournent sur la boucle, sans bloquer."""
        try:
            result = await tool.run(ctx)
        except asyncio.CancelledError:
            # Annulation dure (Task.cancel) non interceptée par l'outil.
            ctx.warn("Tâche annulée")
            result = ToolResult(
                renderable="[#f3c969][!] Tâche interrompue par l'utilisateur.[/]",
                data={"cancelled": True},
            )
            self.post_message(EngineResult(tool, value, result))
            return
        except Exception as exc:  # un outil ne doit jamais crasher l'app
            ctx.err(f"Exception : {exc}")
            result = ToolResult(renderable=f"[#ff6b6b]✗ {exc}[/]", data={"error": str(exc)})
        self.post_message(EngineResult(tool, value, result))

    @work(thread=True)
    def _run_thread(self, tool, value, ctx) -> None:
        """Outils synchrones / bloquants : isolés dans un THREAD (annulation coopérative)."""
        try:
            result = tool.run(ctx)
        except Exception as exc:
            ctx.err(f"Exception : {exc}")
            result = ToolResult(renderable=f"[#ff6b6b]✗ {exc}[/]", data={"error": str(exc)})
        self.post_message(EngineResult(tool, value, result))

    def on_engine_log(self, message: EngineLog) -> None:
        tag, color = _LEVELS.get(message.level, ("[~]", "#58c7ff"))
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.query_one("#console", RichLog).write(
            f"[#3a3a48]{timestamp}[/] [{color}]{tag}[/] {message.text}"
        )

    def on_engine_progress(self, message: EngineProgress) -> None:
        bar = self.query_one("#tool-progress", ProgressBar)
        if message.total is not None:
            bar.total = message.total
            bar.progress = 0
        if message.progress is not None:
            bar.progress = message.progress
        if message.advance is not None:
            bar.advance(message.advance)

    def on_engine_result(self, message: EngineResult) -> None:
        console = self.query_one("#console", RichLog)
        console.write(message.result.renderable)
        console.write("[#a970ff]└─[/] [#3a3a48]job terminé · Ctrl+E pour exporter[/]\n")
        self._last = (message.tool, message.value, message.result)
        self._busy = False
        self._worker = None
        self._worker_kind = None
        self._ctx = None
        self.query_one("#tool-progress").display = False
        self._set_worker_state("idle")

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Filet de sécurité : worker stoppé (annulation/erreur) sans résultat."""
        if (
            event.worker is self._worker
            and event.state in (WorkerState.CANCELLED, WorkerState.ERROR)
            and self._busy
        ):
            self.query_one("#console", RichLog).write("[#f3c969]┄ worker arrêté.[/]")
            self._busy = False
            self._worker = None
            self._ctx = None
            self.query_one("#tool-progress").display = False
            self._set_worker_state("idle")

    def _set_worker_state(self, state: str) -> None:
        self._worker_state = state
        self.app.busy = state == "running"  # pilote l'indicateur animé du header
        if self._mode == "home":
            self.query_one("#detail-head", Static).update(
                render_home(self.app.registry, state, self.app.config)
            )

    # ---- Actions ------------------------------------------------------ #
    def action_cancel(self) -> None:
        """Kill switch (Ctrl+X) : actif seulement pendant un job."""
        if not self._busy:
            return
        self.query_one("#console", RichLog).write(
            "[#f3c969]┄[/] [#f3c969]annulation demandée (Ctrl+X)…[/]"
        )
        # 1) drapeau coopératif : seul moyen propre pour un worker thread
        #    (un thread Python ne peut pas être tué de force).
        if self._ctx is not None:
            self._ctx.request_cancel()
        # 2) annulation DURE réservée aux workers async (interrompt un await
        #    long comme un httpx.get) ; jamais sur un thread (état faussé).
        if self._worker_kind == "async" and self._worker is not None:
            try:
                self._worker.cancel()
            except Exception:
                pass

    def action_go_home(self) -> None:
        if self._busy:
            return  # on ne quitte pas la vue pendant un job
        self.query_one("#categories", ListView).focus()
        self._show_home()

    def action_clear_console(self) -> None:
        self.query_one("#console", RichLog).clear()

    def action_settings(self) -> None:
        self.app.push_screen(SettingsScreen())

    def action_export(self) -> None:
        console = self.query_one("#console", RichLog)
        if self._last is None:
            console.write("[#f3c969][!][/] Rien à exporter — lance d'abord un module.")
            return
        tool, value, result = self._last
        try:
            paths = export_result(tool.name, value, result)
        except Exception as exc:
            console.write(f"[#ff6b6b][✗][/] Export échoué : {exc}")
            return
        console.write("[#36e07f][+][/] Rapport exporté :")
        for path in paths:
            console.write(f"     [#58c7ff]→[/] exports/{path.name}")


# ====================================================================== #
#  Application
# ====================================================================== #
class DashboardApp(App):
    CSS_PATH = str(Path(__file__).parent / "styles" / "dashboard.tcss")
    TITLE = "OSTING SUITE"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quitter"),
        Binding("ctrl+c", "quit", "Quitter", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.registry = discover_tools()
        self.config = ConfigVault()
        self.busy = False  # lu par le TopBar pour l'indicateur worker animé

    def on_mount(self) -> None:
        self.push_screen(SplashScreen())

    def loading_steps(self) -> list[str]:
        steps = ["Initialisation du noyau OSTING", "Montage du moteur de modules"]
        for category in self.registry:
            steps.append(f"Chargement du pack {category} ({len(self.registry[category])} outils)")
        steps += ["Initialisation de l'API Vault", "Établissement du lien sécurisé"]
        return steps


if __name__ == "__main__":
    DashboardApp().run()
