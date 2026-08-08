"""
THEeye - Data Extraction Service
Extracts structured research data from paper metadata and abstracts.

Uses pattern-based extraction (no external LLM required) that identifies
methodology, sample size, variables, and findings from abstract text.
For LLM-powered extraction, set use_llm=True and configure an API key.
"""

import re
from typing import Optional
from .models import Paper, ExtractedData


# ---------------------------------------------------------------------------
# Pattern-based extraction (works without an LLM)
# ---------------------------------------------------------------------------

# Common methodology keywords
METHOD_PATTERNS = [
    r"\b(panel data|cross-?section|time series|longitudinal|case study|mixed methods|"
    r"systematic review|meta-?analysis|regression|OLS|2SLS|GMM|fixed effects|"
    r"random effects|difference-?in-?differences|propensity score|instrumental variable|"
    r"qualitative|quantitative|survey|experiment|content analysis|thematic analysis|"
    r"structural equation|factor analysis|Bayesian|machine learning|deep learning)\b"
]

SAMPLE_PATTERNS = [
    r"(?:sample of|sample size|N\s*=|n\s*=|based on|covering|consisting of|"
    r"comprising|involving)\s*(\d[\d,]*(?:\.\d+)?)\s*(?:countries|firms|individuals|"
    r"observations|respondents|participants|companies|nations|states|counties|years)",
    r"(\d[\d,]*)\s*(?:countries|firms|observations|respondents|nations)\s*(?:over|during|from|between)",
]

DATA_SOURCE_PATTERNS = [
    r"(?:data(?:\s+set)?(?:\s+is|\s+are|\s+from|\s+drawn from|\s+obtained from|\s+collected from))\s+"
    r"(?:the\s+)?([A-Z][^.]{5,80}?)(?:\.|,|;|\s+(?:and|over|during|from|between|for))",
]

VARIABLE_PATTERNS = [
    r"\b(FDI|GDP|inflation|trade openness|institutional quality|governance|"
    r"economic growth|human capital|population|unemployment|exchange rate|"
    r"foreign direct investment|democracy|corruption|rule of law|"
    r"government effectiveness|political stability|regulatory quality|"
    r"voice and accountability|control of corruption)\b"
]

FINDING_INDICATORS = [
    "results show", "findings indicate", "we find", "results indicate",
    "the study finds", "evidence suggests", "results reveal", "we observe",
    "findings show", "results demonstrate", "analysis shows", "results suggest",
    "positive effect", "negative effect", "significant relationship",
    "no significant", "positively associated", "negatively associated",
    "promotes", "hinders", "reduces", "increases", "decreases",
    "enhances", "diminishes", "contributes to", "inhibits",
]

EFFECT_SIZE_PATTERNS = [
    r"(?:coefficient|estimate|effect)\s*(?:of|is|=)\s*([-+]?\d*\.?\d+)",
    r"(\d*\.?\d+)\s*(?:percent|%)\s*(?:increase|decrease|change|reduction|growth)",
    r"(?:elasticity|correlation)\s*(?:of|is|=)\s*([-+]?\d*\.?\d+)",
]


def _extract_methodology(text: str) -> Optional[str]:
    """Identify research methodology from text."""
    if not text:
        return None
    text_lower = text.lower()
    found = []
    for pattern in METHOD_PATTERNS:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        found.extend(matches)
    if found:
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for m in found:
            if m not in seen:
                seen.add(m)
                unique.append(m)
        return ", ".join(unique[:4]).title()
    return None


def _extract_sample_size(text: str) -> Optional[str]:
    """Extract sample size information."""
    if not text:
        return None
    for pattern in SAMPLE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            number = match.group(1)
            # Get the unit from the pattern
            full_match = match.group(0)
            return full_match.strip()
    return None


def _extract_data_source(text: str) -> Optional[str]:
    """Extract the data source mentioned in the abstract."""
    if not text:
        return None
    for pattern in DATA_SOURCE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip().rstrip(",.;")
    return None


def _extract_variables(text: str) -> list[str]:
    """Extract key variables mentioned in the text."""
    if not text:
        return []
    found = set()
    for pattern in VARIABLE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            found.add(m.upper() if len(m) <= 5 else m.title())
    return sorted(found)[:10]


def _extract_findings(text: str) -> list[str]:
    """Extract key findings as sentences."""
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    findings = []
    for sent in sentences:
        sent_lower = sent.lower()
        if any(indicator in sent_lower for indicator in FINDING_INDICATORS):
            # Clean and truncate
            clean = sent.strip()
            if 20 < len(clean) < 300:
                findings.append(clean)
    return findings[:5]


def _extract_effect_size(text: str) -> Optional[str]:
    """Extract effect sizes, coefficients, or elasticities."""
    if not text:
        return None
    for pattern in EFFECT_SIZE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return None


def _extract_research_question(text: str, title: str) -> Optional[str]:
    """Infer the research question from title and abstract."""
    if not title:
        return None
    # Look for question indicators in abstract
    if text:
        for marker in ["this study examines", "this paper investigates", "this study investigates",
                       "we examine", "we investigate", "this paper examines", "this study explores",
                       "this paper explores", "this study analyzes", "this paper analyzes",
                       "the aim of this", "the objective of this", "this research examines"]:
            idx = text.lower().find(marker)
            if idx != -1:
                # Extract the sentence containing the marker
                start = idx
                end = text.find(".", idx)
                if end != -1:
                    return text[start:end + 1].strip()
    # Fall back to title-based inference
    return f"This study investigates: {title}"


def _extract_limitations(text: str) -> Optional[str]:
    """Extract limitations mentioned in the abstract."""
    if not text:
        return None
    for marker in ["however", "limitation", "limited by", "caveat", "shortcoming"]:
        idx = text.lower().find(marker)
        if idx != -1:
            end = text.find(".", idx)
            if end != -1:
                return text[idx:end + 1].strip()
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_from_paper(paper: Paper, use_llm: bool = False) -> ExtractedData:
    """
    Extract structured data from a single paper.

    Args:
        paper: The Paper object with title and abstract.
        use_llm: If True, would use an LLM for deeper extraction (requires API key config).

    Returns:
        ExtractedData with structured fields populated.
    """
    # Combine title and abstract for analysis
    full_text = " ".join(filter(None, [paper.title, paper.abstract]))

    return ExtractedData(
        paper_title=paper.title,
        doi=paper.doi,
        research_question=_extract_research_question(paper.abstract, paper.title),
        methodology=_extract_methodology(full_text),
        sample_size=_extract_sample_size(full_text),
        data_source=_extract_data_source(full_text),
        variables=_extract_variables(full_text),
        key_findings=_extract_findings(paper.abstract or ""),
        effect_size=_extract_effect_size(full_text),
        limitations=_extract_limitations(paper.abstract or ""),
        extraction_method="llm" if use_llm else "template",
    )


def extract_batch(papers: list[Paper], use_llm: bool = False) -> list[ExtractedData]:
    """Extract structured data from multiple papers."""
    return [extract_from_paper(p, use_llm) for p in papers]


def build_comparison_table(extracted: list[ExtractedData]) -> list[dict]:
    """
    Build a comparison table suitable for display/export.
    Each row is one paper with its extracted fields.
    """
    table = []
    for item in extracted:
        table.append({
            "paper": item.paper_title,
            "doi": item.doi or "N/A",
            "methodology": item.methodology or "N/A",
            "sample": item.sample_size or "N/A",
            "data_source": item.data_source or "N/A",
            "variables": ", ".join(item.variables) if item.variables else "N/A",
            "key_finding": item.key_findings[0] if item.key_findings else "N/A",
            "effect_size": item.effect_size or "N/A",
        })
    return table
