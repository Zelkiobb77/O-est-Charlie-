"""NETWORK — scanner de ports TCP RÉEL et asynchrone (asyncio).

Établit de vraies connexions TCP via ``asyncio.open_connection`` (non bloquant),
en loguant chaque port testé dans la live console.

⚠ Légal : ne scannez que des systèmes que vous êtes autorisé à tester
(votre propre machine, scanme.nmap.org, un périmètre de pentest validé).
"""

from __future__ import annotations

import asyncio

from rich.table import Table

from core.base import ToolModule, ToolResult

_PORTS = {
    21: "FTP", 22: "SSH", 25: "SMTP", 53: "DNS", 80: "HTTP", 110: "POP3",
    143: "IMAP", 443: "HTTPS", 445: "SMB", 3306: "MySQL", 3389: "RDP",
    5432: "PostgreSQL", 6379: "Redis", 8080: "HTTP-alt", 8443: "HTTPS-alt",
}


async def _probe(host: str, port: int, timeout: float = 1.0) -> str:
    """Tente une connexion TCP. Retourne 'open' / 'closed' / 'filtered'."""
    try:
        future = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(future, timeout=timeout)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return "open"
    except asyncio.TimeoutError:
        return "filtered"
    except (ConnectionRefusedError, OSError):
        return "closed"


class PortScanner(ToolModule):
    name = "Port Scanner"
    category = "NETWORK"
    icon = "🛰"
    author = "Zelkiobb"
    description = (
        "Scan TCP réel (asyncio) des ports courants d'une cible AUTORISÉE. "
        "Chaque sonde est loguée en direct ; l'UI reste 100% fluide."
    )
    input_label = "Hôte cible (autorisé)"
    input_placeholder = "ex: 127.0.0.1 / scanme.nmap.org"

    async def run(self, ctx) -> ToolResult:
        host = (ctx.value or "").strip()
        if not host:
            ctx.err("Aucune cible fournie")
            return ToolResult(renderable="[red]Saisis un hôte à scanner.[/red]")

        ctx.set_total(len(_PORTS))  # ← pilote la ProgressBar
        ctx.info(f"Scan TCP concurrent de {host} · {len(_PORTS)} ports")

        async def probe(port: int, service: str):
            ctx.step(f"Sonde {host}:{port} ({service})…")
            return port, service, await _probe(host, port)

        # Toutes les sondes en parallèle ; on logue chaque hit dès qu'il tombe.
        tasks = [asyncio.create_task(probe(p, s)) for p, s in _PORTS.items()]
        results: dict[int, tuple[str, str]] = {}
        open_ports = []
        interrupted = False
        try:
            for coro in asyncio.as_completed(tasks):
                port, service, state = await coro
                ctx.advance()  # ← +1 sur la barre à chaque port franchi
                results[port] = (service, state)
                if state == "open":
                    ctx.ok(f"Port {port}/{service} OUVERT")
                    open_ports.append(port)
                if ctx.cancelled:  # ← annulation coopérative (Ctrl+X)
                    interrupted = True
                    ctx.warn("Annulation détectée — arrêt du scan")
                    break
        except asyncio.CancelledError:  # ← annulation dure (Task.cancel)
            interrupted = True
            ctx.warn("Scan interrompu (annulation de la tâche)")
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except asyncio.CancelledError:
                pass

        if interrupted:
            done = sorted(open_ports)
            ctx.warn(f"Scan interrompu · {len(done)} port(s) ouvert(s) avant arrêt")
            return ToolResult(
                renderable=(
                    "[#f3c969][!] Scan interrompu par l'utilisateur.[/]\n"
                    f"[#7a7a8c]Ports ouverts détectés avant l'arrêt : "
                    f"{', '.join(map(str, done)) or '—'}[/]"
                ),
                data={"host": host, "cancelled": True, "open_ports": done},
            )

        table = Table(title=f"Scan TCP — {host}", expand=True)
        table.add_column("Port", justify="right", style="bold")
        table.add_column("Service")
        table.add_column("État", justify="center")
        for port in sorted(results):
            service, state = results[port]
            badge = {
                "open": "[#36e07f]● open[/]",
                "filtered": "[#f3c969]◌ filtered[/]",
                "closed": "[#6f7b8c]○ closed[/]",
            }[state]
            table.add_row(str(port), service, badge)

        open_ports.sort()
        ctx.ok(f"Scan terminé · {len(open_ports)}/{len(_PORTS)} port(s) ouvert(s)")
        return ToolResult(
            renderable=table,
            data={"host": host, "open_ports": open_ports, "scanned": list(_PORTS)},
        )
