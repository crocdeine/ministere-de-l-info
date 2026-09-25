"""Référentiel groupe parlementaire × période → bloc politique (ADR-0011).

Clé : ``(chambre, groupe, legislature)``. Chaque entrée couvre un intervalle fermé
``[legislature_debut, legislature_fin]`` :

- **AN** : numéros de législature (12 = 2002-2007 … 17 = 2024-). Les intervalles sont
  toujours bornés : un groupe observé dans une législature non couverte (ex. XVIIIe)
  n'est pas classé et déclenche un WARNING, ce qui force une revue du classement
  selon la grille en vigueur à l'élection de cette législature.
- **SENAT** : le Sénat n'a pas de législature et la source (ODSEN_GENERAL) ne donne
  que le groupe actuel ou le dernier groupe, sans date. Les bornes sont ``None``
  (toutes périodes) ; seule une source datée des appartenances permettrait un
  classement par renouvellement (voir ADR-0011, limites).

Règle de classement (ADR-0005 n° 3, décision Mathias 2026-09-24, doctrine de l'ADR-0010) :
bloc de la nuance du parti dominant du groupe, selon (1) la grille officielle couvrant
l'élection de la législature ; (2) sinon la grille la plus proche dans le temps, de
préférence antérieure, si le code désigne la même famille ; (3) sinon le classement
reconstruit. Grilles retenues : XIIe-XVe → INTA1931378J (2020) par l'étape 2 ;
XVIe (2022) → INTA1931378J ; XVIIe (2024) → IOMA2322276J (2023). Groupes composites
sans parti dominant : DIV. Non-inscrits : DIV, exceptions par ``leg_blocs_override``.

Un groupe absent du référentiel n'est **pas** classé DIV : bloc NULL (« non classé »)
et WARNING au chargement.
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

import duckdb

logger = logging.getLogger(__name__)

BLOCS_VALIDES: frozenset[str] = frozenset({"EXG", "GAU", "DIV", "CENT", "DTE", "EXD"})
CHAMBRES: frozenset[str] = frozenset({"AN", "SENAT"})
LEGISLATURE_MAX_COUVERTE = 17

# Grilles officielles citées (docs/sources-officielles/nuances/)
_G2020 = "INTA1931378J (2020) annexe 3 p. 10"
_G2023 = "IOMA2322276J (2023) annexes 1-2 p. 6-7"
_G2026 = "INTP2602966C (2026) annexe 3 p. 11"
# Doctrine ADR-0010 : (1) grille couvrant le scrutin ; (2) sinon grille la plus proche,
# de préférence antérieure, si le code désigne la même famille ; (3) sinon reconstruction.
_PROCHE = "doctrine ADR-0010 (2) : pas de grille pour le scrutin, grille la plus proche"
_RECONS = "doctrine ADR-0010 (3) : pas de code équivalent dans les grilles, classement "
_RECONS += "reconstruit (ADR-0005 n° 4)"


@dataclass(frozen=True)
class CorrespondanceGroupe:
    """Une ligne du référentiel leg_groupes_blocs."""

    chambre: str
    groupe: str
    legislature_debut: int | None
    legislature_fin: int | None
    bloc: str
    libelle: str
    source_bloc: str

    def couvre(self, legislature: int | None) -> bool:
        """Vrai si la période ``legislature`` est dans l'intervalle de l'entrée."""
        if self.legislature_debut is None and self.legislature_fin is None:
            return True
        if legislature is None:
            return False
        if self.legislature_debut is not None and legislature < self.legislature_debut:
            return False
        return not (self.legislature_fin is not None and legislature > self.legislature_fin)


def _an(
    groupe: str, debut: int, fin: int, bloc: str, libelle: str, source: str
) -> CorrespondanceGroupe:
    return CorrespondanceGroupe("AN", groupe, debut, fin, bloc, libelle, source)


def _senat(groupe: str, bloc: str, libelle: str, source: str) -> CorrespondanceGroupe:
    return CorrespondanceGroupe("SENAT", groupe, None, None, bloc, libelle, source)


# ---------------------------------------------------------------------------
# Assemblée nationale — sigles Datan (colonne groupeAbrev), législatures 12 à 17
# ---------------------------------------------------------------------------

_AN: tuple[CorrespondanceGroupe, ...] = (
    # --- Gauche -----------------------------------------------------------
    _an(
        "SOC",
        12,
        17,
        "GAU",
        "Socialiste / Socialistes et apparentés",
        f"PS = SOC → GAU : {_G2020}, {_G2023}, {_G2026} ; 12-15 : {_PROCHE}",
    ),
    _an(
        "SOC-A", 12, 17, "GAU", "Socialistes et apparentés", f"PS = SOC → GAU : {_G2020}, {_G2023}"
    ),
    _an(
        "SRC",
        13,
        14,
        "GAU",
        "Socialiste, radical, citoyen et divers gauche",
        f"PS dominant = SOC → GAU : {_G2020} ; {_PROCHE}",
    ),
    _an(
        "S.R.C.",
        13,
        14,
        "GAU",
        "Socialiste, radical, citoyen et divers gauche",
        f"Variante de sigle SRC ; PS dominant = SOC → GAU : {_G2020} ; {_PROCHE}",
    ),
    _an(
        "SER",
        14,
        14,
        "GAU",
        "Socialiste, écologiste et républicain",
        f"PS dominant = SOC → GAU : {_G2020} ; {_PROCHE}",
    ),
    _an(
        "NG",
        15,
        15,
        "GAU",
        "Nouvelle Gauche",
        f"PS dominant = SOC → GAU : {_G2020} ; {_PROCHE}",
    ),
    _an(
        "CR",
        12,
        12,
        "GAU",
        "Député·e·s communistes et républicains",
        f"PCF = COM → GAU : {_G2020} ; {_PROCHE}",
    ),
    _an(
        "GDR",
        13,
        17,
        "GAU",
        "Gauche démocrate et républicaine",
        f"PCF dominant = COM → GAU : {_G2020}, {_G2023}",
    ),
    _an(
        "GDR-NUPES",
        16,
        16,
        "GAU",
        "Gauche démocrate et républicaine - NUPES",
        f"PCF dominant = COM → GAU : {_G2020} (grille retenue pour la XVIe, ADR-0010)",
    ),
    _an("ECOLO", 14, 16, "GAU", "Écologiste", f"EELV = VEC → GAU : {_G2020}, {_G2023}"),
    _an(
        "ECOS",
        17,
        17,
        "GAU",
        "Écologiste et social",
        f"Les Écologistes = VEC → GAU : {_G2023} (grille retenue pour la XVIIe, ADR-0010)",
    ),
    _an(
        "RRDP",
        14,
        14,
        "GAU",
        "Radical, républicain, démocrate et progressiste",
        f"PRG = RDG → GAU : {_G2020}, {_G2023}, {_G2026} ; décision Mathias 2026-09-24 (Q20)",
    ),
    _an(
        "FI",
        15,
        15,
        "GAU",
        "La France insoumise",
        f"FI → GAU : {_G2020} ({_PROCHE}) ; ADR-0005 (FI 2017 = GAU) ; décision Mathias "
        "2026-09-24 (Q18)",
    ),
    _an(
        "LFI-NUPES",
        16,
        16,
        "GAU",
        "La France insoumise - NUPES",
        f"FI → GAU : {_G2020} (grille retenue pour la XVIe, ADR-0010), {_G2023} ; "
        "décision Mathias 2026-09-24 (Q18)",
    ),
    _an(
        "LFI-NFP",
        17,
        17,
        "GAU",
        "La France insoumise - Nouveau Front populaire",
        f"FI → GAU : {_G2023}, grille retenue pour la XVIIe élue en 2024 (ADR-0010) ; "
        "décision Mathias "
        f"2026-09-24 (Q19). {_G2026} classe LFI en EXG pour les scrutins postérieurs au "
        "2 fév. 2026 (non rétroactif, ADR-0005 n° 3)",
    ),
    # --- Divers -----------------------------------------------------------
    _an(
        "NI",
        12,
        17,
        "DIV",
        "Non inscrits",
        "Aucun groupe, pas de nuance commune ; exceptions dans leg_blocs_override",
    ),
    _an(
        "LT", 15, 15, "DIV", "Libertés et territoires", "Groupe composite sans parti dominant → DIV"
    ),
    _an(
        "LIOT",
        16,
        17,
        "DIV",
        "Libertés, indépendants, outre-mer et territoires",
        "Groupe composite sans parti dominant → DIV",
    ),
    # --- Centre -----------------------------------------------------------
    _an(
        "UDF",
        12,
        12,
        "CENT",
        "Union pour la démocratie française",
        f"UDF → CENT (cohérent législatives 2002) ; {_RECONS}",
    ),
    _an(
        "NC",
        13,
        14,
        "CENT",
        "Nouveau Centre",
        f"NCE → CENT (cohérent législatives 2012) ; {_RECONS}",
    ),
    _an(
        "UDI",
        14,
        14,
        "CENT",
        "Union des démocrates et indépendants",
        f"UDI → CENT : {_G2020} ; {_PROCHE}",
    ),
    _an(
        "LC",
        15,
        15,
        "CENT",
        "Les Constructifs (UDI + LR constructifs)",
        f"UDI et AGR → CENT : {_G2020}",
    ),
    _an("UDI-AGIR", 15, 15, "CENT", "UDI, Agir et indépendants", f"UDI et AGR → CENT : {_G2020}"),
    _an("UDI_I", 15, 15, "CENT", "UDI et indépendants", f"UDI → CENT : {_G2020}"),
    _an("AGIR-E", 15, 15, "CENT", "Agir ensemble", f"AGR → CENT : {_G2020}"),
    _an("LAREM", 15, 15, "CENT", "La République en marche", f"REM → CENT : {_G2020}"),
    _an("MODEM", 15, 15, "CENT", "Mouvement démocrate et apparentés", f"MDM → CENT : {_G2020}"),
    _an(
        "DEM",
        15,
        17,
        "CENT",
        "Démocrate (MoDem et indépendants)",
        f"MDM → CENT : {_G2020}, {_G2023}",
    ),
    _an("RE", 16, 16, "CENT", "Renaissance", f"REM/REN → CENT : {_G2020}, {_G2023}"),
    _an(
        "HOR",
        16,
        17,
        "CENT",
        "Horizons et apparentés",
        f"HOR → Centre : {_G2023}, {_G2026} (absent de {_G2020} : {_PROCHE})",
    ),
    _an("EPR", 17, 17, "CENT", "Ensemble pour la République", f"REN → Centre : {_G2023}"),
    # --- Droite -----------------------------------------------------------
    _an(
        "UMP",
        12,
        14,
        "DTE",
        "Union pour un mouvement populaire",
        f"UMP → LR = DTE : {_G2020} ; {_PROCHE}",
    ),
    _an(
        "R-UMP",
        14,
        14,
        "DTE",
        "Rassemblement-UMP (2012-2013)",
        f"Scission temporaire de l'UMP ; LR = DTE : {_G2020} ; {_PROCHE}",
    ),
    _an("LES-REP", 14, 14, "DTE", "Les Républicains", f"LR → DTE : {_G2020}"),
    _an("LR", 14, 16, "DTE", "Les Républicains", f"LR → DTE : {_G2020}, {_G2023}"),
    _an("DR", 17, 17, "DTE", "Droite républicaine", f"LR → DTE : {_G2023}"),
    # --- Extrême droite ----------------------------------------------------
    _an("RN", 16, 17, "EXD", "Rassemblement national", f"RN → EXD : {_G2020}, {_G2023}"),
    _an(
        "UDR",
        17,
        17,
        "EXD",
        "Union des droites pour la République",
        f"UXD 2024 → EXD : {_G2023} (LUXD = EXD) ; {_G2026} (UDR = EXD, CE n° 512694)",
    ),
    _an(
        "UDDPLR",
        17,
        17,
        "EXD",
        "Union des droites pour la République (sigle Datan)",
        f"Variante de sigle UDR → EXD : {_G2023}, {_G2026}",
    ),
)

# ---------------------------------------------------------------------------
# Sénat — colonne « Groupe politique » d'ODSEN_GENERAL (groupe actuel ou dernier)
# ---------------------------------------------------------------------------

_SENAT: tuple[CorrespondanceGroupe, ...] = (
    # Groupes actuels (renouvellements 2020 et 2023)
    _senat(
        "CRCE-K",
        "GAU",
        "Communiste républicain citoyen et écologiste - Kanaky",
        f"PCF dominant = COM → GAU : {_G2020}, {_G2023}",
    ),
    _senat(
        "SER",
        "GAU",
        "Socialiste, écologiste et républicain",
        f"PS dominant = SOC → GAU : {_G2020}, {_G2023}",
    ),
    _senat(
        "GEST",
        "GAU",
        "Écologiste - Solidarité et territoires",
        f"EELV = VEC → GAU : {_G2020}, {_G2023} ; décision Mathias 2026-09-24 (Q21)",
    ),
    _senat(
        "RDPI",
        "CENT",
        "Rassemblement des démocrates, progressistes et indépendants",
        f"Renaissance : REM → CENT {_G2020}, REN → Centre {_G2023} ; "
        "décision Mathias 2026-09-24 (Q21)",
    ),
    _senat(
        "UC",
        "CENT",
        "Union centriste",
        f"UDI/centristes → CENT : {_G2020} (élus 2020), {_G2026}. Point ouvert : {_G2023} "
        "(élus 2023, doctrine ADR-0010) place UDI "
        "à Droite (sénateurs élus en 2023) — maintien CENT en attendant la décision Q14",
    ),
    _senat(
        "Les Indépendants",
        "CENT",
        "Les Indépendants - République et territoires",
        f"Doctrine ADR-0005 (parti dominant, grille de l'élection) : groupe rattaché à "
        f"Horizons (HOR → Centre : {_G2023}, {_G2026}) et à Agir (AGR → CENT : {_G2020}) ; "
        "décision Mathias 2026-09-24 (Q22, application de la doctrine)",
    ),
    _senat(
        "RDSE",
        "DIV",
        "Rassemblement démocratique et social européen",
        "Groupe composite (radicaux de gauche et valoisiens, divers) sans parti "
        "dominant → DIV, comme LT/LIOT à l'AN",
    ),
    _senat("Les Républicains", "DTE", "Les Républicains", f"LR → DTE : {_G2020}, {_G2023}"),
    _senat(
        "NI",
        "DIV",
        "Réunion administrative des sénateurs ne figurant sur la liste d'aucun groupe",
        "Aucun groupe ; exceptions dans leg_blocs_override",
    ),
    # Groupes historiques (dernier groupe d'anciens sénateurs, 2002-2023)
    _senat(
        "CRCE",
        "GAU",
        "Communiste républicain citoyen et écologiste (2017-2023)",
        f"PCF dominant → GAU : {_G2020}",
    ),
    _senat(
        "CRC",
        "GAU",
        "Communiste, républicain et citoyen (jusqu'en 2017)",
        f"PCF dominant = COM → GAU : {_G2020} ; {_PROCHE}",
    ),
    _senat(
        "SOC",
        "GAU",
        "Socialiste (jusqu'en 2017)",
        f"PS dominant = SOC → GAU : {_G2020} ; {_PROCHE}",
    ),
    _senat("SOCR", "GAU", "Socialiste et républicain (2017-2020)", f"PS dominant → GAU : {_G2020}"),
    _senat(
        "ECOLO",
        "GAU",
        "Écologiste (2012-2017)",
        f"EELV = VEC → GAU : {_G2020} ; {_PROCHE}",
    ),
    _senat("LaREM", "CENT", "La République en marche (2017-2020)", f"REM → CENT : {_G2020}"),
    _senat(
        "UC-UDF",
        "CENT",
        "Union centriste - UDF (2002-2011)",
        f"UDF → CENT (cohérent AN : UDF = CENT) ; {_RECONS}",
    ),
    _senat(
        "UMP",
        "DTE",
        "Union pour un mouvement populaire (2002-2015)",
        f"UMP → LR = DTE : {_G2020} ; {_PROCHE}",
    ),
)

CORRESPONDANCES_GROUPES: tuple[CorrespondanceGroupe, ...] = _AN + _SENAT


# ---------------------------------------------------------------------------
# Groupes sénatoriaux disparus avant le renouvellement de 2002 (addendum ADR-0011)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GroupeHorsPerimetre:
    """Groupe du Sénat dissous avant le renouvellement du 29 septembre 2002.

    Un ancien sénateur dont c'est le dernier groupe (ODSEN_GENERAL) a quitté le Sénat
    au plus tard à ce renouvellement : il est hors du périmètre 2002-présent. Aucun bloc
    n'est attribué (ce serait un classement hors périmètre).
    """

    sigle: str
    libelle: str
    periode: str
    justification: str


_CONNAISSANCE = (
    "connaissance générale de l'historique des groupes du Sénat, non vérifiée sur "
    "senat.fr (accès réseau indisponible le 2026-09-25) — à confirmer"
)

# Clé : sigle normalisé (majuscules, sans points, espaces ni tirets), cf. normaliser_sigle.
GROUPES_SENAT_ANTERIEURS_2002: tuple[GroupeHorsPerimetre, ...] = (
    GroupeHorsPerimetre(
        "UNR",
        "Union pour la nouvelle République",
        "1959-1968",
        f"Devenu UDR en 1968 ; {_CONNAISSANCE}",
    ),
    GroupeHorsPerimetre(
        "UNRUDT",
        "Union pour la nouvelle République - Union démocratique du travail",
        "années 1960",
        f"Variante de l'UNR ; {_CONNAISSANCE}",
    ),
    GroupeHorsPerimetre(
        "UDR",
        "Union des démocrates pour la République",
        "1968-1977",
        f"Devenu RPR en 1977 ; {_CONNAISSANCE}",
    ),
    GroupeHorsPerimetre(
        "RPR",
        "Rassemblement pour la République",
        "1977-2002",
        "Fondu dans le groupe UMP constitué après le renouvellement du 29 septembre 2002 "
        "(octobre 2002) : les sénateurs réélus en 2002 ont UMP (ou un groupe ultérieur) "
        f"pour dernier groupe ; RPR = mandat achevé au plus tard en septembre 2002 ; {_CONNAISSANCE}",
    ),
    GroupeHorsPerimetre(
        "RI",
        "Républicains et indépendants / Républicains indépendants",
        "1962-1977, puis 1995-2002",
        f"Fondu dans le groupe UMP en octobre 2002 (même raisonnement que RPR) ; {_CONNAISSANCE}",
    ),
    GroupeHorsPerimetre(
        "UREI",
        "Union des républicains et des indépendants",
        "1977-1995",
        f"Redevenu RI ; {_CONNAISSANCE}",
    ),
    GroupeHorsPerimetre(
        "IPAS",
        "Indépendants et paysans d'action sociale",
        "1959-1962",
        f"Groupe du début de la Ve République ; {_CONNAISSANCE}",
    ),
    GroupeHorsPerimetre(
        "CNIP",
        "Centre national des indépendants et paysans",
        "années 1960",
        f"Groupe des débuts de la Ve République ; {_CONNAISSANCE}",
    ),
    GroupeHorsPerimetre(
        "CRARS",
        "Centre républicain d'action rurale et sociale",
        "1959-1971",
        f"Disparu au début des années 1970 ; {_CONNAISSANCE}",
    ),
    GroupeHorsPerimetre(
        "GD",
        "Gauche démocratique",
        "jusqu'en 1989",
        f"Devenu RDE en 1989, puis RDSE en 1995 ; {_CONNAISSANCE}",
    ),
    GroupeHorsPerimetre(
        "RDE",
        "Rassemblement démocratique et européen",
        "1989-1995",
        f"Devenu RDSE en 1995 (RDSE, toujours existant, est classé) ; {_CONNAISSANCE}",
    ),
    GroupeHorsPerimetre(
        "RPCD",
        "Républicains populaires et Centre démocratique",
        "années 1960",
        f"Groupe démocrate-chrétien, remplacé par l'UCDP ; {_CONNAISSANCE}",
    ),
    GroupeHorsPerimetre(
        "UCDP",
        "Union centriste des démocrates de progrès",
        "1968-années 1970",
        f"Remplacé par l'Union centriste (UC, classée) ; {_CONNAISSANCE}",
    ),
    GroupeHorsPerimetre(
        "CD",
        "Centre démocratique",
        "années 1960",
        f"Groupe centriste des années 1960 ; {_CONNAISSANCE}",
    ),
    GroupeHorsPerimetre(
        "PDM",
        "Progrès et démocratie moderne",
        "1967-années 1970",
        f"Formation centriste des années 1970 ; {_CONNAISSANCE}",
    ),
    GroupeHorsPerimetre(
        "COM",
        "Groupe communiste",
        "jusqu'aux années 1990",
        f"Devenu Communiste républicain et citoyen (CRC, classé) ; {_CONNAISSANCE}",
    ),
)


def normaliser_sigle(sigle: str | None) -> str:
    """Sigle comparable : majuscules, sans points, espaces ni tirets (``G.D.`` → ``GD``)."""
    if not sigle:
        return ""
    return "".join(ch for ch in sigle.upper() if ch.isalnum())


_SIGLES_SENAT_ANTERIEURS_2002: frozenset[str] = frozenset(
    g.sigle for g in GROUPES_SENAT_ANTERIEURS_2002
)


def est_groupe_senat_anterieur_2002(groupe: str | None) -> bool:
    """Vrai si le groupe du Sénat a disparu avant le renouvellement de 2002."""
    return normaliser_sigle(groupe) in _SIGLES_SENAT_ANTERIEURS_2002


def valider_correspondances(
    correspondances: Iterable[CorrespondanceGroupe] = CORRESPONDANCES_GROUPES,
) -> None:
    """Lève ValueError si le référentiel est incohérent (bloc, chambre, bornes, recouvrement)."""
    correspondances_liste = list(correspondances)
    par_cle: dict[tuple[str, str], list[CorrespondanceGroupe]] = {}
    for c in correspondances_liste:
        if c.chambre not in CHAMBRES:
            raise ValueError(f"Chambre inconnue : {c}")
        if c.bloc not in BLOCS_VALIDES:
            raise ValueError(f"Bloc hors ADR-0005 : {c}")
        if not c.source_bloc.strip():
            raise ValueError(f"source_bloc vide : {c}")
        if c.chambre == "AN":
            if c.legislature_debut is None or c.legislature_fin is None:
                raise ValueError(f"Intervalle AN non borné : {c}")
            if c.legislature_debut > c.legislature_fin:
                raise ValueError(f"Intervalle AN inversé : {c}")
        par_cle.setdefault((c.chambre, c.groupe), []).append(c)

    for (chambre, groupe), lignes in par_cle.items():
        if len(lignes) == 1:
            continue
        if any(ligne.legislature_debut is None for ligne in lignes):
            raise ValueError(f"{chambre}/{groupe} : entrée non bornée et entrées multiples")
        lignes_triees = sorted(lignes, key=lambda x: x.legislature_debut or 0)
        for a, b in zip(lignes_triees, lignes_triees[1:], strict=False):
            if (b.legislature_debut or 0) <= (a.legislature_fin or 0):
                raise ValueError(f"{chambre}/{groupe} : intervalles qui se recouvrent")

    sigles_senat_classes = {
        normaliser_sigle(c.groupe) for c in correspondances_liste if c.chambre == "SENAT"
    }
    conflits = sigles_senat_classes & _SIGLES_SENAT_ANTERIEURS_2002
    if conflits:
        raise ValueError(f"Groupes Sénat à la fois classés et antérieurs à 2002 : {conflits}")


def resoudre_bloc(chambre: str, groupe: str | None, legislature: int | None) -> str | None:
    """Bloc du groupe pour la période donnée, ou None si non classé."""
    if not groupe:
        return None
    for c in CORRESPONDANCES_GROUPES:
        if c.chambre == chambre and c.groupe == groupe and c.couvre(legislature):
            return c.bloc
    return None


def journaliser_non_classes(chambre: str, non_classes: Counter[tuple[str, int | None]]) -> None:
    """Émet un WARNING récapitulatif des (groupe, législature) absents du référentiel."""
    if not non_classes:
        logger.info("%s : tous les groupes sont classés (référentiel ADR-0011)", chambre)
        return
    detail = ", ".join(
        f"{groupe} (lég. {leg if leg is not None else '-'}) × {n}"
        for (groupe, leg), n in sorted(non_classes.items(), key=lambda kv: (-kv[1], str(kv[0])))
    )
    logger.warning(
        "%s : %d élu(s) dans un groupe non classé, bloc NULL (compléter "
        "etl/legislatif_groupes.py après décision) : %s",
        chambre,
        sum(non_classes.values()),
        detail,
    )


def journaliser_sans_groupe(chambre: str, sans_groupe: Counter[int | None]) -> None:
    """INFO : élus sans groupe dans la source (statut explicite, aucun bloc attribué)."""
    if not sans_groupe:
        return
    detail = ", ".join(
        f"lég. {leg if leg is not None else '-'} × {n}"
        for leg, n in sorted(sans_groupe.items(), key=lambda kv: str(kv[0]))
    )
    logger.info(
        "%s : %d élu(s) sans groupe dans la source (groupe NULL, bloc NULL, hors contrôle "
        "de complétude du référentiel) : %s",
        chambre,
        sum(sans_groupe.values()),
        detail,
    )


def populate_groupes_blocs(con: duckdb.DuckDBPyConnection) -> int:
    """Recharge intégralement leg_groupes_blocs depuis le référentiel Python (idempotent)."""
    valider_correspondances()
    con.execute("DELETE FROM leg_groupes_blocs")
    con.executemany(
        "INSERT INTO leg_groupes_blocs (chambre, groupe, legislature_debut, legislature_fin, "
        "bloc, libelle, source_bloc) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (
                c.chambre,
                c.groupe,
                c.legislature_debut,
                c.legislature_fin,
                c.bloc,
                c.libelle,
                c.source_bloc,
            )
            for c in CORRESPONDANCES_GROUPES
        ],
    )
    n = len(CORRESPONDANCES_GROUPES)
    logger.info("leg_groupes_blocs : %d correspondances (groupe, législature) → bloc", n)
    return n
