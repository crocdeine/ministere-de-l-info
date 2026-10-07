"""Résumé des mesures (médiane, p90, max) par lancement."""

import json
import os
import statistics as st
from pathlib import Path

lignes = [
    json.loads(x)
    for x in Path(os.environ.get("BANC_MESURES", "mesures.jsonl")).read_text().splitlines()
]
bloc: list[dict] = []
for ligne in lignes:
    c = ligne["corps"]
    if c.get("mesure") == "lancement":
        ouv = next((b for b in bloc if b["corps"].get("mesure") == "ouverture"), None)
        ch = next((b for b in bloc if b["corps"].get("mesure") == "changements"), None)
        print(
            f"== {c['etiquette']}  RSS {c['rssMo']:.0f} Mo  {'' if c['termine'] else 'NON TERMINÉ'}"
        )
        if ouv:
            o = ouv["corps"]
            res = o.get("ressources", [])
            pm = sum(r[3] for r in res if r[0] == "communes.pmtiles")
            js = sum(r[3] for r in res if str(r[0]).endswith(".js"))
            print(
                f"   ouverture → carte colorée : {o['epoch'] - c['t0']:.0f} ms ; depuis document {o['depuisNavigation'] - (o.get('docFin') or 0):.0f} ms ; pmtiles {pm / 1e3:.0f} Ko ({sum(1 for r in res if r[0] == 'communes.pmtiles')} req.) ; JS {js / 1e3:.0f} Ko"
            )
        if ch:
            for cle in ("premiereImage", "idle"):
                v = ch["corps"][cle]
                q = sorted(v)
                print(
                    f"   {cle:13s} n={len(v)} 20 premiers méd {st.median(v[:20]):.0f} | 50 : méd {st.median(v):.0f} p90 {q[int(0.9 * len(q)) - 1]:.0f} max {max(v):.0f} min {min(v):.0f} ms"
                )
            print(f"   tas JS : {ch['corps']['tasJsMo']}")
            for d in ch["corps"]["details"]:
                print(
                    f"   détail {d['format']:4s} {d['octets'] / 1e3:.0f} Ko lecture {d['msLecture']:.1f} ms décodage {d['msDecodage']:.1f} ms"
                )
        bloc = []
    else:
        bloc.append(ligne)
