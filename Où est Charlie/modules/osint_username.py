"""OSINT — recherche RÉELLE et FIABLE d'un pseudo (anti-faux-positifs).

Vérification async (aiohttp + asyncio.gather). Pour chaque plateforme, on ne se
contente PAS du code HTTP : un dictionnaire de signatures décide via l'une de
trois stratégies :

  • "status"  : 200 = présent, 404/410 = absent.
  • "message" : la page renvoie 200 même si absent → on cherche un marqueur
                d'absence (ex: "could not be found"). Présent ⇒ absent.
  • "present" : un marqueur DOIT être là pour que le profil existe
                (ex: la balise tgme_page_title de Telegram).

Les plateformes 100% JS / sous login (Instagram, TikTok, X, YouTube) sont
volontairement exclues : non vérifiables de façon fiable en HTTP simple.
"""

from __future__ import annotations

import asyncio

import aiohttp
from rich.table import Table

from core.base import ToolModule, ToolResult

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Plateformes à signatures FIABLES uniquement (SPA/bloquées exclues).
_SITES = {
    "GitHub":     {"url": "https://github.com/{}",               "check": "status"},
    "GitLab":     {"url": "https://gitlab.com/{}",               "check": "status"},
    "Dev.to":     {"url": "https://dev.to/{}",                   "check": "status"},
    "Docker Hub": {"url": "https://hub.docker.com/v2/users/{}/", "check": "status"},
    "Keybase":    {"url": "https://keybase.io/{}",               "check": "status"},
    "Chess.com":  {"url": "https://api.chess.com/pub/player/{}", "check": "status"},
    "SoundCloud": {"url": "https://soundcloud.com/{}",           "check": "status"},
    # PyPI : soft-404 + WAF → on exige le marqueur "Profile of" du vrai profil.
    "PyPI":       {"url": "https://pypi.org/user/{}/", "check": "present", "present": "profile of"},
    # Steam : 200 même si absent → marqueur d'absence.
    "Steam":      {"url": "https://steamcommunity.com/id/{}", "check": "message",
                   "absent": ["the specified profile could not be found"]},
    # Telegram : la balise n'existe que si le profil existe.
    "Telegram":   {"url": "https://t.me/{}", "check": "present", "present": "tgme_page_title"},
    "HackerNews": {"url": "https://news.ycombinator.com/user?id={}", "check": "message",
                   "absent": ["no such user."]},
}


async def _check(session: aiohttp.ClientSession, name: str, cfg: dict, target: str):
    """Retourne (name, result, status, url) avec result ∈ found/notfound/unknown."""
    url = cfg["url"].format(target)
    method = cfg.get("check", "status")
    try:
        async with session.get(url, allow_redirects=True) as resp:
            status = resp.status
            text = "" if method == "status" else (await resp.text(errors="ignore")).lower()
    except Exception:
        return name, "unknown", None, url

    if method == "status":
        result = "found" if status == 200 else ("notfound" if status in (404, 410) else "unknown")
    elif method == "message":
        if status != 200:
            result = "notfound" if status in (404, 410) else "unknown"
        else:
            # marqueur d'absence présent ⇒ le profil n'existe pas
            result = "notfound" if any(m in text for m in cfg["absent"]) else "found"
    else:  # present
        if status != 200:
            result = "notfound" if status in (404, 410) else "unknown"
        else:
            result = "found" if cfg["present"].lower() in text else "notfound"
    return name, result, status, url


class UsernameFinder(ToolModule):
    name = "Username Finder"
    category = "OSINT"
    icon = "🔎"
    author = "Zelkiobb"
    description = (
        "Recherche async FIABLE d'un pseudo sur 11 plateformes (aiohttp). "
        "Détection par signatures (code HTTP + contenu) — zéro faux positif."
    )
    input_label = "Pseudo cible"
    input_placeholder = "ex: torvalds"

    async def run(self, ctx) -> ToolResult:
        target = (ctx.value or "").strip()
        if not target:
            ctx.err("Aucun pseudo fourni")
            return ToolResult(renderable="[red]Saisis un pseudo à rechercher.[/red]")

        ctx.set_total(len(_SITES))
        ctx.info(f"Recherche fiable de « {target} » sur {len(_SITES)} plateformes…")
        results: dict[str, tuple[str, int | None, str]] = {}

        async def run_check(name: str, cfg: dict) -> None:
            name, result, status, url = await _check(session, name, cfg, target)
            if result == "found":
                ctx.ok(f"Trouvé sur {name}")
            elif result == "notfound":
                ctx.step(f"Introuvable sur {name}")
            else:
                ctx.warn(f"Incertain sur {name} (HTTP {status})")
            ctx.advance()
            results[name] = (result, status, url)

        timeout = aiohttp.ClientTimeout(total=12)
        connector = aiohttp.TCPConnector(limit=40, ttl_dns_cache=300)
        async with aiohttp.ClientSession(
            timeout=timeout, connector=connector, headers={"User-Agent": _UA}
        ) as session:
            await asyncio.gather(*(run_check(n, c) for n, c in _SITES.items()))

        found = sorted((n for n, (r, *_) in results.items() if r == "found"), key=str.lower)
        unknown = sorted((n for n, (r, *_) in results.items() if r == "unknown"), key=str.lower)
        ctx.ok(f"{len(found)} profil(s) confirmé(s) · {len(unknown)} incertain(s)")

        table = Table(title=f"Présence de « {target} »", expand=True)
        table.add_column("Plateforme", style="bold")
        table.add_column("Statut", justify="center")
        table.add_column("Profil", overflow="fold")
        for name in found:
            url = results[name][2]
            table.add_row(name, "[#36e07f]● TROUVÉ[/]", f"[link={url}]{url}[/link]")
        for name in unknown:
            table.add_row(f"[#f3c969]{name}[/]", "[#f3c969]? incertain[/]", "[#3a3a48]à vérifier[/]")
        for name in sorted((n for n in results if results[n][0] == "notfound"), key=str.lower):
            table.add_row(f"[#6f7b8c]{name}[/]", "[#6f7b8c]○ introuvable[/]", "[#3a3a48]—[/]")

        return ToolResult(
            renderable=table,
            data={"target": target, "found": found, "unknown": unknown, "checked": list(_SITES)},
        )
