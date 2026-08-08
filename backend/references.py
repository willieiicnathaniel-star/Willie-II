"""
THEeye - Reference Management Module
Export and manage references in multiple formats compatible with
Mendeley, Zotero, NotePal, and other reference managers.

Supported export formats:
  - BibTeX (for LaTeX/BibTeX users, Zotero, Mendeley)
  - RIS (universal format, works with all reference managers)
  - CSL JSON (Citation Style Language, for Zotero, Mendeley)
  - EndNote XML
  - APA/MLA/Chicago/Harvard formatted citations
"""

import json
import re
from typing import Optional
from .models import Paper


# ---------------------------------------------------------------------------
# Reference Manager Registry
# ---------------------------------------------------------------------------

REFERENCE_MANAGERS = {
    "mendeley": {
        "name": "Mendeley",
        "url": "https://www.mendeley.com",
        "description": "Reference manager and academic social network by Elsevier",
        "import_formats": ["ris", "bibtex", "csl_json"],
        "import_instructions": [
            "1. Download the RIS or BibTeX file from THEeye",
            "2. Open Mendeley Desktop or Mendeley Reference Manager",
            "3. Go to File > Import > RIS (or BibTeX)",
            "4. Select the downloaded file",
            "5. Review imported references and add to collections",
        ],
        "web_importer": "https://www.mendeley.com/reference-management/web-importer",
    },
    "zotero": {
        "name": "Zotero",
        "url": "https://www.zotero.org",
        "description": "Free, open-source reference manager",
        "import_formats": ["ris", "bibtex", "csl_json"],
        "import_instructions": [
            "1. Download the RIS or CSL JSON file from THEeye",
            "2. Open Zotero",
            "3. Go to File > Import",
            "4. Select the downloaded file",
            "5. Choose whether to import into a new collection",
            "6. Review imported references",
        ],
        "web_importer": "https://www.zotero.org/download/",
        "browser_connector": "Zotero Connector browser extension can capture references directly",
    },
    "notepal": {
        "name": "NotePal",
        "url": "https://notepal.com",
        "description": "Research note-taking and reference management tool",
        "import_formats": ["ris", "bibtex"],
        "import_instructions": [
            "1. Download the RIS or BibTeX file from THEeye",
            "2. Open NotePal",
            "3. Go to References > Import",
            "4. Select the downloaded file",
            "5. Organize references into your research notes",
        ],
    },
}


def get_reference_managers() -> dict:
    """Get all reference manager integrations."""
    return REFERENCE_MANAGERS.copy()


def get_reference_manager(manager_id: str) -> dict | None:
    """Get a specific reference manager by ID."""
    return REFERENCE_MANAGERS.get(manager_id)


# ---------------------------------------------------------------------------
# BibTeX Export
# ---------------------------------------------------------------------------

def export_bibtex(papers: list[Paper]) -> str:
    """Export papers as BibTeX format."""
    entries = []
    for i, paper in enumerate(papers, 1):
        # Generate citation key
        key = _generate_bibtex_key(paper, i)

        # Authors
        if paper.authors:
            authors = " and ".join(a.name for a in paper.authors)
        else:
            authors = "Unknown"

        # Build entry
        entry = f"@article{{{key},\n"
        entry += f"  title     = {{{_escape_bibtex(paper.title)}}},\n"
        entry += f"  author    = {{{_escape_bibtex(authors)}}},\n"

        if paper.journal:
            entry += f"  journal   = {{{_escape_bibtex(paper.journal)}}},\n"
        if paper.year:
            entry += f"  year      = {{{paper.year}}},\n"
        if paper.doi:
            entry += f"  doi       = {{{paper.doi}}},\n"
        if paper.issn:
            entry += f"  issn      = {{{paper.issn}}},\n"
        if paper.volume:
            entry += f"  volume    = {{{paper.volume}}},\n"
        if paper.quartile:
            entry += f"  note      = {{SJR Quartile: {paper.quartile}}},\n"
        if paper.abstract:
            # Truncate abstract for BibTeX
            abstract = paper.abstract[:500] + "..." if len(paper.abstract) > 500 else paper.abstract
            entry += f"  abstract  = {{{_escape_bibtex(abstract)}}},\n"
        if paper.source_db:
            entry += f"  source    = {{{paper.source_db}}},\n"

        entry += "}\n"
        entries.append(entry)

    return "\n".join(entries)


def _generate_bibtex_key(paper: Paper, index: int) -> str:
    """Generate a BibTeX citation key."""
    if paper.authors and paper.authors[0].name:
        # Get last name of first author
        name_parts = paper.authors[0].name.split()
        last_name = name_parts[-1].lower() if name_parts else "unknown"
        last_name = re.sub(r'[^a-z]', '', last_name)
    else:
        last_name = "unknown"

    year = paper.year or "nd"
    # Add first word of title for uniqueness
    title_word = ""
    if paper.title:
        words = re.findall(r'[a-zA-Z]+', paper.title)
        if words:
            title_word = re.sub(r'[^a-z]', '', words[0].lower())

    return f"{last_name}{year}{title_word}"


def _escape_bibtex(text: str) -> str:
    """Escape special characters for BibTeX."""
    if not text:
        return ""
    text = text.replace("&", r"\&")
    text = text.replace("%", r"\%")
    text = text.replace("_", r"\_")
    text = text.replace("#", r"\#")
    text = text.replace("$", r"\$")
    return text


# ---------------------------------------------------------------------------
# RIS Export
# ---------------------------------------------------------------------------

def export_ris(papers: list[Paper]) -> str:
    """Export papers as RIS format (compatible with all reference managers)."""
    entries = []
    for paper in papers:
        entry = "TY  - JOUR\n"

        # Title
        if paper.title:
            entry += f"TI  - {paper.title}\n"
            entry += f"T1  - {paper.title}\n"

        # Authors
        for author in paper.authors:
            entry += f"AU  - {author.name}\n"
            if author.affiliation:
                entry += f"C1  - {author.affiliation}\n"

        # Journal
        if paper.journal:
            entry += f"JO  - {paper.journal}\n"
            entry += f"JF  - {paper.journal}\n"

        # Year
        if paper.year:
            entry += f"PY  - {paper.year}\n"
            entry += f"Y1  - {paper.year}\n"

        # DOI
        if paper.doi:
            entry += f"DO  - {paper.doi}\n"

        # ISSN
        if paper.issn:
            entry += f"SN  - {paper.issn}\n"

        # Abstract
        if paper.abstract:
            entry += f"AB  - {paper.abstract}\n"
            entry += f"N2  - {paper.abstract}\n"

        # Citation count
        if paper.cited_by_count:
            entry += f"M3  - Citations: {paper.cited_by_count}\n"

        # Quartile
        if paper.quartile:
            entry += f"M1  - SJR Quartile: {paper.quartile}\n"

        # Open access
        if paper.is_open_access and paper.oa_url:
            entry += f"UR  - {paper.oa_url}\n"
        elif paper.doi:
            entry += f"UR  - https://doi.org/{paper.doi}\n"

        # Source database
        if paper.source_db:
            entry += f"M2  - Source: {paper.source_db}\n"

        # TLDR from Semantic Scholar
        if paper.tldr:
            entry += f"N1  - AI Summary: {paper.tldr}\n"

        entry += "ER  - \n"
        entries.append(entry)

    return "\n".join(entries)


# ---------------------------------------------------------------------------
# CSL JSON Export
# ---------------------------------------------------------------------------

def export_csl_json(papers: list[Paper]) -> str:
    """Export papers as CSL JSON (Citation Style Language)."""
    items = []
    for paper in papers:
        item = {
            "type": "article-journal",
            "title": paper.title,
        }

        # Authors
        if paper.authors:
            item["author"] = []
            for author in paper.authors:
                name_parts = author.name.split()
                if len(name_parts) >= 2:
                    item["author"].append({
                        "family": name_parts[-1],
                        "given": " ".join(name_parts[:-1]),
                    })
                else:
                    item["author"].append({"literal": author.name})

        if paper.journal:
            item["container-title"] = paper.journal
        if paper.year:
            item["issued"] = {"date-parts": [[paper.year]]}
        if paper.doi:
            item["DOI"] = paper.doi
        if paper.issn:
            item["ISSN"] = [paper.issn]
        if paper.abstract:
            item["abstract"] = paper.abstract
        if paper.cited_by_count:
            item["citation-count"] = paper.cited_by_count
        if paper.is_open_access and paper.oa_url:
            item["URL"] = paper.oa_url
        elif paper.doi:
            item["URL"] = f"https://doi.org/{paper.doi}"

        # Custom fields
        if paper.quartile:
            item["custom"] = {"SJR-quartile": paper.quartile}
        if paper.source_db:
            item["source-database"] = paper.source_db

        items.append(item)

    return json.dumps(items, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# EndNote XML Export
# ---------------------------------------------------------------------------

def export_endnote_xml(papers: list[Paper]) -> str:
    """Export papers as EndNote XML format."""
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<records>\n'

    for paper in papers:
        xml += '  <record>\n'
        xml += '    <ref-type name="Journal Article">17</ref-type>\n'

        if paper.title:
            xml += f'    <title><style face="normal" font="default">{_escape_xml(paper.title)}</style></title>\n'

        if paper.authors:
            xml += '    <authors>\n'
            xml += '      <authors>\n'
            for author in paper.authors:
                xml += f'        <author><style face="normal" font="default">{_escape_xml(author.name)}</style></author>\n'
            xml += '      </authors>\n'
            xml += '    </authors>\n'

        if paper.journal:
            xml += f'    <periodical><full-title><style face="normal" font="default">{_escape_xml(paper.journal)}</style></full-title></periodical>\n'

        if paper.year:
            xml += f'    <dates><year><style face="normal" font="default">{paper.year}</style></year></dates>\n'

        if paper.doi:
            xml += f'    <electronic-resource-num><style face="normal" font="default">{paper.doi}</style></electronic-resource-num>\n'

        if paper.issn:
            xml += f'    <issn><style face="normal" font="default">{paper.issn}</style></issn>\n'

        if paper.abstract:
            xml += f'    <abstract><style face="normal" font="default">{_escape_xml(paper.abstract[:500])}</style></abstract>\n'

        if paper.quartile:
            xml += f'    <notes><style face="normal" font="default">SJR Quartile: {paper.quartile}</style></notes>\n'

        xml += '  </record>\n'

    xml += '</records>\n'
    return xml


def _escape_xml(text: str) -> str:
    """Escape special characters for XML."""
    if not text:
        return ""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&apos;")
    return text


# ---------------------------------------------------------------------------
# Formatted Citations (APA, MLA, Chicago, Harvard)
# ---------------------------------------------------------------------------

def format_citation_apa(paper: Paper) -> str:
    """Format a single paper as APA 7th edition citation."""
    # Authors
    if paper.authors:
        author_str = _format_authors_apa(paper.authors)
    else:
        author_str = "Unknown"

    year = f"({paper.year})" if paper.year else "(n.d.)"
    title = paper.title or ""
    journal = paper.journal or ""
    doi = f" https://doi.org/{paper.doi}" if paper.doi else ""

    return f"{author_str} {year}. {title}. {journal}.{doi}"


def format_citation_mla(paper: Paper) -> str:
    """Format a single paper as MLA 9th edition citation."""
    if paper.authors:
        author_str = _format_authors_mla(paper.authors)
    else:
        author_str = ""

    title = f'"{paper.title}."' if paper.title else ""
    journal = paper.journal or ""
    year = str(paper.year) if paper.year else "n.d."
    doi = f" doi:{paper.doi}." if paper.doi else ""

    parts = [p for p in [author_str, title, journal, year] if p]
    return " ".join(parts) + doi


def format_citation_chicago(paper: Paper) -> str:
    """Format a single paper as Chicago author-date citation."""
    if paper.authors:
        author_str = _format_authors_chicago(paper.authors)
    else:
        author_str = "Unknown"

    year = str(paper.year) if paper.year else "n.d."
    title = paper.title or ""
    journal = paper.journal or ""
    doi = f" https://doi.org/{paper.doi}." if paper.doi else "."

    return f'{author_str} {year}. "{title}" {journal}.{doi}'


def format_citation_harvard(paper: Paper) -> str:
    """Format a single paper as Harvard citation."""
    if paper.authors:
        author_str = _format_authors_harvard(paper.authors)
    else:
        author_str = "Anon"

    year = str(paper.year) if paper.year else "n.d."
    title = paper.title or ""
    journal = paper.journal or ""
    doi = f" DOI: {paper.doi}" if paper.doi else ""

    return f'{author_str} {year}. {title}. {journal}.{doi}'


def format_citations(papers: list[Paper], style: str = "apa") -> list[dict]:
    """Format multiple papers in the specified citation style."""
    formatters = {
        "apa": format_citation_apa,
        "mla": format_citation_mla,
        "chicago": format_citation_chicago,
        "harvard": format_citation_harvard,
    }

    formatter = formatters.get(style.lower(), format_citation_apa)
    results = []

    for i, paper in enumerate(papers, 1):
        results.append({
            "number": i,
            "citation": formatter(paper),
            "doi": paper.doi,
            "title": paper.title,
        })

    return results


def _format_authors_apa(authors: list) -> str:
    """Format authors for APA style."""
    if not authors:
        return "Unknown"
    if len(authors) == 1:
        return _format_single_author_apa(authors[0].name)
    elif len(authors) == 2:
        return f"{_format_single_author_apa(authors[0].name)} & {_format_single_author_apa(authors[1].name)}"
    elif len(authors) <= 20:
        formatted = [_format_single_author_apa(a.name) for a in authors[:-1]]
        return ", ".join(formatted) + f", & {_format_single_author_apa(authors[-1].name)}"
    else:
        formatted = [_format_single_author_apa(a.name) for a in authors[:19]]
        return ", ".join(formatted) + ", ... " + _format_single_author_apa(authors[-1].name)


def _format_single_author_apa(name: str) -> str:
    """Format a single author name for APA."""
    parts = name.split()
    if len(parts) >= 2:
        last = parts[-1]
        initials = ". ".join(p[0].upper() for p in parts[:-1] if p) + "."
        return f"{last}, {initials}"
    return name


def _format_authors_mla(authors: list) -> str:
    """Format authors for MLA style."""
    if not authors:
        return ""
    if len(authors) == 1:
        return _format_single_author_mla(authors[0].name)
    elif len(authors) == 2:
        return f"{_format_single_author_mla(authors[0].name)}, and {_format_authors_first_last(authors[1].name)}"
    else:
        return f"{_format_single_author_mla(authors[0].name)}, et al."


def _format_single_author_mla(name: str) -> str:
    """Format single author for MLA (Last, First)."""
    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[-1]}, {' '.join(parts[:-1])}"
    return name


def _format_authors_first_last(name: str) -> str:
    """Format author as First Last."""
    return name


def _format_authors_chicago(authors: list) -> str:
    """Format authors for Chicago style."""
    if not authors:
        return "Unknown"
    if len(authors) == 1:
        return _format_single_author_chicago(authors[0].name)
    elif len(authors) <= 3:
        first = _format_single_author_chicago(authors[0].name)
        rest = ", ".join(a.name for a in authors[1:-1])
        last = authors[-1].name
        if rest:
            return f"{first}, {rest}, and {last}"
        return f"{first}, and {last}"
    else:
        return f"{_format_single_author_chicago(authors[0].name)} et al."


def _format_single_author_chicago(name: str) -> str:
    """Format single author for Chicago (First Last)."""
    parts = name.split()
    if len(parts) >= 2:
        return f"{' '.join(parts[:-1])} {parts[-1]}"
    return name


def _format_authors_harvard(authors: list) -> str:
    """Format authors for Harvard style."""
    if not authors:
        return "Anon"
    if len(authors) == 1:
        return _format_single_author_harvard(authors[0].name)
    elif len(authors) == 2:
        return f"{_format_single_author_harvard(authors[0].name)} and {_format_single_author_harvard(authors[1].name)}"
    else:
        return f"{_format_single_author_harvard(authors[0].name)} et al."


def _format_single_author_harvard(name: str) -> str:
    """Format single author for Harvard (Last, F.)."""
    parts = name.split()
    if len(parts) >= 2:
        last = parts[-1]
        initials = "".join(p[0].upper() + "." for p in parts[:-1] if p)
        return f"{last}, {initials}"
    return name


# ---------------------------------------------------------------------------
# Export Dispatcher
# ---------------------------------------------------------------------------

EXPORT_FORMATS = {
    "bibtex": {"name": "BibTeX", "extension": ".bib", "description": "For LaTeX, Zotero, Mendeley"},
    "ris": {"name": "RIS", "extension": ".ris", "description": "Universal format for all reference managers"},
    "csl_json": {"name": "CSL JSON", "extension": ".json", "description": "Citation Style Language JSON for Zotero/Mendeley"},
    "endnote": {"name": "EndNote XML", "extension": ".xml", "description": "For EndNote users"},
    "apa": {"name": "APA 7th", "extension": ".txt", "description": "Formatted APA citations"},
    "mla": {"name": "MLA 9th", "extension": ".txt", "description": "Formatted MLA citations"},
    "chicago": {"name": "Chicago", "extension": ".txt", "description": "Formatted Chicago citations"},
    "harvard": {"name": "Harvard", "extension": ".txt", "description": "Formatted Harvard citations"},
}


def get_export_formats() -> dict:
    """Get all available export formats."""
    return EXPORT_FORMATS.copy()


def export_references(papers: list[Paper], format: str = "bibtex") -> dict:
    """
    Export papers in the specified format.

    Returns: {"format": format, "content": str, "filename": str, "count": int}
    """
    if format == "bibtex":
        content = export_bibtex(papers)
    elif format == "ris":
        content = export_ris(papers)
    elif format == "csl_json":
        content = export_csl_json(papers)
    elif format == "endnote":
        content = export_endnote_xml(papers)
    elif format in ("apa", "mla", "chicago", "harvard"):
        citations = format_citations(papers, format)
        content = "\n\n".join(f"[{c['number']}] {c['citation']}" for c in citations)
    else:
        content = export_bibtex(papers)
        format = "bibtex"

    fmt_info = EXPORT_FORMATS.get(format, EXPORT_FORMATS["bibtex"])
    filename = f"theeye_references{fmt_info['extension']}"

    return {
        "format": format,
        "format_name": fmt_info["name"],
        "content": content,
        "filename": filename,
        "count": len(papers),
    }


# ---------------------------------------------------------------------------
# Citation Verification Engine
# ---------------------------------------------------------------------------

def verify_citations(text: str, references: list[dict]) -> dict:
    """Verify that inline citations in *text* correspond to entries in *references*.

    Parses several common inline-citation patterns from the text, cross-checks
    each against the supplied reference list, and reports:

      * **matched**  – citations that correctly match a reference entry
      * **orphan_citations** – citations found in the text but absent from the
        reference list
      * **uncited_references** – references that are never cited in the text
      * **mismatches** – numbered citations whose author/year details do not
        match the corresponding reference entry

    Returns a structured dict with all findings and a human-readable summary.
    """
    if not text or not text.strip():
        return {
            "total_citations_found": 0,
            "total_references": len(references),
            "matched": [],
            "orphan_citations": [],
            "uncited_references": [],
            "mismatches": [],
            "summary": "No text provided for verification.",
            "all_correct": False,
        }

    # ------------------------------------------------------------------
    # 1. Parse all inline citations from the text
    # ------------------------------------------------------------------
    citations_found: list[dict] = []

    # Pattern A: (Author, Year) [ref_num]  — THEeye's own format
    pattern_a = re.compile(
        r'\(([^)]+?),\s*(\d{4}|n\.d\.)\)\s*\[(\d+)\]'
    )
    for m in pattern_a.finditer(text):
        citations_found.append({
            "raw": m.group(0),
            "author_text": m.group(1).strip(),
            "year": m.group(2).strip(),
            "ref_num": int(m.group(3)),
            "type": "numbered_with_details",
            "position": m.start(),
        })

    # Track ref_nums and positions already captured
    captured_ref_nums = {c["ref_num"] for c in citations_found if c["ref_num"]}
    captured_positions = {c["position"] for c in citations_found}
    # Also track the range of each pattern A match to avoid pattern B matching [N] inside it
    captured_ranges = [(c["position"], c["position"] + len(c["raw"])) for c in citations_found]

    # Pattern B: [N] — bare numbered citation (only if not already captured by A)
    pattern_b = re.compile(r'\[(\d+)\]')
    for m in pattern_b.finditer(text):
        ref_num = int(m.group(1))
        # Skip if this ref_num was already captured by pattern A
        if ref_num in captured_ref_nums:
            continue
        # Skip if this position falls within a pattern A match range
        if any(start <= m.start() < end for start, end in captured_ranges):
            continue
        citations_found.append({
            "raw": m.group(0),
            "author_text": None,
            "year": None,
            "ref_num": ref_num,
            "type": "numbered_only",
            "position": m.start(),
        })

    # Pattern C: (Author, Year) or (Author et al., Year) — APA-style
    pattern_c = re.compile(
        r'\(([^)]+?),\s*(\d{4}|n\.d\.)\)'
    )
    for m in pattern_c.finditer(text):
        author_text = m.group(1).strip()
        year = m.group(2).strip()
        # Skip if already captured by pattern A (same position or within range)
        if m.start() in captured_positions:
            continue
        if any(start <= m.start() < end for start, end in captured_ranges):
            continue
        # Skip if this looks like a page range or other non-citation
        if any(ch in author_text for ch in ['-', '/']) and not any(
            ch.isalpha() for ch in author_text
        ):
            continue
        citations_found.append({
            "raw": m.group(0),
            "author_text": author_text,
            "year": year,
            "ref_num": None,
            "type": "author_year",
            "position": m.start(),
        })

    # Pattern D: Author (Year) — narrative citation
    pattern_d = re.compile(
        r'([A-Z][a-z]+(?:\s+(?:et al\.|&|and)\s+[A-Z][a-z]+)?)\s+\((\d{4}|n\.d\.)\)'
    )
    for m in pattern_d.finditer(text):
        author_text = m.group(1).strip()
        year = m.group(2).strip()
        if any(c["position"] == m.start() for c in citations_found):
            continue
        citations_found.append({
            "raw": m.group(0),
            "author_text": author_text,
            "year": year,
            "ref_num": None,
            "type": "narrative",
            "position": m.start(),
        })

    # ------------------------------------------------------------------
    # 2. Build reference lookup structures
    # ------------------------------------------------------------------
    refs_by_num: dict[int, dict] = {}
    refs_by_author_year: dict[str, dict] = {}
    ref_nums_cited: set[int] = set()

    for ref in references:
        num = ref.get("ref_number") or ref.get("number")
        if num:
            refs_by_num[int(num)] = ref
        # Build author-year key for fuzzy matching
        author_str = ref.get("authors", "") or ref.get("author", "")
        year_str = str(ref.get("year", "")) or ""
        if author_str and year_str:
            # Normalize: lowercase, take first author's last name
            first_author = author_str.split(",")[0].split("&")[0].split(" and ")[0].strip()
            key = f"{first_author.lower()}_{year_str}"
            refs_by_author_year[key] = ref
            # Also store with "et al" variant
            if "et al" in author_str.lower() or len(author_str.split(",")) > 1:
                key_et_al = f"{first_author.lower()}_et al_{year_str}"
                refs_by_author_year[key_et_al] = ref

    # ------------------------------------------------------------------
    # 3. Cross-check each citation against references
    # ------------------------------------------------------------------
    matched: list[dict] = []
    orphan_citations: list[dict] = []
    mismatches: list[dict] = []

    for cite in citations_found:
        ref_num = cite.get("ref_num")
        author_text = cite.get("author_text")
        year = cite.get("year")

        # Try to match by reference number first
        if ref_num is not None:
            ref_nums_cited.add(ref_num)
            if ref_num in refs_by_num:
                ref = refs_by_num[ref_num]
                # Verify author/year details if available
                if author_text and year:
                    ref_authors = ref.get("authors", "") or ref.get("author", "")
                    ref_year = str(ref.get("year", ""))
                    # Check year match
                    if year != "n.d." and ref_year and year != ref_year:
                        mismatches.append({
                            "citation": cite["raw"],
                            "issue": f"Year mismatch: citation says '{year}' but reference [{ref_num}] says '{ref_year}'",
                            "ref_num": ref_num,
                            "citation_year": year,
                            "reference_year": ref_year,
                            "suggested_correction": f"Reference [{ref_num}]: {ref_authors} ({ref_year}). {ref.get('title', '')}. {ref.get('journal', '')}",
                        })
                    # Check author match (fuzzy)
                    elif author_text and ref_authors:
                        # Extract first author last name from both
                        cite_first = author_text.split(",")[0].split("&")[0].split(" and ")[0].strip().lower()
                        ref_first = ref_authors.split(",")[0].split("&")[0].split(" and ")[0].strip().lower()
                        if cite_first and ref_first and cite_first not in ref_first and ref_first not in cite_first:
                            mismatches.append({
                                "citation": cite["raw"],
                                "issue": f"Author mismatch: citation says '{author_text}' but reference [{ref_num}] says '{ref_authors}'",
                                "ref_num": ref_num,
                                "citation_author": author_text,
                                "reference_author": ref_authors,
                                "suggested_correction": f"Reference [{ref_num}]: {ref_authors} ({ref_year}). {ref.get('title', '')}. {ref.get('journal', '')}",
                            })
                        else:
                            matched.append({
                                "citation": cite["raw"],
                                "ref_num": ref_num,
                                "matched_reference": _ref_summary(ref),
                            })
                    else:
                        matched.append({
                            "citation": cite["raw"],
                            "ref_num": ref_num,
                            "matched_reference": _ref_summary(ref),
                        })
                else:
                    matched.append({
                        "citation": cite["raw"],
                        "ref_num": ref_num,
                        "matched_reference": _ref_summary(ref),
                    })
            else:
                orphan_citations.append({
                    "citation": cite["raw"],
                    "ref_num": ref_num,
                    "issue": f"Citation [{ref_num}] appears in text but reference [{ref_num}] is missing from the reference list.",
                    "author_text": author_text,
                    "year": year,
                })

        # Try to match by author-year (for non-numbered citations)
        elif author_text and year:
            first_author = author_text.split(",")[0].split("&")[0].split(" and ")[0].strip()
            key = f"{first_author.lower()}_{year}"
            key_et_al = f"{first_author.lower()}_et al_{year}"

            matched_ref = refs_by_author_year.get(key) or refs_by_author_year.get(key_et_al)
            if matched_ref:
                ref_num = matched_ref.get("ref_number") or matched_ref.get("number")
                if ref_num:
                    ref_nums_cited.add(int(ref_num))
                matched.append({
                    "citation": cite["raw"],
                    "ref_num": ref_num,
                    "matched_reference": _ref_summary(matched_ref),
                })
            else:
                # Try fuzzy matching on author last name + year
                fuzzy_found = False
                for rkey, ref in refs_by_author_year.items():
                    ref_first = rkey.split("_")[0]
                    if first_author.lower() in ref_first or ref_first in first_author.lower():
                        if year in rkey:
                            ref_num = ref.get("ref_number") or ref.get("number")
                            if ref_num:
                                ref_nums_cited.add(int(ref_num))
                            matched.append({
                                "citation": cite["raw"],
                                "ref_num": ref_num,
                                "matched_reference": _ref_summary(ref),
                                "note": "Fuzzy author match",
                            })
                            fuzzy_found = True
                            break
                if not fuzzy_found:
                    orphan_citations.append({
                        "citation": cite["raw"],
                        "ref_num": None,
                        "issue": f"Citation '{cite['raw']}' not found in the reference list.",
                        "author_text": author_text,
                        "year": year,
                    })

    # ------------------------------------------------------------------
    # 4. Find uncited references
    # ------------------------------------------------------------------
    uncited_references: list[dict] = []
    for ref in references:
        num = ref.get("ref_number") or ref.get("number")
        if num and int(num) not in ref_nums_cited:
            uncited_references.append({
                "ref_num": int(num),
                "reference": _ref_summary(ref),
                "issue": f"Reference [{num}] is listed but never cited in the text.",
            })

    # ------------------------------------------------------------------
    # 5. Build summary
    # ------------------------------------------------------------------
    total_issues = len(orphan_citations) + len(uncited_references) + len(mismatches)
    all_correct = total_issues == 0 and len(citations_found) > 0

    if all_correct:
        summary = (
            f"All {len(citations_found)} citation(s) correctly match the "
            f"{len(references)} reference(s). No issues found."
        )
    elif len(citations_found) == 0:
        summary = "No inline citations detected in the text. Make sure your text contains citations like (Author, Year) [1] or [1]."
    else:
        parts = []
        if orphan_citations:
            parts.append(f"{len(orphan_citations)} orphan citation(s)")
        if uncited_references:
            parts.append(f"{len(uncited_references)} uncited reference(s)")
        if mismatches:
            parts.append(f"{len(mismatches)} mismatch(es)")
        summary = (
            f"Found {total_issues} issue(s): {', '.join(parts)}. "
            f"Checked {len(citations_found)} citation(s) against "
            f"{len(references)} reference(s)."
        )

    return {
        "total_citations_found": len(citations_found),
        "total_references": len(references),
        "matched": matched,
        "orphan_citations": orphan_citations,
        "uncited_references": uncited_references,
        "mismatches": mismatches,
        "summary": summary,
        "all_correct": all_correct,
    }


def _ref_summary(ref: dict) -> str:
    """Build a short human-readable summary of a reference entry."""
    authors = ref.get("authors", "") or ref.get("author", "") or "Unknown"
    year = ref.get("year", "n.d.")
    title = ref.get("title", "") or ""
    if title and len(title) > 80:
        title = title[:80] + "..."
    journal = ref.get("journal", "") or ""
    doi = ref.get("doi", "") or ""
    parts = [f"{authors} ({year})"]
    if title:
        parts.append(f'"{title}"')
    if journal:
        parts.append(journal)
    if doi:
        parts.append(f"DOI: {doi}")
    return ". ".join(parts)
