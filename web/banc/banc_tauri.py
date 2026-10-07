"""Lance l'app Tauri de mesure (en arrière-plan, sans prendre le focus), attend la fin du banc,
relève l'empreinte mémoire (footprint) des processus de l'app, puis la ferme.

Usage : python3 banc_tauri.py [NOMBRE_DE_LANCEMENTS]
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

MESURES = Path(os.environ.get("BANC_MESURES", "mesures.jsonl"))
APP = Path(__file__).resolve().parent.parent / "src-tauri/target/release/bundle/macos/Banc A0.app"


def pids_webkit() -> set[int]:
    sortie = subprocess.run(["pgrep", "-f", "com.apple.WebKit"], capture_output=True, text=True)
    return {int(x) for x in sortie.stdout.split()}


def empreinte(pid: int) -> float | None:
    """Empreinte physique (Mo) d'un processus selon `footprint`."""
    s = subprocess.run(["footprint", str(pid)], capture_output=True, text=True).stdout
    m = re.search(r"Footprint:\s*([\d.]+)\s*(KB|MB|GB)", s)
    if not m:
        return None
    return float(m.group(1)) * {"KB": 1 / 1024, "MB": 1, "GB": 1024}[m.group(2)]


def lancer() -> None:
    avant = pids_webkit()
    n0 = len(MESURES.read_text().splitlines()) if MESURES.exists() else 0
    t0 = time.time() * 1000
    subprocess.run(["open", "-n", str(APP)], check=True)
    lignes: list[str] = []
    for _ in range(240):
        time.sleep(0.5)
        lignes = MESURES.read_text().splitlines()[n0:] if MESURES.exists() else []
        if any('"fin"' in x for x in lignes):
            break
    app = subprocess.run(["pgrep", "-f", f"{APP}/Contents/MacOS"], capture_output=True, text=True)
    pids_app = [int(x) for x in app.stdout.split()]
    nouveaux = sorted(pids_webkit() - avant)
    memoire = {f"app:{p}": empreinte(p) for p in pids_app}
    for p in nouveaux:
        nom = subprocess.run(["ps", "-o", "comm=", "-p", str(p)], capture_output=True, text=True)
        memoire[f"{nom.stdout.strip().split('.')[-1]}:{p}"] = empreinte(p)
    for p in pids_app:
        subprocess.run(["kill", str(p)])
    etiquette = next(
        (json.loads(x)["corps"]["params"]["etiquette"] for x in lignes if '"changements"' in x),
        "tauri-inconnu",
    )
    total = sum(v for v in memoire.values() if v)
    with MESURES.open("a") as f:
        f.write(
            json.dumps(
                {
                    "corps": {
                        "mesure": "lancement",
                        "etiquette": etiquette,
                        "t0": t0,
                        "rssMo": total,
                        "memoire": memoire,
                        "termine": any('"fin"' in x for x in lignes),
                    }
                }
            )
            + "\n"
        )
    print(etiquette, f"empreinte {total:.0f} Mo", {k: round(v or 0) for k, v in memoire.items()})
    time.sleep(2)


for _ in range(int(sys.argv[1]) if len(sys.argv) > 1 else 1):
    lancer()
