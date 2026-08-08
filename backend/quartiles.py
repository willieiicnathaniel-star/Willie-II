"""
THEeye - Journal Quartile Database
Maps journal ISSNs / names to SCImago (SJR) quartiles.

Data source: SCImago Journal Rank (https://www.scimagojr.com/)
This file contains a curated subset of high-impact journals across fields.
For production use, load the full SCImago CSV from their website.
"""

# Mapping: ISSN -> (journal_name, quartile, subject_area)
# Quartiles based on SCImago SJR rankings.
QUARTILE_DB: dict[str, tuple[str, str, str]] = {
    # --- Economics & Finance ---
    "0304-3878": ("Journal of Development Economics", "Q1", "Economics"),
    "0022-1996": ("Journal of International Economics", "Q1", "Economics"),
    "0305-750X": ("World Development", "Q1", "Economics"),
    "0928-7655": ("Economic Systems", "Q1", "Economics"),
    "0147-5967": ("Journal of Comparative Economics", "Q1", "Economics"),
    "0165-1889": ("Journal of Economic Dynamics and Control", "Q1", "Economics"),
    "0304-3932": ("Journal of Monetary Economics", "Q1", "Economics"),
    "0047-2727": ("Journal of Public Economics", "Q1", "Economics"),
    "0167-6296": ("Health Economics", "Q1", "Economics"),
    "0264-9993": ("Economic Modelling", "Q1", "Economics"),
    "1056-8190": ("Review of Development Economics", "Q2", "Economics"),
    "1049-0078": ("Review of International Economics", "Q2", "Economics"),
    "0938-2259": ("Schmollers Jahrbuch", "Q3", "Economics"),
    "0377-2217": ("European Journal of Operational Research", "Q1", "Decision Sciences"),
    "0165-4101": ("Journal of Accounting and Economics", "Q1", "Economics"),
    "1574-0669": ("Economics & Human Biology", "Q2", "Economics"),
    "0176-2680": ("European Journal of Political Economy", "Q2", "Economics"),
    "0922-1425": ("Open Economies Review", "Q3", "Economics"),
    "1010-6609": ("Journal of International Development", "Q2", "Economics"),
    "1467-9361": ("Review of International Political Economy", "Q1", "Political Science"),

    # --- Finance ---
    "0304-405X": ("Journal of Financial Economics", "Q1", "Finance"),
    "0304-3932": ("Journal of Financial Economics", "Q1", "Finance"),
    "0261-5606": ("Journal of International Money and Finance", "Q1", "Finance"),
    "1042-4431": ("Journal of Forecasting", "Q2", "Finance"),
    "1572-3097": ("The Journal of Economic Asymmetry", "Q3", "Economics"),

    # --- Management & Business ---
    "0148-2963": ("Journal of Business Research", "Q1", "Business"),
    "0263-2373": ("International Journal of Hospitality Management", "Q1", "Business"),
    "0925-5273": ("International Journal of Production Economics", "Q1", "Business"),
    "0167-9236": ("Decision Support Systems", "Q1", "Information Systems"),

    # --- Social Sciences & Political Science ---
    "0305-750X": ("World Development", "Q1", "Social Sciences"),
    "0049-089X": ("Social Science Research", "Q2", "Social Sciences"),
    "0048-7333": ("Research Policy", "Q1", "Social Sciences"),

    # --- Environmental & Energy ---
    "0140-9883": ("Energy Economics", "Q1", "Economics"),
    "0961-4055": ("Energy Policy", "Q1", "Energy"),
    "1364-0321": ("Renewable and Sustainable Energy Reviews", "Q1", "Energy"),

    # --- Multidisciplinary / General Science ---
    "0036-8075": ("Science", "Q1", "Multidisciplinary"),
    "0028-0836": ("Nature", "Q1", "Multidisciplinary"),
    "2045-2322": ("Scientific Reports", "Q2", "Multidisciplinary"),
    "1758-2652": ("PLOS Neglected Tropical Diseases", "Q1", "Medicine"),
    "1932-6203": ("PLOS ONE", "Q2", "Multidisciplinary"),

    # --- Mathematics & Statistics ---
    "0167-9473": ("Computational Statistics & Data Analysis", "Q1", "Statistics"),

    # --- Medicine & Health ---
    "0277-9536": ("Social Science & Medicine", "Q1", "Medicine"),
    "1047-2797": ("Annals of Epidemiology", "Q2", "Medicine"),
}

# Build a name-based lookup (lowercase) for fuzzy matching
NAME_DB: dict[str, tuple[str, str, str]] = {}
for _issn, (_name, _q, _area) in QUARTILE_DB.items():
    _key = _name.lower().strip()
    NAME_DB[_key] = (_name, _q, _area)


def lookup_quartile(issn: str | None = None, journal_name: str | None = None) -> str | None:
    """
    Look up the SJR quartile for a journal by ISSN or name.

    Returns: 'Q1', 'Q2', 'Q3', 'Q4', or None if not found.
    """
    # Try ISSN first (exact match)
    if issn:
        clean = issn.strip().upper().replace(" ", "-")
        if clean in QUARTILE_DB:
            return QUARTILE_DB[clean][1]
        # Try without hyphen
        clean_nohyphen = clean.replace("-", "")
        for db_issn, (_, q, _) in QUARTILE_DB.items():
            if db_issn.replace("-", "") == clean_nohyphen:
                return q

    # Try journal name (exact, then fuzzy)
    if journal_name:
        name_lower = journal_name.lower().strip()
        if name_lower in NAME_DB:
            return NAME_DB[name_lower][1]
        # Fuzzy: check if any known journal name is contained in the input
        for known_name, (_, q, _) in NAME_DB.items():
            if known_name in name_lower or name_lower in known_name:
                return q

    return None


def get_all_journals() -> list[dict]:
    """Return all journals in the database for browsing."""
    result = []
    seen = set()
    for issn, (name, q, area) in QUARTILE_DB.items():
        key = (name, q)
        if key not in seen:
            seen.add(key)
            result.append({
                "journal": name,
                "issn": issn,
                "quartile": q,
                "subject_area": area,
            })
    return sorted(result, key=lambda x: (x["quartile"], x["journal"]))
