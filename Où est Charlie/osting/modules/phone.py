"""Analyse d'un numéro de téléphone (métadonnées publiques, hors-ligne)."""

from __future__ import annotations

import phonenumbers
from phonenumbers import PhoneNumberType, carrier, geocoder, timezone
from rich.table import Table

from ..core import console

# phonenumbers expose les types comme des entiers ; on les rend lisibles.
_TYPE_NAMES = {
    PhoneNumberType.FIXED_LINE: "ligne fixe",
    PhoneNumberType.MOBILE: "mobile",
    PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixe ou mobile",
    PhoneNumberType.TOLL_FREE: "numéro vert",
    PhoneNumberType.PREMIUM_RATE: "surtaxé",
    PhoneNumberType.SHARED_COST: "coût partagé",
    PhoneNumberType.VOIP: "VoIP",
    PhoneNumberType.PERSONAL_NUMBER: "numéro personnel",
    PhoneNumberType.PAGER: "pager",
    PhoneNumberType.UAN: "UAN",
    PhoneNumberType.VOICEMAIL: "messagerie vocale",
    PhoneNumberType.UNKNOWN: "inconnu",
}


def run(number: str, region: str | None = None) -> dict:
    console.print(f"\n[bold]Analyse du numéro[/bold] : [cyan]{number}[/cyan]\n")

    try:
        parsed = phonenumbers.parse(number, region)
    except phonenumbers.NumberParseException as exc:
        console.print(f"[red]Numéro illisible :[/red] {exc}")
        console.print("[dim]Astuce : format international (+33…) ou précise --region FR.[/dim]")
        return {}

    valid = phonenumbers.is_valid_number(parsed)
    possible = phonenumbers.is_possible_number(parsed)

    info = {
        "valide": valid,
        "possible": possible,
        "pays": geocoder.description_for_number(parsed, "fr") or "—",
        "opérateur": carrier.name_for_number(parsed, "fr") or "—",
        "fuseaux": ", ".join(timezone.time_zones_for_number(parsed)) or "—",
        "indicatif_pays": f"+{parsed.country_code}",
        "type": _TYPE_NAMES.get(phonenumbers.number_type(parsed), "inconnu"),
        "format_international": phonenumbers.format_number(
            parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
        ),
        "format_e164": phonenumbers.format_number(
            parsed, phonenumbers.PhoneNumberFormat.E164
        ),
    }

    table = Table(show_header=False, box=None)
    table.add_column(style="bold")
    table.add_column(overflow="fold")
    table.add_row("Valide", "[green]oui[/green]" if valid else "[red]non[/red]")
    for key, value in info.items():
        if key == "valide":
            continue
        table.add_row(key.replace("_", " "), str(value))
    console.print(table)

    return info
