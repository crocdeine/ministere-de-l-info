"""Lance Chrome sans fenêtre (headless) sur le banc, attend la fin, relève la mémoire, ferme.

Usage : python3 banc_chrome.py STRATEGIE [FONDU 0|1] [ETIQUETTE]
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

MESURES = Path(os.environ.get("BANC_MESURES", "mesures.jsonl"))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROFIL = Path("/Volumes/le gros stockage/outils/tmp/poc-a0/chrome-profil")

strategie = sys.argv[1]
fondu = sys.argv[2] if len(sys.argv) > 2 else "0"
etiquette = sys.argv[3] if len(sys.argv) > 3 else f"chromium-{strategie}-f{fondu}"
url = (
    f"http://127.0.0.1:4173/?banc=1&strategie={strategie}&fondu={fondu}"
    f"&etiquette={etiquette}&rapport=http://127.0.0.1:8765/"
)
shutil.rmtree(PROFIL, ignore_errors=True)  # profil neuf : cache HTTP vide (à froid)
n0 = len(MESURES.read_text().splitlines()) if MESURES.exists() else 0
t0 = time.time() * 1000
p = subprocess.Popen(
    [
        CHROME,
        "--headless=new",
        f"--user-data-dir={PROFIL}",
        "--window-size=1280,860",
        "--no-first-run",
        "--no-default-browser-check",
        "--enable-precise-memory-info",
        url,
    ],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
fin = None
for _ in range(600):
    time.sleep(0.5)
    lignes = MESURES.read_text().splitlines()[n0:] if MESURES.exists() else []
    if any('"fin"' in ligne for ligne in lignes):
        fin = lignes
        break
# Mémoire : RSS cumulée des processus Chrome de ce profil (Ko → Mo).
ps = subprocess.run(["ps", "-axo", "rss=,command="], capture_output=True, text=True).stdout
rss = sum(int(ligne.split()[0]) for ligne in ps.splitlines() if str(PROFIL) in ligne) / 1024
p.terminate()
try:
    p.wait(10)
except subprocess.TimeoutExpired:
    p.kill()
with MESURES.open("a") as f:
    f.write(
        json.dumps(
            {
                "corps": {
                    "mesure": "lancement",
                    "etiquette": etiquette,
                    "t0": t0,
                    "rssMo": rss,
                    "termine": fin is not None,
                }
            }
        )
        + "\n"
    )
print(etiquette, "terminé" if fin else "DÉLAI DÉPASSÉ", f"RSS {rss:.0f} Mo")
