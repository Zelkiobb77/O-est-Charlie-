"""DISCORD — décodage d'un Snowflake (réellement fonctionnel, hors-ligne)."""

from __future__ import annotations

from datetime import datetime, timezone

from rich.table import Table

from core.base import ToolModule, ToolResult

_DISCORD_EPOCH = 1420070400000


class DiscordSnowflake(ToolModule):
    name = "Snowflake Decoder"
    category = "DISCORD"
    icon = "❄"
    author = "Zelkiobb"
    description = "Décode un ID Discord : date de création, worker, process, incrément."
    input_label = "ID Discord"
    input_placeholder = "ex: 175928847299117063"

    def run(self, ctx) -> ToolResult:
        raw = (ctx.value or "").strip()
        ctx.info(f"Décodage du snowflake {raw or '(vide)'}")
        try:
            snowflake = int(raw)
        except ValueError:
            ctx.err("ID non numérique")
            return ToolResult(renderable="[red]Fournis un ID Discord numérique.[/red]")

        timestamp_ms = (snowflake >> 22) + _DISCORD_EPOCH
        created = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        worker = (snowflake >> 17) & 0x1F
        process = (snowflake >> 12) & 0x1F
        increment = snowflake & 0xFFF
        ctx.ok(f"Créé le {created:%Y-%m-%d %H:%M:%S} UTC")

        table = Table(title=f"Snowflake {snowflake}", show_header=False, expand=True)
        table.add_column(style="bold cyan")
        table.add_column()
        table.add_row("Créé le (UTC)", created.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])
        table.add_row("Worker ID", str(worker))
        table.add_row("Process ID", str(process))
        table.add_row("Incrément", str(increment))
        return ToolResult(
            renderable=table,
            data={
                "id": snowflake,
                "created_utc": created.isoformat(),
                "worker": worker,
                "process": process,
                "increment": increment,
            },
        )
