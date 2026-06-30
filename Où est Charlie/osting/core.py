"""Utilitaires partagés : session HTTP, console, bannière et garde éthique."""

from __future__ import annotations

import colorsys
import os
import sys
import time
from pathlib import Path

import requests
from rich.console import Console
from rich.live import Live
from rich.text import Text

from . import __version__


def _setup_console_encoding() -> None:
    """Force l'UTF-8 sur la console Windows pour éviter le mojibake (é, —, …)."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except Exception:
            pass
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass


_setup_console_encoding()
console = Console()

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Fichier marquant que l'utilisateur a lu et accepté l'avertissement.
_ACK_FILE = Path.home() / ".osting_ack"

BANNER_TEXT = "OU EST CHARLY ?"

LEGAL_NOTICE = (
    "[bold yellow]Usage légitime uniquement.[/bold yellow] OSTING interroge des sources "
    "publiques. L'agrégation de données peut devenir illégale (harcèlement, atteinte à la "
    "vie privée, RGPD) selon l'intention et la juridiction. N'investigue que : ta propre "
    "empreinte, un périmètre pour lequel tu as une autorisation écrite, ou des cibles de "
    "challenge/CTF. Tu es seul responsable de ton usage."
)


def make_session(timeout: int = 10) -> requests.Session:
    """Crée une session HTTP avec un User-Agent réaliste."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    session.request_timeout = timeout  # type: ignore[attr-defined]
    return session


def _figlet_lines(text: str) -> list[str]:
    """Rend `text` en grandes lettres ASCII (figlet), avec repli simple."""
    try:
        from pyfiglet import Figlet
        art = Figlet(font="standard").renderText(text)
        return [line for line in art.rstrip("\n").split("\n")]
    except Exception:
        return [text]


def _rainbow_rgb(hue: float) -> tuple[int, int, int]:
    r, g, b = colorsys.hsv_to_rgb(hue % 1.0, 1.0, 1.0)
    return int(r * 255), int(g * 255), int(b * 255)


CREDIT = "by Zelkiobb"


def _append_credit(frame: Text, width: int, hue_step: float, elapsed: float) -> None:
    """Ajoute la signature centrée et colorée sous la bannière."""
    line = CREDIT.center(width)
    for col, ch in enumerate(line):
        r, g, b = _rainbow_rgb(col * hue_step - elapsed * 0.35)
        frame.append(ch, style=f"bold italic rgb({r},{g},{b})")


def build_static_banner(text: str = BANNER_TEXT, hue_step: float = 0.018) -> Text:
    """Construit la bannière colorée (non animée) sous forme de `rich.Text`."""
    lines = _figlet_lines(text)
    art_width = max((len(line) for line in lines), default=len(CREDIT))
    out = Text()
    for line in lines:
        for col, ch in enumerate(line):
            r, g, b = _rainbow_rgb(col * hue_step)
            out.append(ch, style=f"bold rgb({r},{g},{b})")
        out.append("\n")
    _append_credit(out, art_width, hue_step, 0.0)
    return out


def animated_banner(
    text: str = BANNER_TEXT,
    duration: float | None = 3.0,
    fps: int = 20,
    hue_step: float = 0.018,
    scroll: int = 2,
) -> None:
    """Bannière arc-en-ciel qui défile horizontalement, signée « by Zelkiobb ».

    `duration=None` → défile sans fin jusqu'à Ctrl+C.
    """
    lines = _figlet_lines(text)
    height = len(lines)
    if height == 0:
        return

    # Sortie non-interactive (pipe, fichier) : un seul rendu coloré statique.
    if not console.is_terminal:
        console.print(build_static_banner(text, hue_step))
        return

    width = max((len(line) for line in lines), default=1)
    gap = 12  # espace entre deux passages du texte
    strip = [line.ljust(width) + " " * gap for line in lines]
    total = width + gap
    window = max(1, console.width - 1)
    interval = 1.0 / fps

    start = time.time()
    offset = 0
    try:
        with Live(console=console, refresh_per_second=fps, transient=False) as live:
            while duration is None or (time.time() - start) < duration:
                elapsed = time.time() - start
                frame = Text()
                for row in range(height):
                    line = strip[row]
                    for i in range(window):
                        ch = line[(offset + i) % total]
                        hue = ((offset + i) * hue_step) + elapsed * 0.35
                        r, g, b = _rainbow_rgb(hue)
                        frame.append(ch, style=f"bold rgb({r},{g},{b})")
                    frame.append("\n")
                _append_credit(frame, window, hue_step, elapsed)
                live.update(frame)
                offset = (offset + scroll) % total
                time.sleep(interval)
    except KeyboardInterrupt:
        pass


def show_banner() -> None:
    """Bannière animée courte au lancement (ne bloque pas l'outil)."""
    animated_banner(duration=3.0)


def ensure_consent(assume_yes: bool = False) -> bool:
    """Affiche l'avertissement et exige une acceptation (une seule fois).

    Retourne True si l'utilisateur peut continuer.
    """
    if _ACK_FILE.exists() or os.environ.get("OSTING_ACK") == "1":
        return True

    console.print(f"\n[on yellow][black] AVERTISSEMENT LÉGAL [/black][/on yellow]")
    console.print(LEGAL_NOTICE)

    if assume_yes:
        accepted = True
    else:
        try:
            answer = console.input(
                "\n[bold]Confirmes-tu un usage légal et autorisé ? [/bold](o/N) "
            )
        except (EOFError, KeyboardInterrupt):
            answer = "n"
        accepted = answer.strip().lower() in {"o", "oui", "y", "yes"}

    if accepted:
        try:
            _ACK_FILE.write_text("acknowledged\n", encoding="utf-8")
        except OSError:
            pass  # Pas grave si on ne peut pas persister.
        return True

    console.print("[red]Acceptation refusée — arrêt.[/red]")
    return False
