# OSTING SUITE

Suite d'outils de reconnaissance / red-team avec une **interface TUI** (Textual)
professionnelle, modulaire et **navigable au clavier**. Architecture *drop-in* :
déposez un script dans `modules/`, il apparaît automatiquement dans l'interface.

> [!WARNING]
> **Usage légitime uniquement** : audit de sa propre exposition, engagements
> autorisés (pentest / bug bounty avec périmètre écrit), apprentissage, CTF.
> L'agrégation de données publiques peut devenir illégale selon l'intention et la
> juridiction. Vous êtes seul responsable de votre usage.

## Aperçu de l'interface

```
┌────────────────────────────────────────────────────────────────────────┐
│ VOID//OSTING SUITE · red-team toolkit v1.0          ⏱ 14:03:11  28/06   │  header live
├──────────────────┬─────────────────────────────────────────────────────┤
│ CATÉGORIES       │ OUTILS                                               │
│ 🛰  OSINT (2)     │ ❄  Snowflake Decoder                                 │
│ 🌐  NETWORK (2)   │ 🪝  Webhook Inspector                                │
│ 💬  DISCORD (2)   ├─────────────────────────────────────────────────────┤
│ 🕸  WEB (2)       │ DÉTAIL / EXÉCUTION                                   │
│                  │ [ champ de saisie ]  [ ▶ Exécuter ]                  │
│                  │ > résultat formaté (tables rich)…                    │
├──────────────────┴─────────────────────────────────────────────────────┤
│ ^q Quitter   esc Sidebar   ^r Exécuter   ↑↓ Naviguer   ⏎ Valider        │  footer
└────────────────────────────────────────────────────────────────────────┘
```

## Installation & lancement

```bash
pip install -r requirements.txt
python dashboard.py
```

(Python 3.10+. Pour le rendu, un terminal moderne est recommandé —
**Windows Terminal** plutôt que le vieux `cmd.exe`.)

## Navigation (100% clavier)

| Touche            | Action                                              |
|-------------------|-----------------------------------------------------|
| `↑` / `↓`         | Naviguer dans la sidebar / la liste d'outils        |
| `Entrée`          | Valider (catégorie → outils, outil → saisie/exéc.)  |
| `Ctrl+R`          | Exécuter l'outil sélectionné                        |
| `Échap`           | Revenir à la sidebar                                |
| `Tab` / `Shift+Tab` | Changer de zone                                   |
| `Ctrl+Q`          | Quitter                                             |

## Architecture

```
dashboard.py          # Lanceur : l'app Textual (layout, navigation, exécution)
core/
├── base.py           # Contrat ToolModule (ce qu'un outil doit exposer)
├── loader.py         # Auto-découverte des modules de modules/
└── widgets.py        # Header live, items de listes, rendu du détail
modules/              # ← DROP-IN : un fichier = un ou plusieurs outils
styles/dashboard.tcss # Thème néon (CSS Textual)
```

Le dashboard ne connaît **aucun** outil en dur : il interroge `core.loader`,
qui scanne `modules/`, instancie chaque classe héritant de `ToolModule`, et les
regroupe par `category`. Sidebar et listes se construisent à partir de ça.

## Ajouter un outil (drag & drop)

Créez `modules/mon_outil.py` :

```python
from rich.table import Table
from core.base import ToolModule

class MonScanner(ToolModule):
    name = "Mon Scanner"
    category = "NETWORK"          # crée/rejoint l'entrée de sidebar
    icon = "📡"
    description = "Ce que fait l'outil."
    input_label = "Cible"        # optionnel : affiche un champ de saisie
    input_placeholder = "ex: 10.0.0.1"

    def run(self, value=None):
        table = Table(title=f"Scan de {value}")
        table.add_column("Port"); table.add_column("État")
        table.add_row("22", "[green]open[/]")
        return table                # renvoie un renderable rich (Table/Text/Panel)
```

Relancez `python dashboard.py` : l'outil est là. Aucun autre fichier à modifier.

### Bonnes pratiques pour les outils lourds

`run()` est synchrone : pour une opération longue (scan réseau, requêtes HTTP),
lancez-la dans un *worker* Textual (`@work`) pour ne pas geler l'UI, et renvoyez
un résultat partiel/progressif. Les modules livrés en démo (scan, headers, DNS)
indiquent en commentaire où brancher la logique réelle.

## Modules fournis

| Catégorie | Outil               | État          |
|-----------|---------------------|---------------|
| OSINT     | Username Finder     | démo          |
| OSINT     | Email Intel         | démo          |
| NETWORK   | Port Scanner        | démo          |
| NETWORK   | DNS Recon           | démo          |
| DISCORD   | Snowflake Decoder   | **fonctionnel** |
| DISCORD   | Webhook Inspector   | **fonctionnel** |
| WEB       | HTTP Header Audit   | démo          |
| WEB       | Dork Generator      | **fonctionnel** |

## Licence

MIT — voir [LICENSE](LICENSE).
