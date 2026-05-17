"""Smoke tests runtime pour fetch_admin_express — pagination et reprise disque."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ministere_de_l_info.data_sources.geo import _batch_file_valid, fetch_admin_express

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def test_departement_download() -> None:
    """Premier appel force=True — vérifie pagination et contenu."""
    log.info("=== Test 1 : téléchargement départements (force=True) ===")
    paths = list(fetch_admin_express("departement", dom=True, force=True))

    assert len(paths) >= 1, f"Aucun batch yieldé, obtenu : {paths}"
    log.info("Batches yieldés : %d", len(paths))

    total_features = 0
    for p in paths:
        assert p.exists(), f"Fichier batch manquant : {p}"
        assert _batch_file_valid(p), f"Batch invalide : {p}"
        data = json.loads(p.read_text(encoding="utf-8"))
        n = len(data["features"])
        log.info("  %s → %d features", p.name, n)
        total_features += n

    assert 96 <= total_features <= 110, (
        f"Nombre de départements inattendu : {total_features} (attendu 96-110)"
    )
    log.info("Total features : %d ✓", total_features)


def test_departement_reprise() -> None:
    """Second appel force=False — vérifie que les batches sont lus depuis le disque."""
    log.info("=== Test 2 : reprise disque (force=False) ===")

    # Capture les logs pour détecter "reprise disque"
    reprise_detectee = False

    class RepriseHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            nonlocal reprise_detectee
            if "reprise disque" in record.getMessage():
                reprise_detectee = True

    handler = RepriseHandler()
    logging.getLogger("ministere_de_l_info.data_sources.geo").addHandler(handler)

    paths = list(fetch_admin_express("departement", dom=True, force=False))

    logging.getLogger("ministere_de_l_info.data_sources.geo").removeHandler(handler)

    assert len(paths) >= 1, "Aucun batch retourné en mode reprise"
    assert reprise_detectee, (
        "Aucun log 'reprise disque' détecté — le cache disque n'a pas été utilisé"
    )
    log.info("Reprise disque confirmée sur %d batch(es) ✓", len(paths))


if __name__ == "__main__":
    test_departement_download()
    test_departement_reprise()
    log.info("=== Tous les smoke tests passent ✓ ===")
