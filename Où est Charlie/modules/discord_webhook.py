"""DISCORD — inspecteur de webhook RÉEL (requête HTTP async via httpx).

Interroge l'API Discord publique pour valider un webhook et récupérer ses
métadonnées (nom, avatar, channel/guild). Le token est fourni par l'utilisateur
dans l'URL : usage légitime d'inspection de SES propres webhooks / d'un
périmètre autorisé.
"""

from __future__ import annotations

import re

import httpx
from rich.table import Table

from core.base import ToolModule, ToolResult

_WEBHOOK_RE = re.compile(
    r"https?://(?:\w+\.)?discord(?:app)?\.com/api/webhooks/(\d+)/([\w-]+)"
)


class WebhookInspector(ToolModule):
    name = "Webhook Inspector"
    category = "DISCORD"
    icon = "🪝"
    author = "Zelkiobb"
    description = (
        "Vérifie EN DIRECT un webhook Discord via l'API (requête HTTP async) : "
        "validité, nom, avatar, channel ID, guild ID."
    )
    input_label = "URL de webhook"
    input_placeholder = "https://discord.com/api/webhooks/<id>/<token>"

    async def run(self, ctx) -> ToolResult:
        match = _WEBHOOK_RE.search((ctx.value or "").strip())
        if not match:
            ctx.err("URL de webhook invalide")
            return ToolResult(renderable="[red]URL de webhook Discord invalide.[/red]")

        webhook_id, token = match.group(1), match.group(2)
        api = f"https://discord.com/api/webhooks/{webhook_id}/{token}"
        ctx.info(f"GET API Discord · webhook {webhook_id}")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(api)
        except Exception as exc:
            ctx.err(f"Erreur réseau : {type(exc).__name__}")
            return ToolResult(
                renderable=f"[red]Erreur réseau : {exc}[/red]",
                data={"webhook_id": webhook_id, "error": str(exc)},
            )

        ctx.step(f"Réponse HTTP {resp.status_code}")
        if resp.status_code == 404:
            ctx.err("Webhook supprimé ou invalide (404)")
            return ToolResult(
                renderable="[red]Webhook invalide ou supprimé (404).[/red]",
                data={"webhook_id": webhook_id, "status": 404},
            )
        if resp.status_code != 200:
            ctx.warn(f"Réponse inattendue : {resp.status_code}")
            return ToolResult(
                renderable=f"[#f3c969]Réponse HTTP {resp.status_code}.[/]",
                data={"webhook_id": webhook_id, "status": resp.status_code},
            )

        info = resp.json()
        name = info.get("name")
        channel_id = info.get("channel_id")
        guild_id = info.get("guild_id")
        avatar = info.get("avatar")
        avatar_url = (
            f"https://cdn.discordapp.com/avatars/{webhook_id}/{avatar}.png"
            if avatar
            else "(avatar par défaut)"
        )
        ctx.ok(f"Webhook valide : « {name} »")

        table = Table(show_header=False, expand=True)
        table.add_column(style="bold cyan")
        table.add_column(overflow="fold")
        table.add_row("Nom", str(name))
        table.add_row("Webhook ID", webhook_id)
        table.add_row("Channel ID", str(channel_id))
        table.add_row("Guild ID", str(guild_id) if guild_id else "—")
        table.add_row("Avatar", avatar_url)
        table.add_row("Statut", "[#36e07f]✓ actif (HTTP 200)[/]")
        return ToolResult(
            renderable=table,
            data={
                "webhook_id": webhook_id,
                "name": name,
                "channel_id": channel_id,
                "guild_id": guild_id,
                "avatar": avatar_url,
                "status": 200,
            },
        )
