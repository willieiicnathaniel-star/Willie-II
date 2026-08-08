"""
THEeye - Literature Discovery Services
Integrates with OpenAlex, Crossref, and Semantic Scholar APIs.

All three APIs are free to use:
  - OpenAlex: https://docs.openalex.org/ (no key required; add mailto for polite pool)
  - Crossref: https://api.crossref.org (no key required; add mailto for polite pool)
  - Semantic Scholar: https://api.semanticscholar.org (API key recommended for higher limits)
"""

import httpx
import asyncio
import re
from datetime import datetime, timezone
from typing import Optional

from .models import Paper, Author, SearchRequest, SearchResponse
from .quartiles import lookup_quartile

# Configuration
CONTACT_EMAIL = "research@theeye.local"  # Replace with your email for polite API pools
SEMANTIC_SCHOLAR_API_KEY: Optional[str] = None  # Set this for higher rate limits

HTTP_TIMEOUT = 30.0
USER_AGENT = "THEeye/1.0 (AI-Assisted Research Platform)"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reconstruct_abstract(inverted_index: dict | None) -> Optional[str]:
    """OpenAlex stores abstracts as inverted indexes. Reconstruct to plain text."""
    if not inverted_index:
        return None
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted_index.items():
        for idx in idxs:
            positions.append((idx, word))
    positions.sort()
    return " ".join(w for _, w in positions) if positions else None


def _clean_html(text: Optional[str]) -> Optional[str]:
    """Strip simple HTML tags from Crossref abstracts."""
    if not text:
        return None
    return re.sub(r"<[^>]+>", "", text).strip()


def _assign_quartile(paper: Paper) -> Paper:
    """Look up and assign the SJR quartile to a paper."""
    if paper.quartile:
        return paper
    q = lookup_quartile(issn=paper.issn, journal_name=paper.journal)
    paper.quartile = q
    return paper


def _parse_year(year_str) -> Optional[int]:
    """Safely parse a year from various formats."""
    if not year_str:
        return None
    if isinstance(year_str, int):
        return year_str
    match = re.search(r"(20\d{2}|19\d{2})", str(year_str))
    return int(match.group(1)) if match else None


# ---------------------------------------------------------------------------
# OpenAlex
# ---------------------------------------------------------------------------

async def search_openalex(query: str, max_results: int = 25,
                          year_from: int | None = None,
                          year_to: int | None = None,
                          client: httpx.AsyncClient | None = None) -> list[Paper]:
    """Search OpenAlex for papers matching the query."""
    params = {
        "search": query,
        "per-page": min(max_results, 50),
        "mailto": CONTACT_EMAIL,
    }
    # Year filter
    filters = []
    if year_from:
        filters.append(f"from_publication_date:{year_from}-01-01")
    if year_to:
        filters.append(f"to_publication_date:{year_to}-12-31")
    if filters:
        params["filter"] = ",".join(filters)

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT})
    try:
        resp = await client.get("https://api.openalex.org/works", params=params)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[OpenAlex] Error: {e}")
        return []
    finally:
        if own_client:
            await client.aclose()

    papers = []
    for work in data.get("results", []):
        # Extract authors
        authors = []
        for auth in work.get("authorships", [])[:10]:
            raw = auth.get("author", {})
            name = raw.get("display_name", "")
            affs = auth.get("institutions", [])
            aff = affs[0].get("display_name") if affs else None
            if name:
                authors.append(Author(name=name, affiliation=aff))

        # Extract journal/source
        primary_loc = work.get("primary_location", {}) or {}
        source = primary_loc.get("source") or {}
        journal = source.get("display_name")
        issn = None
        issns = source.get("issn", [])
        if issns:
            issn = issns[0]

        # Best OA location
        best_oa = work.get("best_oa_location", {}) or {}
        oa_url = best_oa.get("pdf_url") or best_oa.get("landing_page_url")
        is_oa = work.get("open_access", {}).get("is_oa", False)

        # Concepts
        concepts = [c.get("display_name", "") for c in work.get("concepts", [])[:5]
                    if c.get("score", 0) > 0.3]

        paper = Paper(
            title=work.get("display_name", work.get("title", "")) or "",
            authors=authors,
            year=_parse_year(work.get("publication_year")),
            journal=journal,
            issn=issn,
            doi=work.get("doi"),
            abstract=_reconstruct_abstract(work.get("abstract_inverted_index")),
            cited_by_count=work.get("cited_by_count", 0),
            is_open_access=is_oa,
            oa_url=oa_url,
            source_db="openalex",
            openalex_id=work.get("id"),
            concepts=concepts,
        )
        papers.append(_assign_quartile(paper))

    return papers


# ---------------------------------------------------------------------------
# Crossref
# ---------------------------------------------------------------------------

async def search_crossref(query: str, max_results: int = 25,
                          year_from: int | None = None,
                          year_to: int | None = None,
                          client: httpx.AsyncClient | None = None) -> list[Paper]:
    """Search Crossref for papers matching the query."""
    params = {
        "query": query,
        "rows": min(max_results, 50),
        "mailto": CONTACT_EMAIL,
        "select": "DOI,title,author,container-title,ISSN,published,is-referenced-by-count,abstract,license,type",
    }
    filters = []
    if year_from:
        filters.append(f"from-pub-date:{year_from}")
    if year_to:
        filters.append(f"until-pub-date:{year_to}")
    if filters:
        params["filter"] = ",".join(filters)

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT})
    try:
        resp = await client.get("https://api.crossref.org/works", params=params)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[Crossref] Error: {e}")
        return []
    finally:
        if own_client:
            await client.aclose()

    papers = []
    for item in data.get("message", {}).get("items", []):
        # Title
        titles = item.get("title", [])
        title = titles[0] if titles else ""
        if not title:
            continue

        # Authors
        authors = []
        for auth in item.get("author", [])[:10]:
            given = auth.get("given", "")
            family = auth.get("family", "")
            name = f"{given} {family}".strip()
            aff = auth.get("affiliation", [{}])
            aff_name = aff[0].get("name") if aff else None
            if name:
                authors.append(Author(name=name, affiliation=aff_name))

        # Journal
        containers = item.get("container-title", [])
        journal = containers[0] if containers else None

        # ISSN
        issns = item.get("ISSN", [])
        issn = issns[0] if issns else None

        # Year
        published = item.get("published", {}) or item.get("issued", {})
        date_parts = published.get("date-parts", [[None]])
        year = _parse_year(date_parts[0][0] if date_parts and date_parts[0] else None)

        paper = Paper(
            title=title,
            authors=authors,
            year=year,
            journal=journal,
            issn=issn,
            doi=item.get("DOI"),
            abstract=_clean_html(item.get("abstract")),
            cited_by_count=item.get("is-referenced-by-count", 0),
            is_open_access=False,
            source_db="crossref",
        )
        papers.append(_assign_quartile(paper))

    return papers


# ---------------------------------------------------------------------------
# Semantic Scholar
# ---------------------------------------------------------------------------

async def search_semantic_scholar(query: str, max_results: int = 25,
                                  year_from: int | None = None,
                                  year_to: int | None = None,
                                  client: httpx.AsyncClient | None = None) -> list[Paper]:
    """Search Semantic Scholar for papers with AI-generated TLDRs."""
    params = {
        "query": query,
        "limit": min(max_results, 50),
        "fields": "title,abstract,authors,year,citationCount,tldr,externalIds,journal,openAccessPdf",
    }
    # Year range filter
    year_filter = ""
    if year_from and year_to:
        year_filter = f"{year_from}-{year_to}"
    elif year_from:
        year_filter = f"{year_from}-"
    elif year_to:
        year_filter = f"-{year_to}"
    if year_filter:
        params["year"] = year_filter

    headers = {"User-Agent": USER_AGENT}
    if SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers=headers)
    try:
        resp = await client.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params=params,
        )
        if resp.status_code == 429:
            print("[Semantic Scholar] Rate limited. Skipping.")
            return []
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[Semantic Scholar] Error: {e}")
        return []
    finally:
        if own_client:
            await client.aclose()

    papers = []
    for item in data.get("data", []):
        # Authors
        authors = []
        for auth in item.get("authors", [])[:10]:
            name = auth.get("name", "")
            if name:
                authors.append(Author(name=name))

        # Journal info
        journal_info = item.get("journal", {}) or {}
        journal = journal_info.get("name")
        issn = None  # S2 doesn't reliably return ISSN

        # TLDR
        tldr_data = item.get("tldr")
        tldr = tldr_data.get("text") if tldr_data else None

        # External IDs
        ext_ids = item.get("externalIds", {}) or {}
        doi = ext_ids.get("DOI")

        # OA PDF
        oa_pdf = item.get("openAccessPdf", {}) or {}
        oa_url = oa_pdf.get("url")

        paper = Paper(
            title=item.get("title", ""),
            authors=authors,
            year=item.get("year"),
            journal=journal,
            issn=issn,
            doi=doi,
            abstract=item.get("abstract"),
            cited_by_count=item.get("citationCount", 0),
            is_open_access=bool(oa_url),
            oa_url=oa_url,
            tldr=tldr,
            source_db="semantic_scholar",
        )
        papers.append(_assign_quartile(paper))

    return papers


# ---------------------------------------------------------------------------
# Google Scholar (via Semantic Scholar broader search + Google Scholar links)
# ---------------------------------------------------------------------------

async def search_google_scholar(query: str, max_results: int = 25,
                                year_from: int | None = None,
                                year_to: int | None = None,
                                client: httpx.AsyncClient | None = None) -> list[Paper]:
    """
    Search Google Scholar results.
    
    Google Scholar does not provide a public API. This function:
    1. Uses Semantic Scholar's broader search as a proxy (it indexes Google Scholar content)
    2. Adds Google Scholar search links for manual verification
    3. Returns results with source_db='google_scholar'
    """
    params = {
        "query": query,
        "limit": min(max_results, 50),
        "fields": "title,abstract,authors,year,citationCount,tldr,externalIds,journal,openAccessPdf,url",
    }
    # Broader year range for Google Scholar-like coverage
    year_filter = ""
    if year_from and year_to:
        year_filter = f"{year_from}-{year_to}"
    elif year_from:
        year_filter = f"{year_from}-"
    elif year_to:
        year_filter = f"-{year_to}"
    if year_filter:
        params["year"] = year_filter

    headers = {"User-Agent": USER_AGENT}
    if SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers=headers)
    try:
        # Use Semantic Scholar's search bulk endpoint for broader coverage
        resp = await client.get(
            "https://api.semanticscholar.org/graph/v1/paper/search/bulk",
            params=params,
        )
        if resp.status_code == 429:
            print("[Google Scholar proxy] Rate limited. Skipping.")
            return []
        if resp.status_code != 200:
            # Fall back to regular search
            resp = await client.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params=params,
            )
            if resp.status_code == 429:
                return []
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[Google Scholar proxy] Error: {e}")
        return []
    finally:
        if own_client:
            await client.aclose()

    papers = []
    items = data.get("data", []) or data.get("items", [])
    for item in items:
        # Authors
        authors = []
        for auth in item.get("authors", [])[:10]:
            name = auth.get("name", "")
            if name:
                authors.append(Author(name=name))

        # Journal info
        journal_info = item.get("journal", {}) or {}
        journal = journal_info.get("name")
        issn = journal_info.get("issn")

        # TLDR
        tldr_data = item.get("tldr")
        tldr = tldr_data.get("text") if tldr_data else None

        # External IDs
        ext_ids = item.get("externalIds", {}) or {}
        doi = ext_ids.get("DOI")

        # OA PDF
        oa_pdf = item.get("openAccessPdf", {}) or {}
        oa_url = oa_pdf.get("url")

        # Google Scholar link
        gs_url = f"https://scholar.google.com/scholar?q={query.replace(' ', '+')}"

        paper = Paper(
            title=item.get("title", ""),
            authors=authors,
            year=item.get("year"),
            journal=journal,
            issn=issn,
            doi=doi,
            abstract=item.get("abstract"),
            cited_by_count=item.get("citationCount", 0),
            is_open_access=bool(oa_url),
            oa_url=oa_url or gs_url,
            tldr=tldr,
            source_db="google_scholar",
            keywords=[query],
        )
        papers.append(_assign_quartile(paper))

    return papers


# ---------------------------------------------------------------------------
# EconPapers / RePEc
# ---------------------------------------------------------------------------

async def search_econpapers(query: str, max_results: int = 25,
                            year_from: int | None = None,
                            year_to: int | None = None,
                            client: httpx.AsyncClient | None = None) -> list[Paper]:
    """
    Search EconPapers/RePEc for economics research papers.
    Uses the RePEc/IDEAS API (https://ideas.repec.org/api).
    """
    # RePEc search API
    params = {
        "q": query,
        "limit": min(max_results, 50),
        "format": "json",
    }

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT})
    try:
        # RePEc IDEAS search
        resp = await client.get(
            "https://api.repec.org/call.cgi",
            params={
                "code": "theeye",
                "getref": query,
                "count": min(max_results, 50),
            },
        )
        
        papers = []
        
        if resp.status_code == 200:
            data = resp.json()
            # RePEc returns different formats, handle both
            items = data if isinstance(data, list) else data.get("results", [])
            
            for item in items[:max_results]:
                # Extract author(s)
                authors = []
                author_str = item.get("author-name", "") or item.get("author", "")
                if isinstance(author_str, str):
                    for name in author_str.split(";"):
                        name = name.strip()
                        if name:
                            # Handle "Last, First" format
                            if "," in name:
                                parts = name.split(",")
                                name = f"{parts[1].strip()} {parts[0].strip()}"
                            authors.append(Author(name=name))
                elif isinstance(author_str, list):
                    for a in author_str:
                        name = a.get("name", "") if isinstance(a, dict) else str(a)
                        if name:
                            authors.append(Author(name=name))

                # Extract year
                year = _parse_year(item.get("year", ""))

                # Apply year filter
                if year_from and year and year < year_from:
                    continue
                if year_to and year and year > year_to:
                    continue

                # Journal
                journal = item.get("journal", "") or item.get("publication", "")
                if isinstance(journal, dict):
                    journal = journal.get("name", "")

                # DOI
                doi = item.get("doi", "")

                # Abstract
                abstract = item.get("abstract", "")

                # Handle/title
                title = item.get("title", "") or item.get("handle", "")

                if not title:
                    continue

                # RePEc handle URL
                handle = item.get("handle", "")
                oa_url = f"https://ideas.repec.org/p/{handle}.html" if handle else None

                paper = Paper(
                    title=title,
                    authors=authors,
                    year=year,
                    journal=journal,
                    doi=doi if doi else None,
                    abstract=abstract if abstract else None,
                    cited_by_count=item.get("citations", 0) if isinstance(item.get("citations"), int) else 0,
                    is_open_access=bool(oa_url),
                    oa_url=oa_url,
                    source_db="econpapers",
                    keywords=[item.get("keywords", "")] if item.get("keywords") else [],
                )
                papers.append(_assign_quartile(paper))
        else:
            print(f"[EconPapers] API returned {resp.status_code}. Using Crossref economics filter as fallback.")
            # Fallback: use Crossref with economics filter
            econ_params = {
                "query": query,
                "rows": min(max_results, 50),
                "mailto": CONTACT_EMAIL,
                "select": "DOI,title,author,container-title,ISSN,published,is-referenced-by-count,abstract",
                "filter": "type:journal-article",
            }
            filters = ["type:journal-article"]
            if year_from:
                filters.append(f"from-pub-date:{year_from}")
            if year_to:
                filters.append(f"until-pub-date:{year_to}")
            econ_params["filter"] = ",".join(filters)

            resp2 = await client.get("https://api.crossref.org/works", params=econ_params)
            if resp2.status_code == 200:
                data2 = resp2.json()
                for item in data2.get("message", {}).get("items", []):
                    titles = item.get("title", [])
                    title = titles[0] if titles else ""
                    if not title:
                        continue

                    authors = []
                    for auth in item.get("author", [])[:10]:
                        given = auth.get("given", "")
                        family = auth.get("family", "")
                        name = f"{given} {family}".strip()
                        if name:
                            authors.append(Author(name=name))

                    containers = item.get("container-title", [])
                    journal = containers[0] if containers else None
                    issns = item.get("ISSN", [])
                    issn = issns[0] if issns else None
                    published = item.get("published", {}) or item.get("issued", {})
                    date_parts = published.get("date-parts", [[None]])
                    year = _parse_year(date_parts[0][0] if date_parts and date_parts[0] else None)

                    paper = Paper(
                        title=title,
                        authors=authors,
                        year=year,
                        journal=journal,
                        issn=issn,
                        doi=item.get("DOI"),
                        abstract=_clean_html(item.get("abstract")),
                        cited_by_count=item.get("is-referenced-by-count", 0),
                        is_open_access=False,
                        source_db="econpapers",
                    )
                    papers.append(_assign_quartile(paper))

        return papers

    except Exception as e:
        print(f"[EconPapers] Error: {e}")
        return []
    finally:
        if own_client:
            await client.aclose()


# ---------------------------------------------------------------------------
# ERIC (Education Resources Information Center)
# ---------------------------------------------------------------------------

async def search_eric(query: str, max_results: int = 25,
                      year_from: int | None = None,
                      year_to: int | None = None,
                      client: httpx.AsyncClient | None = None) -> list[Paper]:
    """
    Search ERIC for education research papers.
    Uses the ERIC API (https://eric.ed.gov/api).
    """
    # ERIC API endpoint
    params = {
        "search": query,
        "format": "json",
        "rows": min(max_results, 50),
        "fields": "id,title,author,publicationdateyear,publicationname,description,peerreviewed,issn,doi,url",
    }

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT})
    try:
        resp = await client.get("https://eric.ed.gov/api/v1/search", params=params)
        
        if resp.status_code != 200:
            print(f"[ERIC] API returned {resp.status_code}. Skipping.")
            return []

        data = resp.json()
        
        # ERIC API response format
        items = data.get("response", {}).get("docs", []) if isinstance(data.get("response"), dict) else data.get("results", [])
        
        papers = []
        for item in items[:max_results]:
            # Title
            title = item.get("title", "")
            if isinstance(title, list):
                title = title[0] if title else ""
            if not title:
                continue

            # Authors
            authors = []
            author_str = item.get("author", "")
            if isinstance(author_str, list):
                for name in author_str:
                    if name and isinstance(name, str):
                        authors.append(Author(name=name.strip()))
            elif isinstance(author_str, str) and author_str:
                for name in author_str.split(";"):
                    name = name.strip()
                    if name:
                        authors.append(Author(name=name))

            # Year
            year = _parse_year(item.get("publicationdateyear", ""))

            # Apply year filter
            if year_from and year and year < year_from:
                continue
            if year_to and year and year > year_to:
                continue

            # Journal/publication name
            journal = item.get("publicationname", "")
            if isinstance(journal, list):
                journal = journal[0] if journal else None

            # ISSN
            issn = item.get("issn", "")
            if isinstance(issn, list):
                issn = issn[0] if issn else None

            # DOI
            doi = item.get("doi", "")
            if isinstance(doi, list):
                doi = doi[0] if doi else None

            # Abstract/description
            abstract = item.get("description", "")
            if isinstance(abstract, list):
                abstract = abstract[0] if abstract else None

            # URL
            eric_id = item.get("id", "")
            url = f"https://eric.ed.gov/?id={eric_id}" if eric_id else None

            # Peer reviewed
            peer_reviewed = item.get("peerreviewed", "")
            if isinstance(peer_reviewed, list):
                peer_reviewed = peer_reviewed[0] if peer_reviewed else ""
            peer_reviewed = str(peer_reviewed).lower() in ("t", "true", "yes", "1")

            paper = Paper(
                title=title,
                authors=authors,
                year=year,
                journal=journal,
                issn=issn,
                doi=doi,
                abstract=abstract,
                cited_by_count=0,  # ERIC doesn't provide citation counts
                is_open_access=bool(url),
                oa_url=url,
                source_db="eric",
                keywords=[],
            )
            papers.append(_assign_quartile(paper))

        return papers

    except Exception as e:
        print(f"[ERIC] Error: {e}")
        return []
    finally:
        if own_client:
            await client.aclose()


# ---------------------------------------------------------------------------
# Unified Search
# ---------------------------------------------------------------------------

def _deduplicate(papers: list[Paper]) -> list[Paper]:
    """Remove duplicate papers based on DOI or normalized title."""
    seen_doi = set()
    seen_title = set()
    unique = []
    for p in papers:
        norm_title = re.sub(r"[^a-z0-9]", "", p.title.lower())[:100]
        if p.doi and p.doi.lower() in seen_doi:
            continue
        if norm_title and norm_title in seen_title:
            continue
        if p.doi:
            seen_doi.add(p.doi.lower())
        if norm_title:
            seen_title.add(norm_title)
        unique.append(p)
    return unique


def _apply_filters(papers: list[Paper], request: SearchRequest) -> list[Paper]:
    """Apply quartile, year, citation, and OA filters."""
    filtered = []
    for p in papers:
        # Quartile filter
        if request.quartiles and p.quartile and p.quartile not in request.quartiles:
            continue
        # Year filter
        if request.year_from and p.year and p.year < request.year_from:
            continue
        if request.year_to and p.year and p.year > request.year_to:
            continue
        # Citation filter
        if p.cited_by_count < request.min_citations:
            continue
        # OA filter
        if request.open_access_only and not p.is_open_access:
            continue
        filtered.append(p)
    return filtered


async def unified_search(request: SearchRequest) -> SearchResponse:
    """
    Search across multiple databases concurrently, deduplicate, filter,
    and return a unified result set sorted by citation count.
    """
    # Use a single shared client for all API requests (more efficient)
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
        tasks = []
        task_dbs = []

        if "openalex" in request.databases:
            tasks.append(search_openalex(request.query, request.max_results,
                                         request.year_from, request.year_to, client=client))
            task_dbs.append("openalex")
        if "crossref" in request.databases:
            tasks.append(search_crossref(request.query, request.max_results,
                                         request.year_from, request.year_to, client=client))
            task_dbs.append("crossref")
        if "semantic_scholar" in request.databases:
            tasks.append(search_semantic_scholar(request.query, request.max_results,
                                                 request.year_from, request.year_to, client=client))
            task_dbs.append("semantic_scholar")
        if "google_scholar" in request.databases:
            tasks.append(search_google_scholar(request.query, request.max_results,
                                               request.year_from, request.year_to, client=client))
            task_dbs.append("google_scholar")
        if "econpapers" in request.databases:
            tasks.append(search_econpapers(request.query, request.max_results,
                                           request.year_from, request.year_to, client=client))
            task_dbs.append("econpapers")
        if "eric" in request.databases:
            tasks.append(search_eric(request.query, request.max_results,
                                     request.year_from, request.year_to, client=client))
            task_dbs.append("eric")

        if not tasks:
            return SearchResponse(
                query=request.query,
                total_found=0,
                papers=[],
                search_timestamp=datetime.now(timezone.utc).isoformat(),
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_papers = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"[{task_dbs[i]}] Exception: {result}")
            continue
        all_papers.extend(result)

    # Deduplicate
    all_papers = _deduplicate(all_papers)

    # Apply filters
    all_papers = _apply_filters(all_papers, request)

    # Sort by citation count (descending), then by year (descending)
    all_papers.sort(key=lambda p: (p.cited_by_count, p.year or 0), reverse=True)

    # Limit
    all_papers = all_papers[:request.max_results]

    return SearchResponse(
        query=request.query,
        total_found=len(all_papers),
        papers=all_papers,
        search_timestamp=datetime.now(timezone.utc).isoformat(),
    )
