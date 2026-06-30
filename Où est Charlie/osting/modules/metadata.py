"""Extraction des métadonnées EXIF d'une image (dont la géolocalisation GPS)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS
from rich.table import Table

from ..core import console


def _gps_to_decimal(coord, ref) -> float:
    degrees, minutes, seconds = (float(x) for x in coord)
    decimal = degrees + minutes / 60 + seconds / 3600
    if ref in ("S", "W"):
        decimal = -decimal
    return round(decimal, 6)


def _parse_gps(gps_info: dict) -> dict:
    gps = {GPSTAGS.get(k, k): v for k, v in gps_info.items()}
    result: dict = {}
    if "GPSLatitude" in gps and "GPSLongitude" in gps:
        lat = _gps_to_decimal(gps["GPSLatitude"], gps.get("GPSLatitudeRef", "N"))
        lon = _gps_to_decimal(gps["GPSLongitude"], gps.get("GPSLongitudeRef", "E"))
        result["latitude"] = lat
        result["longitude"] = lon
        result["google_maps"] = f"https://maps.google.com/?q={lat},{lon}"
    if "GPSAltitude" in gps:
        result["altitude"] = float(gps["GPSAltitude"])
    return result


def run(image_path: str) -> dict:
    path = Path(image_path)
    if not path.exists():
        console.print(f"[red]Fichier introuvable :[/red] {image_path}")
        return {}

    console.print(f"\n[bold]Métadonnées EXIF[/bold] : [cyan]{path.name}[/cyan]\n")

    try:
        img = Image.open(path)
        exif = img._getexif()
    except Exception as exc:
        console.print(f"[red]Lecture impossible :[/red] {type(exc).__name__}")
        return {}

    if not exif:
        console.print("[yellow]Aucune métadonnée EXIF (souvent retirée par les réseaux sociaux).[/yellow]")
        return {"exif": {}, "gps": {}}

    tags: dict = {}
    gps: dict = {}
    for tag_id, value in exif.items():
        tag = TAGS.get(tag_id, tag_id)
        if tag == "GPSInfo":
            gps = _parse_gps(value)
        else:
            tags[tag] = value

    interesting = ["Make", "Model", "Software", "DateTime", "DateTimeOriginal",
                   "Artist", "Copyright", "LensModel", "ImageWidth", "ImageLength"]
    table = Table(title="EXIF", show_header=False, box=None)
    table.add_column(style="bold")
    table.add_column(overflow="fold")
    for key in interesting:
        if key in tags:
            table.add_row(key, str(tags[key]))
    console.print(table)

    if gps:
        gps_table = Table(title="[red]Géolocalisation GPS[/red]", show_header=False, box=None)
        gps_table.add_column(style="bold")
        gps_table.add_column(overflow="fold")
        for key, value in gps.items():
            gps_table.add_row(key, str(value))
        console.print(gps_table)
    else:
        console.print("[dim]Pas de coordonnées GPS dans l'image.[/dim]")

    return {"exif": {k: str(v) for k, v in tags.items()}, "gps": gps}
