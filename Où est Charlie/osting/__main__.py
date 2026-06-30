"""Point d'entrée CLI d'OSTING.

Exemples :
    python -m osting username john_doe
    python -m osting email john@example.com
    python -m osting domain example.com
    python -m osting exif photo.jpg
    python -m osting dorks "John Doe"
    python -m osting phone +33612345678
    python -m osting full john_doe          # enchaîne plusieurs modules
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings

# Warning cosmétique quand urllib3/chardet ne matchent pas la version de requests.
warnings.filterwarnings("ignore", module="requests")

from .core import animated_banner, console, ensure_consent, show_banner
from .menu import run_menu
from .modules import dorks, domain, email_intel, metadata, phone, username


def _build_parser() -> argparse.ArgumentParser:
    # Options communes acceptées avant OU après la sous-commande.
    # SUPPRESS évite que les sous-parsers écrasent la valeur du parser principal.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                        help="sortie JSON brute (en plus de l'affichage)")
    common.add_argument("--yes", action="store_true", default=argparse.SUPPRESS,
                        help="accepte l'avertissement légal sans prompt")

    parser = argparse.ArgumentParser(
        prog="osting",
        parents=[common],
        description="OSTING — multitool OSINT à partir de sources publiques (usage légal).",
    )
    parser.set_defaults(json=False, yes=False)

    # Pas de sous-commande => menu interactif coloré.
    sub = parser.add_subparsers(dest="command", required=False)

    sub.add_parser("menu", parents=[common], help="menu interactif coloré (défaut si aucune commande)")

    p = sub.add_parser("username", parents=[common], help="cherche un pseudo sur de nombreuses plateformes")
    p.add_argument("value")

    p = sub.add_parser("email", parents=[common], help="reconnaissance autour d'une adresse e-mail")
    p.add_argument("value")

    p = sub.add_parser("domain", parents=[common], help="WHOIS, DNS et sous-domaines d'un domaine")
    p.add_argument("value")

    p = sub.add_parser("exif", parents=[common], help="métadonnées EXIF/GPS d'une image")
    p.add_argument("value")

    p = sub.add_parser("dorks", parents=[common], help="génère des dorks de moteur de recherche")
    p.add_argument("value")
    p.add_argument("--engine", default="Google", choices=["Google", "Bing", "DuckDuckGo"])

    p = sub.add_parser("phone", parents=[common], help="métadonnées d'un numéro de téléphone")
    p.add_argument("value")
    p.add_argument("--region", default=None, help="code pays par défaut (ex: FR) si non international")

    p = sub.add_parser("full", parents=[common], help="enchaîne username + email + dorks sur une cible")
    p.add_argument("value")

    p = sub.add_parser("banner", parents=[common], help="bannière arc-en-ciel qui défile sans fin (Ctrl+C pour quitter)")
    p.add_argument("--text", default=None, help="texte personnalisé à faire défiler")

    return parser


def _dispatch(args) -> object:
    if args.command == "username":
        return username.run(args.value)
    if args.command == "email":
        return email_intel.run(args.value)
    if args.command == "domain":
        return domain.run(args.value)
    if args.command == "exif":
        return metadata.run(args.value)
    if args.command == "dorks":
        return dorks.run(args.value, engine=args.engine)
    if args.command == "phone":
        return phone.run(args.value, region=args.region)
    if args.command == "full":
        out = {}
        out["username"] = username.run(args.value)
        if "@" in args.value:
            out["email"] = email_intel.run(args.value)
        out["dorks"] = dorks.run(args.value)
        return out
    if args.command == "banner":
        kwargs = {"duration": None}
        if args.text:
            kwargs["text"] = args.text
        animated_banner(**kwargs)
        return None
    if args.command == "menu":
        run_menu()
        return None
    return None


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Aucune sous-commande => menu interactif par défaut.
    if args.command is None:
        args.command = "menu"

    # `banner` et `menu` gèrent eux-mêmes leur affichage / consentement.
    if args.command not in ("banner", "menu"):
        show_banner()
        if not ensure_consent(assume_yes=args.yes):
            return 1

    try:
        result = _dispatch(args)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrompu.[/yellow]")
        return 130

    if args.json:
        console.print_json(json.dumps(result, default=str, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
