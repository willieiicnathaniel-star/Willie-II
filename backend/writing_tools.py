"""
THEeye - Writing Tools Module
Integration with external writing enhancement tools and local writing analysis.

Tools integrated:
  - Grammarly: Grammar, style, and clarity checking
  - QuillBot: Paraphrasing and rewriting
  - Paperpal: Academic writing assistant

Local features:
  - Readability analysis (Flesch-Kincaid, Gunning Fog)
  - Academic tone assessment
  - Passive voice detection
  - Sentence structure analysis
"""

import re
import math
from typing import Optional


# ---------------------------------------------------------------------------
# Tool Registry
# ---------------------------------------------------------------------------

WRITING_TOOLS = {
    "grammarly": {
        "name": "Grammarly",
        "url": "https://www.grammarly.com",
        "description": "AI-powered grammar, spelling, punctuation, style, and tone checker. "
                       "Offers real-time suggestions for clarity, engagement, and delivery.",
        "category": "grammar_style",
        "features": [
            "Grammar and spell check",
            "Style and tone suggestions",
            "Clarity improvements",
            "Plagiarism detection (premium)",
            "Vocabulary enhancement",
        ],
        "how_to_use": [
            "1. Go to grammarly.com and create an account",
            "2. Upload your draft or paste text into the Grammarly editor",
            "3. Review and accept/reject suggestions",
            "4. Copy the improved text back to your document",
        ],
        "integration_type": "external_link",
        "free_tier": True,
    },
    "quillbot": {
        "name": "QuillBot",
        "url": "https://quillbot.com",
        "description": "AI-powered paraphrasing and rewriting tool. Offers multiple modes "
                       "(Standard, Fluency, Formal, Academic, Simple) for different writing contexts.",
        "category": "paraphrasing",
        "features": [
            "Paraphrasing with multiple modes",
            "Academic mode for scholarly writing",
            "Sentence restructuring",
            "Synonym suggestions",
            "Summarizer tool",
            "Grammar checker",
        ],
        "how_to_use": [
            "1. Go to quillbot.com",
            "2. Paste your text into the paraphraser",
            "3. Select 'Academic' mode for research papers",
            "4. Review paraphrased suggestions",
            "5. Use the summarizer for literature review condensation",
        ],
        "integration_type": "external_link",
        "free_tier": True,
    },
    "paperpal": {
        "name": "Paperpal",
        "url": "https://paperpal.com",
        "description": "Academic writing assistant by Cactus Communications. Specialized for "
                       "research paper writing with subject-specific suggestions and journal formatting.",
        "category": "academic_writing",
        "features": [
            "Academic language enhancement",
            "Subject-specific writing suggestions",
            "Journal-specific formatting",
            "Tone adjustment for academic writing",
            "Translation support",
            "Manuscript checks",
        ],
        "how_to_use": [
            "1. Go to paperpal.com and sign up",
            "2. Upload your manuscript or paste text",
            "3. Select your subject area and target journal",
            "4. Review AI-powered suggestions for academic improvement",
            "5. Export the polished manuscript",
        ],
        "integration_type": "external_link",
        "free_tier": True,
    },
}


def get_writing_tools() -> dict:
    """Get all writing tool integrations."""
    return WRITING_TOOLS.copy()


def get_writing_tool(tool_id: str) -> dict | None:
    """Get a specific writing tool by ID."""
    return WRITING_TOOLS.get(tool_id)


# ---------------------------------------------------------------------------
# Local Writing Analysis (no external API needed)
# ---------------------------------------------------------------------------

def analyze_writing(text: str) -> dict:
    """
    Perform local writing quality analysis on text.
    Returns readability metrics, style assessment, and improvement suggestions.
    """
    if not text or len(text.strip()) < 10:
        return {"error": "Text too short for analysis."}

    # Basic counts
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    words = re.findall(r'\b[a-zA-Z]+\b', text)
    syllables = sum(_count_syllables(word) for word in words)

    num_sentences = len(sentences)
    num_words = len(words)
    num_syllables = syllables
    num_chars = len(text)

    if num_sentences == 0 or num_words == 0:
        return {"error": "Unable to parse text."}

    # Readability metrics
    flesch_reading_ease = 206.835 - (1.015 * (num_words / num_sentences)) - (84.6 * (num_syllables / num_words))
    flesch_grade_level = 0.39 * (num_words / num_sentences) + 11.8 * (num_syllables / num_words) - 15.59
    gunning_fog = 0.4 * ((num_words / num_sentences) + _count_complex_words(words) * (100 / num_words))

    # Passive voice detection (simplified)
    passive_patterns = [
        r'\b(?:is|are|was|were|be|been|being)\s+\w+ed\b',
        r'\b(?:is|are|was|were|be|been|being)\s+being\s+\w+ed\b',
    ]
    passive_count = 0
    for pattern in passive_patterns:
        passive_count += len(re.findall(pattern, text, re.IGNORECASE))

    # Sentence length analysis
    sentence_lengths = [len(re.findall(r'\b[a-zA-Z]+\b', s)) for s in sentences]
    avg_sentence_length = num_words / num_sentences
    long_sentences = sum(1 for l in sentence_lengths if l > 25)
    short_sentences = sum(1 for l in sentence_lengths if l < 10)

    # Academic tone indicators
    academic_words = [
        'furthermore', 'moreover', 'nevertheless', 'consequently', 'subsequently',
        'therefore', 'however', 'thus', 'hence', 'accordingly', 'specifically',
        'particularly', 'notably', 'essentially', 'fundamentally', 'predominantly',
        'systematically', 'comprehensive', 'empirical', 'methodology', 'theoretical',
        'hypothesis', 'framework', 'analysis', 'significance', 'correlation',
        'regression', 'variable', 'coefficient', 'robust', 'endogeneity',
    ]
    academic_word_count = sum(1 for w in words if w.lower() in academic_words)
    academic_ratio = academic_word_count / num_words if num_words > 0 else 0

    # Transition words
    transitions = [
        'however', 'therefore', 'moreover', 'furthermore', 'consequently',
        'nevertheless', 'meanwhile', 'subsequently', 'in addition', 'for instance',
        'for example', 'in contrast', 'on the other hand', 'as a result',
        'in conclusion', 'firstly', 'secondly', 'finally', 'overall',
    ]
    transition_count = sum(1 for t in transitions if t in text.lower())

    # Generate suggestions
    suggestions = []

    if avg_sentence_length > 25:
        suggestions.append({
            "type": "readability",
            "message": f"Average sentence length is {avg_sentence_length:.1f} words. Consider breaking up long sentences for better readability.",
            "severity": "medium",
        })
    elif avg_sentence_length < 10:
        suggestions.append({
            "type": "readability",
            "message": f"Average sentence length is {avg_sentence_length:.1f} words. Consider combining short sentences for better flow.",
            "severity": "low",
        })

    if passive_count > num_sentences * 0.3:
        suggestions.append({
            "type": "style",
            "message": f"Found {passive_count} instances of passive voice. Consider using active voice for stronger, clearer writing.",
            "severity": "medium",
        })

    if academic_ratio < 0.02:
        suggestions.append({
            "type": "tone",
            "message": "Low use of academic vocabulary. Consider incorporating more scholarly terminology.",
            "severity": "low",
        })

    if transition_count < num_sentences * 0.2:
        suggestions.append({
            "type": "structure",
            "message": "Few transition words detected. Add transitions (however, therefore, moreover) to improve logical flow.",
            "severity": "medium",
        })

    if flesch_reading_ease < 30:
        suggestions.append({
            "type": "readability",
            "message": f"Flesch Reading Ease is {flesch_reading_ease:.1f} (very difficult). Consider simplifying language.",
            "severity": "high",
        })

    if long_sentences > num_sentences * 0.3:
        suggestions.append({
            "type": "readability",
            "message": f"{long_sentences} sentences exceed 25 words. Consider splitting them.",
            "severity": "medium",
        })

    # --- Enhanced analysis: structure, argument, academic standards ---
    structure_analysis = _analyze_structure(text)
    argument_analysis = _analyze_argument_quality(text, sentences, words)
    standards_analysis = _analyze_academic_standards(text, words)

    # Structure-based suggestions
    if not structure_analysis["has_hierarchy"]:
        suggestions.append({
            "type": "structure",
            "message": "No headings or section structure detected. Use Markdown headings (#, ##, ###) or numbered sections (1., 1.1.) to organize your text academically.",
            "severity": "high",
        })
    else:
        for issue in structure_analysis["hierarchy_issues"]:
            suggestions.append({
                "type": "structure",
                "message": issue,
                "severity": "medium",
            })

    missing_key_sections = [s for s in structure_analysis["sections_missing"]
                           if s.lower() in ["introduction", "literature review", "methodology",
                                            "results", "discussion", "conclusion"]]
    if missing_key_sections:
        suggestions.append({
            "type": "structure",
            "message": f"Missing key academic sections: {', '.join(missing_key_sections[:5])}. Consider adding these sections for a complete academic structure.",
            "severity": "medium",
        })

    # Argument-based suggestions
    if not argument_analysis["has_thesis_statement"]:
        suggestions.append({
            "type": "argument",
            "message": "No clear thesis or claim statement detected. Add a statement like 'This study argues...' or 'This paper examines...' to establish your central argument.",
            "severity": "high",
        })

    if argument_analysis["counterargument_count"] == 0:
        suggestions.append({
            "type": "argument",
            "message": "No counterarguments or opposing viewpoints detected. Engage with alternative perspectives using 'however', 'on the other hand', or 'critics argue' to strengthen your scholarly debate.",
            "severity": "high",
        })

    if argument_analysis["evidence_count"] == 0:
        suggestions.append({
            "type": "argument",
            "message": "No evidence or citations detected. Support your claims with inline citations (e.g., Smith, 2020) or phrases like 'according to' and 'as shown by'.",
            "severity": "high",
        })
    elif argument_analysis["citation_count"] == 0 and argument_analysis["evidence_count"] > 0:
        suggestions.append({
            "type": "argument",
            "message": "Evidence phrases found but no formal citations detected. Add inline citations in a consistent format (e.g., APA: (Author, Year) or numbered: [1]).",
            "severity": "medium",
        })

    if argument_analysis["critical_analysis_count"] == 0:
        suggestions.append({
            "type": "argument",
            "message": "No critical engagement with prior work detected. Use phrases like 'building on', 'challenging', or 'extending' to show how your work relates to existing scholarship.",
            "severity": "medium",
        })

    if argument_analysis["perspective_balance"] in ["one-sided", "mostly one-sided"]:
        suggestions.append({
            "type": "argument",
            "message": f"Argument appears {argument_analysis['perspective_balance']}. Add more counterarguments and alternative perspectives to create a balanced scholarly debate.",
            "severity": "medium",
        })

    # Academic standards suggestions
    if standards_analysis["contraction_count"] > 0:
        suggestions.append({
            "type": "tone",
            "message": f"Found {standards_analysis['contraction_count']} contraction(s) ({', '.join(standards_analysis['contractions_found'][:5])}). Expand contractions to full forms (e.g., 'don't' → 'do not') for academic formality.",
            "severity": "medium",
        })

    if standards_analysis["informal_word_count"] > 0:
        suggestions.append({
            "type": "tone",
            "message": f"Found informal/colloquial language: {', '.join(standards_analysis['informal_words'][:5])}. Replace with formal academic equivalents.",
            "severity": "low",
        })

    if standards_analysis["first_person_count"] > 3:
        suggestions.append({
            "type": "tone",
            "message": f"Excessive first-person usage ({standards_analysis['first_person_count']} instances). Consider using third-person or objective phrasing (e.g., 'this study' instead of 'I').",
            "severity": "low",
        })

    # Overall assessment
    if flesch_reading_ease >= 60:
        readability_label = "Good"
    elif flesch_reading_ease >= 30:
        readability_label = "Moderate"
    else:
        readability_label = "Needs improvement"

    if academic_ratio >= 0.05:
        tone_label = "Strongly academic"
    elif academic_ratio >= 0.03:
        tone_label = "Academic"
    elif academic_ratio >= 0.01:
        tone_label = "Somewhat academic"
    else:
        tone_label = "Needs more academic vocabulary"

    return {
        "word_count": num_words,
        "sentence_count": num_sentences,
        "avg_sentence_length": round(avg_sentence_length, 1),
        "syllable_count": num_syllables,
        "complex_word_count": _count_complex_words(words),
        "passive_voice_count": passive_count,
        "long_sentences": long_sentences,
        "short_sentences": short_sentences,
        "academic_word_count": academic_word_count,
        "academic_ratio": round(academic_ratio * 100, 2),
        "transition_count": transition_count,
        "readability": {
            "flesch_reading_ease": round(flesch_reading_ease, 1),
            "flesch_grade_level": round(flesch_grade_level, 1),
            "gunning_fog_index": round(gunning_fog, 1),
            "label": readability_label,
        },
        "tone_assessment": tone_label,
        "structure": structure_analysis,
        "argument": argument_analysis,
        "academic_standards": standards_analysis,
        "suggestions": suggestions,
        "overall_score": _calculate_writing_score(
            flesch_reading_ease, passive_count, num_sentences,
            academic_ratio, transition_count, avg_sentence_length,
            structure_analysis["structure_score"],
            argument_analysis["argument_score"],
            standards_analysis["formal_tone_score"],
        ),
    }


# ---------------------------------------------------------------------------
# Structure & Heading Analysis
# ---------------------------------------------------------------------------

# Standard academic sections and their common heading variants
_ACADEMIC_SECTIONS = {
    "abstract": ["abstract", "executive summary"],
    "introduction": ["introduction", "background", "overview"],
    "literature_review": ["literature review", "review of literature", "related work",
                          "related literature", "prior research", "theoretical framework",
                          "conceptual framework"],
    "methodology": ["methodology", "methods", "research design", "research methodology",
                    "data and methods", "empirical strategy", "model specification",
                    "data collection", "sample and data"],
    "results": ["results", "findings", "empirical results", "analysis",
                "analytical results", "estimation results"],
    "discussion": ["discussion", "interpretation", "discussion of results",
                   "discussion of findings"],
    "conclusion": ["conclusion", "conclusions", "concluding remarks",
                   "summary and conclusion", "final remarks"],
    "references": ["references", "bibliography", "works cited", "reference list"],
    "acknowledgments": ["acknowledgments", "acknowledgements"],
    "appendix": ["appendix", "appendices"],
}


def _analyze_structure(text: str) -> dict:
    """
    Analyze document structure: headings, hierarchy, academic sections,
    and numbering format.
    """
    lines = text.split('\n')
    headings = []
    heading_issues = []

    # --- Detect headings ---
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        # Markdown headings: #, ##, ###, ####, #####
        md_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if md_match:
            level = len(md_match.group(1))
            heading_text = md_match.group(2).strip().rstrip('#').strip()
            headings.append({
                "level": level,
                "text": heading_text,
                "type": "markdown",
                "line": i + 1,
            })
            continue

        # Numbered headings: 1., 1.1., 1.1.1., 2., etc.
        num_match = re.match(r'^(\d+(?:\.\d+)*)\.?\s+(.+)$', stripped)
        if num_match:
            num_str = num_match.group(1)
            # Determine level by counting dots
            level = num_str.count('.') + 1
            heading_text = num_match.group(2).strip()
            # Only treat as heading if the text is short (< 100 chars) and not a full sentence
            if len(heading_text) < 100 and not heading_text.endswith('.'):
                headings.append({
                    "level": level,
                    "text": heading_text,
                    "type": "numbered",
                    "number": num_str,
                    "line": i + 1,
                })
                continue

        # Bold headings: **Text** or __Text__ on its own line (short, no period)
        bold_match = re.match(r'^\*\*(.+?)\*\*$', stripped)
        if bold_match:
            heading_text = bold_match.group(1).strip()
            if len(heading_text) < 100 and not heading_text.endswith('.'):
                headings.append({
                    "level": 2,  # Default bold to level 2
                    "text": heading_text,
                    "type": "bold",
                    "line": i + 1,
                })
                continue

        # ALL CAPS headings (short lines in all caps)
        if (len(stripped) < 80 and stripped.upper() == stripped
                and re.search(r'[A-Z]', stripped)
                and not stripped.endswith('.')
                and not re.match(r'^[A-Z]\s*$', stripped)):
            # Check if it looks like a heading (not just an acronym)
            if len(stripped.split()) <= 10:
                headings.append({
                    "level": 1,
                    "text": stripped,
                    "type": "caps",
                    "line": i + 1,
                })
                continue

    # --- Validate heading hierarchy ---
    has_hierarchy = len(headings) > 0
    prev_level = 0
    for h in headings:
        if prev_level > 0 and h["level"] > prev_level + 1:
            heading_issues.append(
                f"Heading level skipped: H{prev_level} → H{h['level']} at line {h['line']} "
                f"(\"{h['text']}\")"
            )
        prev_level = h["level"]

    # --- Detect numbering format ---
    numbering_format = "none"
    numbered_headings = [h for h in headings if h["type"] == "numbered"]
    if numbered_headings:
        # Check if decimal (1., 1.1., 1.1.1.) or simple (1., 2., 3.)
        has_multi_level = any(h["level"] > 1 for h in numbered_headings)
        if has_multi_level:
            numbering_format = "decimal"
        else:
            numbering_format = "simple"

        # Check consistency
        expected_num = 1
        top_level = [h for h in numbered_headings if h["level"] == 1]
        for h in top_level:
            try:
                actual = int(h["number"])
                if actual != expected_num:
                    heading_issues.append(
                        f"Numbering out of sequence: expected {expected_num}, "
                        f"got {actual} at line {h['line']}"
                    )
                expected_num = actual + 1
            except ValueError:
                pass

    # --- Detect academic sections ---
    sections_found = []
    sections_missing = []
    all_heading_text = " ".join(h["text"].lower() for h in headings)

    for section_key, variants in _ACADEMIC_SECTIONS.items():
        found = any(v in all_heading_text for v in variants)
        if found:
            sections_found.append(section_key.replace("_", " ").title())
        else:
            sections_missing.append(section_key.replace("_", " ").title())

    # Also check body text for section mentions (less reliable)
    text_lower = text.lower()
    if not any("abstract" in s.lower() for s in sections_found):
        if re.search(r'\babstract\b', text_lower[:500]):
            sections_found.append("Abstract (in body)")
            sections_missing = [s for s in sections_missing if not s.lower().startswith("abstract")]

    # --- Calculate structure score ---
    structure_score = 0
    if has_hierarchy:
        structure_score += 30
    if not heading_issues:
        structure_score += 20
    else:
        structure_score += max(0, 20 - len(heading_issues) * 5)
    if numbering_format != "none":
        structure_score += 15
    # Reward for having key academic sections
    key_sections = ["Introduction", "Literature Review", "Methodology", "Results",
                    "Discussion", "Conclusion"]
    found_count = sum(1 for ks in key_sections if any(ks.lower() in s.lower() for s in sections_found))
    structure_score += int((found_count / len(key_sections)) * 35)

    return {
        "headings": headings,
        "heading_count": len(headings),
        "has_hierarchy": has_hierarchy,
        "hierarchy_issues": heading_issues,
        "numbering_format": numbering_format,
        "numbering_consistent": len(heading_issues) == 0,
        "sections_found": sections_found,
        "sections_missing": sections_missing,
        "structure_score": max(0, min(100, structure_score)),
    }


# ---------------------------------------------------------------------------
# Argument & Debate Quality Analysis
# ---------------------------------------------------------------------------

# Thesis/claim statement indicators
_THESIS_INDICATORS = [
    "this study argues", "this paper argues", "this research argues",
    "this study examines", "this paper examines", "this research examines",
    "this study investigates", "this paper investigates",
    "this study explores", "this paper explores",
    "this study aims", "this paper aims", "this research aims",
    "this study seeks", "this paper seeks",
    "we hypothesize", "this study hypothesizes",
    "the objective of this study", "the purpose of this study",
    "the aim of this study", "the goal of this study",
    "this study addresses", "this paper addresses",
    "the central question", "the research question",
    "this study contends", "this paper contends",
    "this study demonstrates", "this paper demonstrates",
    "this study shows", "this paper shows",
    "this study finds", "this paper finds",
    "we argue that", "this article argues",
]

# Counterargument / debate markers
_COUNTERARGUMENT_MARKERS = [
    "however", "on the other hand", "in contrast", "conversely",
    "nevertheless", "nonetheless", "notwithstanding",
    "critics argue", "critics contend", "critics point out",
    "skeptics argue", "skeptics contend",
    "contrary to", "despite this", "despite the",
    "while some", "while others", "whereas",
    "alternative view", "alternative perspective",
    "detractors", "opposing view", "opposing argument",
    "challenges this", "challenges the",
    "questions this", "questions the",
    "contradicts", "disputes", "contests",
    "but critics", "but some scholars",
    "a competing", "an alternative explanation",
    "pushback", "counter-argument", "counterargument",
]

# Evidence/citation support patterns
_CITATION_PATTERNS = [
    (r'\([A-Z][a-z]+(?:\s+(?:et\s+al\.?|and|&)\s+[A-Z][a-z]+)?,?\s*\d{4}[a-z]?\)', "APA"),
    (r'\([A-Z][a-z]+\s+(?:et\s+al\.?|and|&)\s*\d{4}\)', "APA_et_al"),
    (r'\[\d+\]', "numbered"),
    (r'\[\d+(?:,\s*\d+)*\]', "numbered_multi"),
    (r'[A-Z][a-z]+\s+\(\d{4}\)', "narrative"),
    (r'[A-Z][a-z]+\s+et\s+al\.?\s+\(\d{4}\)', "narrative_et_al"),
]

# Evidence/support phrases
_EVIDENCE_PHRASES = [
    "according to", "as shown by", "as demonstrated by", "as evidenced by",
    "as reported by", "as found by", "as noted by", "as observed by",
    "in line with", "consistent with", "supporting the finding",
    "empirical evidence", "data show", "data shows", "data indicate",
    "results indicate", "results show", "results demonstrate",
    "findings suggest", "findings reveal", "findings indicate",
    "studies show", "studies indicate", "studies suggest",
    "research shows", "research indicates", "research suggests",
    "evidence suggests", "evidence shows", "evidence indicates",
]

# Critical analysis markers (engaging with and building on prior work)
_CRITICAL_ANALYSIS_MARKERS = [
    "building on", "extending", "challenging", "departing from",
    "diverging from", "complementing", "synthesizing", "reconciling",
    "in contrast to", "in disagreement with", "in extending",
    "advancing beyond", "moving beyond", "going beyond",
    "filling a gap", "addressing a gap", "bridging the gap",
    "contributing to", "adding to", "enhancing our understanding",
    "complicating the", "problematizing", "interrogating",
    "refining the", "reconceptualizing", "rethinking",
    "while acknowledging", "incorporating", "integrating",
    "drawing on", "leveraging", "adapting",
]


def _analyze_argument_quality(text: str, sentences: list, words: list) -> dict:
    """
    Analyze argument quality: thesis statements, counterarguments,
    evidence, critical analysis, and perspective balance.
    """
    text_lower = text.lower()

    # --- Detect thesis/claim statements ---
    thesis_indicators_found = []
    for indicator in _THESIS_INDICATORS:
        if indicator in text_lower:
            thesis_indicators_found.append(indicator)

    has_thesis = len(thesis_indicators_found) > 0

    # --- Detect counterarguments ---
    counterargument_markers_found = []
    for marker in _COUNTERARGUMENT_MARKERS:
        count = text_lower.count(marker)
        if count > 0:
            counterargument_markers_found.extend([marker] * count)

    counterargument_count = len(counterargument_markers_found)

    # --- Detect evidence/citations ---
    citation_matches = []
    citation_formats = set()
    for pattern, fmt in _CITATION_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            citation_matches.extend(matches)
            citation_formats.add(fmt)

    evidence_phrases_found = []
    for phrase in _EVIDENCE_PHRASES:
        count = text_lower.count(phrase)
        if count > 0:
            evidence_phrases_found.extend([phrase] * count)

    evidence_count = len(citation_matches) + len(evidence_phrases_found)

    # --- Detect critical analysis ---
    critical_markers_found = []
    for marker in _CRITICAL_ANALYSIS_MARKERS:
        count = text_lower.count(marker)
        if count > 0:
            critical_markers_found.extend([marker] * count)

    critical_analysis_count = len(critical_markers_found)

    # --- Assess perspective balance ---
    if counterargument_count == 0:
        perspective_balance = "one-sided"
    elif counterargument_count <= 2:
        perspective_balance = "mostly one-sided"
    elif counterargument_count <= 5:
        perspective_balance = "balanced"
    else:
        perspective_balance = "well-balanced"

    # --- Assess argument depth ---
    depth_score = 0
    if has_thesis:
        depth_score += 25
    if counterargument_count > 0:
        depth_score += min(25, counterargument_count * 8)
    if evidence_count > 0:
        depth_score += min(25, evidence_count * 5)
    if critical_analysis_count > 0:
        depth_score += min(25, critical_analysis_count * 8)

    if depth_score >= 70:
        argument_depth = "deep"
    elif depth_score >= 40:
        argument_depth = "moderate"
    elif depth_score >= 20:
        argument_depth = "limited"
    else:
        argument_depth = "shallow"

    # --- Determine primary citation format ---
    if citation_formats:
        if "APA" in citation_formats or "APA_et_al" in citation_formats:
            citation_format = "APA"
        elif "numbered" in citation_formats or "numbered_multi" in citation_formats:
            citation_format = "Numbered"
        elif "narrative" in citation_formats or "narrative_et_al" in citation_formats:
            citation_format = "Narrative APA"
        else:
            citation_format = list(citation_formats)[0]
    else:
        citation_format = "none"

    return {
        "has_thesis_statement": has_thesis,
        "thesis_indicators": thesis_indicators_found[:5],
        "counterargument_count": counterargument_count,
        "counterargument_markers": list(set(counterargument_markers_found))[:10],
        "evidence_count": evidence_count,
        "citation_count": len(citation_matches),
        "citation_format": citation_format,
        "evidence_phrases": list(set(evidence_phrases_found))[:10],
        "critical_analysis_count": critical_analysis_count,
        "critical_markers": list(set(critical_markers_found))[:10],
        "perspective_balance": perspective_balance,
        "argument_depth": argument_depth,
        "argument_score": max(0, min(100, depth_score)),
    }


# ---------------------------------------------------------------------------
# Academic Writing Standards Analysis
# ---------------------------------------------------------------------------

# Contractions to detect
_CONTRACTION_PATTERN = re.compile(
    r"\b(?:don't|doesn't|didn't|isn't|aren't|wasn't|weren't|haven't|hasn't|hadn't|"
    r"won't|wouldn't|can't|cannot|couldn't|shouldn't|it's|that's|there's|here's|"
    r"let's|they're|we're|you're|I'm|we've|they've|we'll|they'll|I've|I'll|I'd|"
    r"you'd|could've|should've|would've|might've|must've|who's|what's|where's|"
    r"when's|why's|how's)\b",
    re.IGNORECASE,
)

# Informal/colloquial words
_INFORMAL_WORDS = {
    "really", "very", "a lot", "lots of", "kind of", "sort of", "stuff",
    "things", "okay", "ok", "yeah", "nope", "yep", "gonna", "wanna", "gotta",
    "kids", "guy", "guys", "cool", "awesome", "great", "big", "huge",
    "tiny", "super", "totally", "basically", "literally", "obviously",
    "just", "pretty", "quite", "so", "too", "anyway", "anyways",
    "moreover", "lastly", "firstly", "secondly",
}

# Hedging language
_HEDGING_WORDS = [
    "may", "might", "could", "would", "should",
    "suggests", "suggesting", "suggest",
    "appears to", "appear to", "appears",
    "seems to", "seem to", "seems",
    "tends to", "tend to",
    "possibly", "likely", "perhaps", "probably", "potentially",
    "arguably", "presumably", "supposedly", "purportedly",
    "to some extent", "to a certain degree",
    "it is possible that", "it appears that", "it seems that",
    "there is evidence to suggest",
]

# First person pronouns
_FIRST_PERSON_PATTERN = re.compile(
    r'\b(?:I|we|our|ours|us|my|mine|myself)\b',
    re.IGNORECASE,
)


def _analyze_academic_standards(text: str, words: list) -> dict:
    """
    Analyze academic writing standards: formal tone, hedging,
    citation format, and first-person usage.
    """
    text_lower = text.lower()

    # --- Detect contractions ---
    contraction_matches = _CONTRACTION_PATTERN.findall(text)
    contractions_found = list(set(c.lower() for c in contraction_matches))

    # --- Detect informal words ---
    informal_words_found = []
    for word in words:
        if word.lower() in _INFORMAL_WORDS:
            informal_words_found.append(word.lower())
    informal_words_found = list(set(informal_words_found))

    # --- Detect hedging language ---
    hedging_found = []
    for hedge in _HEDGING_WORDS:
        count = text_lower.count(hedge)
        if count > 0:
            hedging_found.extend([hedge] * count)

    # --- Detect first-person usage ---
    first_person_matches = _FIRST_PERSON_PATTERN.findall(text)
    # Filter out "I" as part of citations like (Author, I.) or Roman numerals
    first_person_count = 0
    for match in first_person_matches:
        # Check context - skip if it's likely a citation or abbreviation
        idx = text.find(match)
        context_before = text[max(0, idx-5):idx]
        context_after = text[idx+len(match):idx+len(match)+5]
        if re.search(r'[,(]\s*$', context_before) or re.match(r'^\s*[.,)]', context_after):
            continue
        first_person_count += 1

    # --- Calculate formal tone score ---
    num_words = len(words) if words else 1
    tone_score = 100
    tone_score -= min(30, len(contraction_matches) * 10)
    tone_score -= min(20, len(informal_words_found) * 5)
    tone_score -= min(15, first_person_count * 3)

    # Hedging is good in moderation (academic caution)
    if len(hedging_found) == 0:
        tone_score -= 5  # Too confident, lacks academic hedging
    elif len(hedging_found) > num_words * 0.05:
        tone_score -= 10  # Too much hedging, appears uncertain
    else:
        tone_score += 5  # Appropriate hedging

    return {
        "contraction_count": len(contraction_matches),
        "contractions_found": contractions_found[:10],
        "informal_word_count": len(informal_words_found),
        "informal_words": informal_words_found[:10],
        "hedging_count": len(hedging_found),
        "hedging_words": list(set(hedging_found))[:10],
        "first_person_count": first_person_count,
        "formal_tone_score": max(0, min(100, tone_score)),
    }


def _count_syllables(word: str) -> int:
    """Estimate syllable count for a word."""
    word = word.lower()
    if len(word) <= 3:
        return 1
    # Remove silent 'e'
    if word.endswith('e'):
        word = word[:-1]
    # Count vowel groups
    vowels = "aeiouy"
    count = 0
    prev_was_vowel = False
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_was_vowel:
            count += 1
        prev_was_vowel = is_vowel
    return max(count, 1)


def _count_complex_words(words: list[str]) -> int:
    """Count words with 3+ syllables (for Gunning Fog)."""
    return sum(1 for w in words if _count_syllables(w) >= 3)


def _calculate_writing_score(flesch: float, passive: int, sentences: int,
                              academic_ratio: float, transitions: int,
                              avg_length: float,
                              structure_score: int = 0,
                              argument_score: int = 0,
                              formal_tone_score: int = 0) -> int:
    """
    Calculate an overall writing quality score (0-100).
    Combines readability, style, structure, argument, and tone.
    """
    # Base score from readability and style (max 55)
    style_score = 30  # Start at base

    # Readability (target: 30-60 for academic writing)
    if 30 <= flesch <= 60:
        style_score += 10
    elif 20 <= flesch <= 70:
        style_score += 5
    else:
        style_score -= 5

    # Passive voice (lower is better)
    if sentences > 0:
        passive_ratio = passive / sentences
        if passive_ratio < 0.15:
            style_score += 5
        elif passive_ratio < 0.3:
            style_score += 3
        else:
            style_score -= 5

    # Academic vocabulary
    if academic_ratio >= 0.05:
        style_score += 5
    elif academic_ratio >= 0.03:
        style_score += 3
    elif academic_ratio >= 0.01:
        style_score += 2

    # Transitions
    if sentences > 0:
        trans_ratio = transitions / sentences
        if trans_ratio >= 0.2:
            style_score += 5
        elif trans_ratio >= 0.1:
            style_score += 3
        else:
            style_score -= 3

    # Sentence length (ideal: 15-25 for academic)
    if 15 <= avg_length <= 25:
        style_score += 5
    elif 10 <= avg_length <= 30:
        style_score += 3
    else:
        style_score -= 3

    style_score = max(0, min(100, style_score))

    # Weighted combination:
    # Style/readability: 30%
    # Structure: 25%
    # Argument quality: 25%
    # Formal tone: 20%
    overall = (
        style_score * 0.30 +
        structure_score * 0.25 +
        argument_score * 0.25 +
        formal_tone_score * 0.20
    )

    return max(0, min(100, round(overall)))


# ---------------------------------------------------------------------------
# Writing Enhancement Suggestions
# ---------------------------------------------------------------------------

def enhance_for_journal(text: str, journal_name: str = None) -> dict:
    """
    Provide targeted suggestions for journal submission readiness.
    """
    analysis = analyze_writing(text)
    if "error" in analysis:
        return analysis

    journal_specific = []

    # Journal-specific checks
    if journal_name:
        journal_name_lower = journal_name.lower()
        if "economic" in journal_name_lower:
            journal_specific.extend([
                "Ensure all economic terms are used correctly (e.g., 'endogeneity', 'causality')",
                "Include robustness checks and mention them in the text",
                "Use standard notation for regression equations",
            ])
        if "systems" in journal_name_lower:
            journal_specific.extend([
                "Emphasize systemic approaches and institutional frameworks",
                "Consider cross-country comparative analysis",
            ])

    readiness_checks = [
        {"check": "Word count adequate (>3000 for full papers)", "passed": analysis["word_count"] >= 3000},
        {"check": "Readable sentence structure", "passed": 10 <= analysis["avg_sentence_length"] <= 25},
        {"check": "Academic tone maintained", "passed": analysis["academic_ratio"] >= 0.02},
        {"check": "Sufficient transitions for flow", "passed": analysis["transition_count"] >= analysis["sentence_count"] * 0.15},
        {"check": "Low passive voice usage", "passed": analysis["passive_voice_count"] < analysis["sentence_count"] * 0.3},
        {"check": "Readability within academic range", "passed": 20 <= analysis["readability"]["flesch_reading_ease"] <= 60},
    ]

    passed_count = sum(1 for c in readiness_checks if c["passed"])
    total_checks = len(readiness_checks)
    readiness_score = round((passed_count / total_checks) * 100)

    return {
        "analysis": analysis,
        "readiness_checks": readiness_checks,
        "readiness_score": readiness_score,
        "ready_for_submission": readiness_score >= 70,
        "journal_specific_suggestions": journal_specific,
        "recommended_tools": _recommend_tools(analysis),
    }


def _recommend_tools(analysis: dict) -> list[dict]:
    """Recommend writing tools based on analysis results."""
    recommendations = []

    # Always recommend Grammarly for grammar
    recommendations.append({
        "tool": "grammarly",
        "reason": "Check grammar, spelling, and punctuation before submission",
        "priority": "high",
    })

    # Recommend QuillBot for paraphrasing if passive voice is high
    if analysis.get("passive_voice_count", 0) > 5:
        recommendations.append({
            "tool": "quillbot",
            "reason": "Use Academic mode to reduce passive voice and improve sentence structure",
            "priority": "medium",
        })

    # Recommend Paperpal for academic tone
    if analysis.get("academic_ratio", 0) < 0.03:
        recommendations.append({
            "tool": "paperpal",
            "reason": "Enhance academic vocabulary and subject-specific writing",
            "priority": "high",
        })

    # Recommend QuillBot for long sentences
    if analysis.get("avg_sentence_length", 0) > 25:
        recommendations.append({
            "tool": "quillbot",
            "reason": "Use summarizer or paraphraser to break up long sentences",
            "priority": "medium",
        })

    return recommendations


# ---------------------------------------------------------------------------
# Inline Text Enhancement Engine
# Works directly on the platform — no external redirects needed.
# Three modes modeled after Grammarly, QuillBot, and Paperpal.
# ---------------------------------------------------------------------------

# --- Grammarly-style: Grammar & Spelling Fixer ---

# Common spelling corrections
_SPELLING_FIXES = {
    "recieve": "receive", "recieved": "received", "recieving": "receiving",
    "seperate": "separate", "seperated": "separated", "seperately": "separately",
    "definately": "definitely", "definatly": "definitely",
    "occured": "occurred", "occuring": "occurring", "occurence": "occurrence",
    "untill": "until", "wich": "which", "thier": "their", "thay": "they",
    "teh": "the", "adn": "and", "nad": "and", "taht": "that",
    "witht he": "with the", "tobe": "to be", "inthe": "in the",
    "ofthe": "of the", "tothe": "to the", "onthe": "on the",
    "forthe": "for the", "andthe": "and the", "isthe": "is the",
    "achive": "achieve", "achived": "achieved", "achivement": "achievement",
    "begining": "beginning", "belive": "believe", "calender": "calendar",
    "cemetarey": "cemetery", "changable": "changeable", "collegue": "colleague",
    "comming": "coming", "commitee": "committee", "completly": "completely",
    "concious": "conscious", "curiousity": "curiosity", "dissapear": "disappear",
    "dissapoint": "disappoint", "embarass": "embarrass", "enviroment": "environment",
    "existance": "existence", "familar": "familiar", "finaly": "finally",
    "flourescent": "fluorescent", "foriegn": "foreign", "freind": "friend",
    "goverment": "government", "gramar": "grammar", "guarentee": "guarantee",
    "happend": "happened", "harras": "harass", "heirarchy": "hierarchy",
    "humourous": "humorous", "hygeine": "hygiene", "immediatly": "immediately",
    "independant": "independent", "knowlege": "knowledge", "liason": "liaison",
    "libary": "library", "licence": "license", "maintainance": "maintenance",
    "managable": "manageable", "millenium": "millennium", "miniscule": "minuscule",
    "mischievous": "mischievous", "noticable": "noticeable", "occassion": "occasion",
    "persistant": "persistent", "posession": "possession", "prefered": "preferred",
    "priviledge": "privilege", "probaly": "probably", "publically": "publicly",
    "que": "queue", "readible": "readable", "realy": "really",
    "recomend": "recommend", "relevent": "relevant", "religous": "religious",
    "repetion": "repetition", "rythm": "rhythm", "secretery": "secretary",
    "similiar": "similar", "sincerly": "sincerely", "speach": "speech",
    "succesful": "successful", "suprise": "surprise", "tendancy": "tendency",
    "tommorow": "tomorrow", "truely": "truly", "unfortunatly": "unfortunately",
    "wether": "whether", "writting": "writing",
}

# Informal -> academic word replacements
_ACADEMIC_UPGRADES = {
    "get": "obtain", "gets": "obtains", "got": "obtained", "getting": "obtaining",
    "show": "demonstrate", "shows": "demonstrates", "showed": "demonstrated",
    "showing": "demonstrating", "shown": "demonstrated",
    "use": "employ", "uses": "employs", "used": "employed", "using": "employing",
    "make": "render", "makes": "renders", "made": "rendered", "making": "rendering",
    "big": "substantial", "bigger": "more substantial", "biggest": "most substantial",
    "small": "marginal", "smaller": "more marginal", "smallest": "most marginal",
    "important": "significant", "really": "particularly",
    "very": "notably", "a lot of": "numerous", "lots of": "numerous",
    "kind of": "somewhat", "sort of": "somewhat",
    "find out": "ascertain", "finds out": "ascertains", "found out": "ascertained",
    "look at": "examine", "looks at": "examines", "looked at": "examined",
    "look into": "investigate", "looks into": "investigates", "looked into": "investigated",
    "think": "posit", "thinks": "posits", "thought": "posited",
    "agree": "concur", "agrees": "concurs", "agreed": "concurred",
    "start": "commence", "starts": "commences", "started": "commenced",
    "end": "conclude", "ends": "concludes", "ended": "concluded",
    "help": "facilitate", "helps": "facilitates", "helped": "facilitated",
    "try": "attempt", "tries": "attempts", "tried": "attempted",
    "change": "modification", "changes": "modifications", "changed": "modified",
    "point out": "highlight", "points out": "highlights", "pointed out": "highlighted",
    "come up with": "propose", "comes up with": "proposes", "came up with": "proposed",
    "deal with": "address", "deals with": "addresses", "dealt with": "addressed",
    "bring up": "raise", "brings up": "raises", "brought up": "raised",
    "cut down": "reduce", "cuts down": "reduces", "cut down": "reduced",
    "findings are": "findings indicate", "results are": "results indicate",
}

# Weak phrases -> stronger academic equivalents
_WEAK_PHRASES = {
    "i think": "it can be argued that",
    "i believe": "the evidence suggests that",
    "in my opinion": "from a scholarly perspective",
    "this paper will look at": "this study examines",
    "this paper looks at": "this study examines",
    "this paper is about": "this study investigates",
    "as everyone knows": "it is widely acknowledged that",
    "everyone knows that": "it is well established that",
    "people say that": "scholars contend that",
    "many people think": "a consensus exists among scholars that",
    "nowadays": "in recent years",
    "in today's world": "in the contemporary context",
    "since the beginning of time": "historically",
    "throughout history": "historically",
}


def fix_grammar(text: str) -> dict:
    """
    Grammarly-style grammar and spelling fixer.
    Detects and corrects common errors, returning the fixed text
    along with a list of changes made.
    """
    if not text or len(text.strip()) < 5:
        return {"original": text, "enhanced": text, "changes": [],
                "summary": "Text too short for grammar analysis."}

    original = text
    changes = []

    # 1. Fix double spaces
    while "  " in text:
        text = text.replace("  ", " ")
        if "  " not in text:
            changes.append({"type": "spacing", "original": "double space",
                            "fixed": "single space", "category": "grammar"})

    # 2. Fix missing space after punctuation
    fixed_punct = re.sub(r'([,.!?;:])([A-Za-z])', r'\1 \2', text)
    if fixed_punct != text:
        changes.append({"type": "punctuation_spacing",
                        "original": "missing space after punctuation",
                        "fixed": "added space after punctuation", "category": "grammar"})
        text = fixed_punct

    # 3. Fix space before punctuation
    fixed_pre_punct = re.sub(r'\s+([,.!?;:])', r'\1', text)
    if fixed_pre_punct != text:
        changes.append({"type": "punctuation_spacing",
                        "original": "space before punctuation",
                        "fixed": "removed space before punctuation", "category": "grammar"})
        text = fixed_pre_punct

    # 4. Capitalize first letter of each sentence
    def _capitalize_sentence(match):
        prefix = match.group(1)
        first_char = match.group(2)
        if first_char.islower():
            return prefix + first_char.upper()
        return match.group(0)

    capitalized = re.sub(r'(^|[.!?]\s+)([a-z])', _capitalize_sentence, text)
    if capitalized != text:
        changes.append({"type": "capitalization",
                        "original": "lowercase at sentence start",
                        "fixed": "capitalized first letter", "category": "grammar"})
        text = capitalized

    # 5. Fix spelling errors (case-insensitive, preserve case)
    words = re.findall(r'\b[A-Za-z]+\b', text)
    for word in words:
        lower = word.lower()
        if lower in _SPELLING_FIXES:
            correct = _SPELLING_FIXES[lower]
            # Preserve capitalization
            if word[0].isupper():
                correct = correct[0].upper() + correct[1:]
            pattern = r'\b' + re.escape(word) + r'\b'
            new_text = re.sub(pattern, correct, text)
            if new_text != text:
                changes.append({"type": "spelling", "original": word,
                                "fixed": correct, "category": "grammar"})
                text = new_text

    # 6. Fix "a" vs "an" before words
    def _fix_article(match):
        article = match.group(1)
        word = match.group(2)
        if not word:
            return match.group(0)
        first_letter = word[0].lower()
        needs_an = first_letter in "aeiou"
        # Check for silent h
        if word.lower().startswith("hour") or word.lower().startswith("honest"):
            needs_an = True
        # Check for vowel sound with consonant (e.g., "university" -> "a")
        if word.lower().startswith(("uni", "use", "eu", "one", "once")):
            needs_an = False

        correct_article = "an" if needs_an else "a"
        if article.lower() == "a" and needs_an:
            changes.append({"type": "article", "original": f"{article} {word}",
                            "fixed": f"an {word}", "category": "grammar"})
            return f"an {word}"
        elif article.lower() == "an" and not needs_an:
            changes.append({"type": "article", "original": f"{article} {word}",
                            "fixed": f"a {word}", "category": "grammar"})
            return f"a {word}"
        return match.group(0)

    # Apply article fixes (but avoid adding duplicate changes)
    prev_changes = len(changes)
    text = re.sub(r'\b([Aa])n?\s+([A-Za-z]+)', _fix_article, text)
    # Deduplicate article changes
    if len(changes) > prev_changes:
        seen = set()
        unique = []
        for c in changes:
            key = (c.get("original"), c.get("fixed"))
            if key not in seen:
                seen.add(key)
                unique.append(c)
        changes = unique

    # 7. Fix repeated words (e.g., "the the")
    repeated = re.sub(r'\b(\w+)(\s+\1\b)+', r'\1', text, flags=re.IGNORECASE)
    if repeated != text:
        changes.append({"type": "repetition", "original": "repeated word",
                        "fixed": "removed duplicate", "category": "grammar"})
        text = repeated

    # 8. Ensure sentence ends with punctuation
    stripped = text.rstrip()
    if stripped and stripped[-1] not in '.!?:"\')':
        text = stripped + "."
        changes.append({"type": "punctuation", "original": "missing end punctuation",
                        "fixed": "added period", "category": "grammar"})

    # 9. Fix comma splice: "word,word" -> "word, word"
    fixed_comma = re.sub(r',([A-Za-z])', r', \1', text)
    if fixed_comma != text:
        changes.append({"type": "punctuation_spacing",
                        "original": "missing space after comma",
                        "fixed": "added space after comma", "category": "grammar"})
        text = fixed_comma

    if text == original:
        summary = "No grammar issues found. Your text looks clean."
    else:
        summary = f"Fixed {len(changes)} grammar issue(s)."

    return {
        "original": original,
        "enhanced": text,
        "changes": changes,
        "summary": summary,
    }


def paraphrase_text(text: str) -> dict:
    """
    QuillBot-style paraphraser.
    Rewrites sentences for clarity, converts passive to active voice,
    and strengthens sentence structure.
    """
    if not text or len(text.strip()) < 20:
        return {"original": text, "enhanced": text, "changes": [],
                "summary": "Text too short for paraphrasing."}

    original = text
    changes = []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    paraphrased_sentences = []

    for sentence in sentences:
        s = sentence.strip()
        if not s:
            paraphrased_sentences.append(s)
            continue

        original_s = s

        # 1. Convert passive voice to active where possible
        # Pattern: "X is/are/was/were verb-ed by Y" -> "Y verb-ed X"
        passive_patterns = [
            (r'\b([A-Za-z\s]+?)\s+(?:is|are|was|were)\s+(\w+ed)\s+by\s+([A-Za-z\s]+?)([.,;:])',
             r'\3 \2 \1\4'),
            (r'\b([A-Za-z\s]+?)\s+(?:is|are|was|were)\s+(\w+ed)\s+by\s+([A-Za-z\s]+)$',
             r'\3 \2 \1'),
        ]
        for pattern, replacement in passive_patterns:
            new_s = re.sub(pattern, replacement, s, flags=re.IGNORECASE)
            if new_s != s:
                changes.append({"type": "passive_to_active", "original": original_s,
                                "fixed": new_s, "category": "paraphrase"})
                s = new_s
                break

        # 2. Replace wordy phrases with concise alternatives
        wordy_replacements = {
            r'\bdue to the fact that\b': "because",
            r'\bin spite of the fact that\b': "although",
            r'\bin the event that\b': "if",
            r'\bat this point in time\b': "currently",
            r'\bin the process of\b': "during",
            r'\bwith regard to\b': "regarding",
            r'\bin order to\b': "to",
            r'\bfor the purpose of\b': "for",
            r'\bin the majority of cases\b': "usually",
            r'\ba large number of\b': "many",
            r'\ba small number of\b': "few",
            r'\bthe majority of\b': "most",
            r'\bhas the ability to\b': "can",
            r'\bhas the capacity to\b': "can",
            r'\bis able to\b': "can",
            r'\bare able to\b': "can",
            r'\bit is important to note that\b': "notably,",
            r'\bit should be noted that\b': "notably,",
            r'\bit is worth noting that\b': "notably,",
            r'\bthere is a need to\b': "must",
            r'\bthere is a tendency for\b': "tends to",
            r'\bplays a role in\b': "contributes to",
            r'\bplays an important role in\b': "significantly contributes to",
            r'\bmake a decision\b': "decide",
            r'\bmake a contribution\b': "contribute",
            r'\bconduct an investigation\b': "investigate",
            r'\bperform an analysis\b': "analyze",
            r'\bcarry out a study\b': "study",
        }
        for pattern, replacement in wordy_replacements.items():
            new_s = re.sub(pattern, replacement, s, flags=re.IGNORECASE)
            if new_s != s:
                if original_s not in [c.get("original") for c in changes if c["type"] == "passive_to_active"]:
                    changes.append({"type": "conciseness", "original": original_s,
                                    "fixed": new_s, "category": "paraphrase"})
                s = new_s

        # 3. Split overly long sentences (>30 words) at conjunctions
        words_in_s = s.split()
        if len(words_in_s) > 30:
            # Try splitting at "and" or "but" or "however"
            for conj in [r'\s+and\s+', r'\s+but\s+', r'\s+however,\s+', r'\s+therefore,\s+']:
                parts = re.split(conj, s, maxsplit=1, flags=re.IGNORECASE)
                if len(parts) == 2 and len(parts[0].split()) > 10 and len(parts[1].split()) > 10:
                    conj_word = re.search(conj, s, re.IGNORECASE)
                    if conj_word:
                        actual_conj = conj_word.group(0).strip().rstrip(',')
                        new_s = parts[0].strip() + ". " + actual_conj.capitalize() + " " + parts[1].strip()
                        if not new_s.endswith('.'):
                            new_s += '.'
                        changes.append({"type": "sentence_split", "original": original_s,
                                        "fixed": new_s, "category": "paraphrase"})
                        s = new_s
                        break

        # 4. Vary sentence beginnings - replace "This study" overuse
        if s.lower().startswith("this study") and sum(1 for ps in paraphrased_sentences if ps.lower().startswith("this study")) > 0:
            alternatives = ["The present research", "The current investigation", "This analysis", "The present work"]
            idx = len(paraphrased_sentences) % len(alternatives)
            new_s = re.sub(r'^[Tt]his\s+study', alternatives[idx], s)
            if new_s != s:
                changes.append({"type": "sentence_variation", "original": original_s,
                                "fixed": new_s, "category": "paraphrase"})
                s = new_s

        paraphrased_sentences.append(s)

    enhanced = " ".join(paraphrased_sentences)

    if enhanced == original:
        summary = "No paraphrasing improvements needed. Your sentences are clear."
    else:
        summary = f"Made {len(changes)} paraphrasing improvement(s) for clarity and conciseness."

    return {
        "original": original,
        "enhanced": enhanced,
        "changes": changes,
        "summary": summary,
    }


def enhance_academic(text: str) -> dict:
    """
    Paperpal-style academic tone enhancer.
    Upgrades informal vocabulary to scholarly equivalents,
    adds transition words, and strengthens academic register.
    """
    if not text or len(text.strip()) < 20:
        return {"original": text, "enhanced": text, "changes": [],
                "summary": "Text too short for academic enhancement."}

    original = text
    changes = []
    enhanced = text

    # 1. Replace weak/informal phrases with academic equivalents
    for informal, academic in _WEAK_PHRASES.items():
        pattern = re.compile(re.escape(informal), re.IGNORECASE)
        if pattern.search(enhanced):
            # Preserve capitalization of first letter
            match = pattern.search(enhanced)
            replacement = academic
            if match.group(0)[0].isupper():
                replacement = replacement[0].upper() + replacement[1:]
            enhanced = pattern.sub(replacement, enhanced)
            changes.append({"type": "phrase_upgrade", "original": informal,
                            "fixed": academic, "category": "academic"})

    # 2. Replace informal words with academic vocabulary
    words = re.findall(r'\b[A-Za-z]+(?:\s+[A-Za-z]+)?\b', enhanced)
    for word in words:
        lower = word.lower()
        if lower in _ACADEMIC_UPGRADES:
            upgrade = _ACADEMIC_UPGRADES[lower]
            # Preserve capitalization
            if word[0].isupper():
                upgrade = upgrade[0].upper() + upgrade[1:]
            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            new_enhanced = pattern.sub(upgrade, enhanced, count=1)
            if new_enhanced != enhanced:
                changes.append({"type": "vocabulary_upgrade", "original": word,
                                "fixed": upgrade, "category": "academic"})
                enhanced = new_enhanced

    # 3. Add transition words between sentences where missing
    sentences = re.split(r'(?<=[.!?])\s+', enhanced)
    transitions_map = {
        "contrast": ["However", "Nevertheless", "In contrast", "Conversely"],
        "addition": ["Furthermore", "Moreover", "Additionally", "In addition"],
        "causation": ["Consequently", "Therefore", "As a result", "Thus"],
        "sequence": ["Subsequently", "Thereafter", "Following this", "Next"],
    }

    # Detect if consecutive sentences lack transitions
    transition_indicators = set()
    for vals in transitions_map.values():
        transition_indicators.update(v.lower() for v in vals)
    transition_indicators.update(["however", "therefore", "moreover", "furthermore",
                                   "consequently", "additionally", "subsequently",
                                   "thus", "hence", "nevertheless", "accordingly",
                                   "in addition", "in contrast", "as a result"])

    enhanced_sentences = []
    for i, sentence in enumerate(sentences):
        s = sentence.strip()
        if not s:
            enhanced_sentences.append(s)
            continue

        if i > 0:
            first_word = s.split()[0].lower() if s.split() else ""
            if first_word not in transition_indicators and not any(
                s.lower().startswith(t) for t in transition_indicators
            ):
                # Add a transition based on position
                category_idx = i % 4
                category = list(transitions_map.keys())[category_idx]
                transition = transitions_map[category][i % len(transitions_map[category])]
                # Don't add transition to very short sentences or headings
                if len(s.split()) > 5 and not s.startswith("#") and not s.startswith("**"):
                    new_s = f"{transition}, {s[0].lower()}{s[1:]}"
                    changes.append({"type": "transition_added", "original": s,
                                    "fixed": new_s, "category": "academic"})
                    s = new_s

        enhanced_sentences.append(s)

    enhanced = " ".join(enhanced_sentences)

    # 4. Replace contractions with full forms
    contractions = {
        r"\bdon't\b": "do not", r"\bdoesn't\b": "does not",
        r"\bdidn't\b": "did not", r"\bisn't\b": "is not",
        r"\baren't\b": "are not", r"\bwasn't\b": "was not",
        r"\bweren't\b": "were not", r"\bhaven't\b": "have not",
        r"\bhasn't\b": "has not", r"\bhadn't\b": "had not",
        r"\bwon't\b": "will not", r"\bwouldn't\b": "would not",
        r"\bcan't\b": "cannot", r"\bcannot\b": "cannot",
        r"\bcouldn't\b": "could not", r"\bshouldn't\b": "should not",
        r"\bit's\b": "it is", r"\bthat's\b": "that is",
        r"\bthere's\b": "there is", r"\bhere's\b": "here is",
        r"\blet's\b": "let us", r"\bthey're\b": "they are",
        r"\bwe're\b": "we are", r"\byou're\b": "you are",
        r"\bI'm\b": "I am", r"\bwe've\b": "we have",
        r"\bthey've\b": "they have", r"\bit've\b": "it has",
        r"\bwe'll\b": "we will", r"\bthey'll\b": "they will",
        r"\bI've\b": "I have", r"\bI'll\b": "I will",
        r"\bI'd\b": "I would", r"\byou'd\b": "you would",
    }
    for pattern, replacement in contractions.items():
        if re.search(pattern, enhanced, re.IGNORECASE):
            new_enhanced = re.sub(pattern, replacement, enhanced, flags=re.IGNORECASE)
            if new_enhanced != enhanced:
                changes.append({"type": "contraction_fix",
                                "original": "contraction",
                                "fixed": "expanded form", "category": "academic"})
                enhanced = new_enhanced

    # 5. Replace "I" statements with more objective phrasing
    first_person_fixes = {
        r'\bI argue\b': "this study argues",
        r'\bI argue that\b': "this study argues that",
        r'\bI show\b': "this study demonstrates",
        r'\bI show that\b': "this study demonstrates that",
        r'\bI find\b': "the findings reveal",
        r'\bI find that\b': "the findings reveal that",
        r'\bI demonstrate\b': "this research demonstrates",
        r'\bI demonstrate that\b': "this research demonstrates that",
        r'\bI propose\b': "this study proposes",
        r'\bI propose that\b': "this study proposes that",
        r'\bI conclude\b': "this study concludes",
        r'\bI conclude that\b': "this study concludes that",
        r'\bI examine\b': "this study examines",
        r'\bI analyze\b': "this analysis examines",
        r'\bwe argue\b': "this study argues",
        r'\bwe show\b': "this study demonstrates",
        r'\bwe find\b': "the findings reveal",
    }
    for pattern, replacement in first_person_fixes.items():
        if re.search(pattern, enhanced, re.IGNORECASE):
            new_enhanced = re.sub(pattern, replacement, enhanced, flags=re.IGNORECASE)
            if new_enhanced != enhanced:
                changes.append({"type": "objectivity", "original": "first-person statement",
                                "fixed": "objective phrasing", "category": "academic"})
                enhanced = new_enhanced

    if enhanced == original:
        summary = "Your text already maintains a strong academic register."
    else:
        summary = f"Made {len(changes)} academic enhancement(s) to improve tone and register."

    return {
        "original": original,
        "enhanced": enhanced,
        "changes": changes,
        "summary": summary,
    }


def enhance_text_all(text: str) -> dict:
    """
    Apply all three enhancement tools in sequence:
    1. Grammar fix (Grammarly-style)
    2. Paraphrase (QuillBot-style)
    3. Academic enhancement (Paperpal-style)
    Returns the fully enhanced text with all changes.
    """
    if not text or len(text.strip()) < 5:
        return {"original": text, "enhanced": text, "all_changes": [],
                "grammar": None, "paraphrase": None, "academic": None,
                "summary": "Text too short for enhancement."}

    # Step 1: Grammar fix
    grammar_result = fix_grammar(text)
    step1_text = grammar_result["enhanced"]

    # Step 2: Paraphrase
    paraphrase_result = paraphrase_text(step1_text)
    step2_text = paraphrase_result["enhanced"]

    # Step 3: Academic enhancement
    academic_result = enhance_academic(step2_text)
    final_text = academic_result["enhanced"]

    all_changes = (
        grammar_result.get("changes", []) +
        paraphrase_result.get("changes", []) +
        academic_result.get("changes", [])
    )

    total = len(all_changes)
    summary = (
        f"Applied {total} total enhancement(s): "
        f"{len(grammar_result.get('changes', []))} grammar fix(es), "
        f"{len(paraphrase_result.get('changes', []))} paraphrase improvement(s), "
        f"{len(academic_result.get('changes', []))} academic enhancement(s)."
    )

    return {
        "original": text,
        "enhanced": final_text,
        "all_changes": all_changes,
        "grammar": grammar_result,
        "paraphrase": paraphrase_result,
        "academic": academic_result,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# Humanize & Naturalize Engine
# Reduces formulaic AI patterns and produces more natural, varied prose.
# Improves readability and authentic voice while preserving academic meaning.
# ---------------------------------------------------------------------------

# Overused AI transition words -> natural alternatives (rotated for variety)
_AI_TRANSITION_REPLACEMENTS = {
    "furthermore": ["additionally", "in addition", "what is more", "beyond this"],
    "moreover": ["additionally", "further", "beyond that", "what is more"],
    "additionally": ["furthermore", "in addition", "also", "beyond this"],
    "consequently": ["as a result", "for this reason", "thus", "which led to"],
    "subsequently": ["afterward", "later", "following this", "in turn"],
    "nevertheless": ["even so", "still", "yet", "despite this"],
    "nonetheless": ["even so", "still", "yet", "all the same"],
    "therefore": ["as a result", "for this reason", "thus", "so"],
    "thus": ["as a result", "in this way", "so", "which means"],
    "hence": ["as a result", "for this reason", "so", "which means"],
    "accordingly": ["as a result", "in response", "so", "which led to"],
    "notably": ["in particular", "worth noting", "significantly", "of note"],
    "specifically": ["in particular", "notably", "that is", "to be precise"],
    "particularly": ["especially", "in particular", "notably", "above all"],
    "essentially": ["fundamentally", "at its core", "in essence", "basically"],
    "fundamentally": ["at its core", "in essence", "essentially", "at bottom"],
    "predominantly": ["mainly", "largely", "chiefly", "primarily"],
    "it is important to note that": ["it is worth noting that", "of note,", "importantly,", "key to this is that"],
    "it is worth noting that": ["of note,", "importantly,", "it should be mentioned that", "notably,"],
    "it should be noted that": ["of note,", "importantly,", "it is worth mentioning that", "notably,"],
    "in conclusion": ["to conclude", "in sum", "overall", "taken together"],
    "in summary": ["to summarize", "in sum", "overall", "taken together"],
    "as a result": ["consequently", "which led to", "so", "for this reason"],
    "on the other hand": ["conversely", "by contrast", "alternatively", "then again"],
    "in addition": ["additionally", "furthermore", "also", "beyond this"],
}

# Formulaic AI sentence starters -> natural alternatives
_AI_STARTER_VARIATIONS = {
    "this study": ["the present research", "this analysis", "the current investigation", "the present work", "our examination"],
    "this paper": ["the present study", "this analysis", "the current work", "this research", "our investigation"],
    "this research": ["the present study", "this analysis", "the current investigation", "this work", "our research"],
    "this analysis": ["the present study", "this examination", "the current research", "our analysis", "this investigation"],
    "these findings": ["the results", "these results", "the outcomes", "what the data show", "the evidence"],
    "the results show": ["the findings indicate", "the data reveal", "the evidence demonstrates", "the results indicate", "the analysis reveals"],
    "the findings reveal": ["the results indicate", "the data show", "the evidence suggests", "the analysis reveals", "the outcomes demonstrate"],
    "this study examines": ["the present research examines", "this analysis investigates", "the current study explores", "our investigation examines", "this work explores"],
    "this study investigates": ["the present research explores", "this analysis examines", "the current investigation studies", "our work investigates", "this research examines"],
    "this study aims": ["the present research aims", "this analysis seeks", "the current investigation aims", "our study seeks", "this work aims"],
}

# Repetitive AI phrases -> natural alternatives
_AI_PHRASE_REPLACEMENTS = {
    r"\bplays a (?:crucial|vital|pivotal|critical|key) role in\b": ["is central to", "is essential to", "is integral to", "is fundamental to"],
    r"\bplays a significant role in\b": ["contributes significantly to", "is important for", "meaningfully shapes", "substantially influences"],
    r"\bis of paramount importance\b": ["is critically important", "is essential", "is crucial", "matters greatly"],
    r"\bis of great significance\b": ["is significant", "matters considerably", "is important", "carries weight"],
    r"\bhas attracted considerable attention\b": ["has drawn significant interest", "has garnered attention", "has become a focus of interest", "has attracted much scrutiny"],
    r"\bhas gained increasing attention\b": ["has drawn growing interest", "has become increasingly scrutinized", "has attracted more focus", "has gained traction"],
    r"\bin the realm of\b": ["in the field of", "within", "in the domain of", "in the area of"],
    r"\ba growing body of literature\b": ["an expanding literature", "increasing scholarship", "a widening body of research", "mounting evidence"],
    r"\bshed light on\b": ["illuminate", "clarify", "explain", "elucidate"],
    r"\bsheds light on\b": ["illuminates", "clarifies", "explains", "elucidates"],
    r"\bpave the way for\b": ["enable", "facilitate", "open possibilities for", "create the foundation for"],
    r"\bpaves the way for\b": ["enables", "facilitates", "opens possibilities for", "creates the foundation for"],
    r"\bin recent years\b": ["lately", "recently", "of late", "in the past decade"],
    r"\bremains a topic of debate\b": ["is still debated", "continues to be contested", "remains unsettled", "is an open question"],
    r"\bremains largely unexplored\b": ["has received little attention", "is not well understood", "has not been closely examined", "warrants further study"],
    r"\bwarrants further investigation\b": ["deserves more study", "calls for closer examination", "merits additional research", "needs further exploration"],
    r"\bbridge the gap between\b": ["connect", "link", "reconcile", "unite"],
    r"\bbridges the gap between\b": ["connects", "links", "reconciles", "unites"],
    r"\bdelve into\b": ["examine closely", "explore", "investigate", "analyze"],
    r"\bdelves into\b": ["examines closely", "explores", "investigates", "analyzes"],
    r"\b underscore[s]? the importance of\b": ["highlight the importance of", "emphasize the significance of", "draw attention to the importance of", "stress the need for"],
    r"\bholds true for\b": ["applies to", "is valid for", "is the case for", "extends to"],
    r"\bit is widely acknowledged that\b": ["it is well known that", "scholars generally agree that", "it is broadly recognized that", "there is broad consensus that"],
    r"\bit is well established that\b": ["research has shown that", "evidence confirms that", "it is widely accepted that", "scholars have demonstrated that"],
    r"\bremains an open question\b": ["is still unresolved", "has yet to be settled", "is not fully answered", "continues to be debated"],
}

# Patterns that indicate AI-generated text
_AI_PATTERN_INDICATORS = [
    "it is important to note that",
    "it is worth noting that",
    "it should be noted that",
    "plays a crucial role",
    "plays a vital role",
    "plays a pivotal role",
    "a growing body of literature",
    "shed light on",
    "pave the way for",
    "bridge the gap",
    "delve into",
    "in the realm of",
    "has attracted considerable attention",
    "has gained increasing attention",
    "remains largely unexplored",
    "warrants further investigation",
    "is of paramount importance",
]


def humanize_text(text: str) -> dict:
    """
    Humanize and naturalize text by reducing formulaic AI patterns.

    This function improves writing quality by:
    1. Reducing overused AI transition words (Furthermore, Moreover, etc.)
    2. Varying sentence beginnings to break repetitive patterns
    3. Replacing formulaic AI phrases with natural alternatives
    4. Varying sentence length for more natural rhythm
    5. Reducing uniform paragraph structure

    The tool preserves citations, technical terms, and academic meaning
    while making the prose read more naturally. AI provenance is still
    tracked and disclosed per platform integrity policy.
    """
    if not text or len(text.strip()) < 20:
        return {
            "original": text,
            "humanized": text,
            "changes": [],
            "patterns_detected": [],
            "naturalness_score": 0,
            "summary": "Text too short for humanization analysis.",
        }

    original = text
    humanized = text
    changes = []
    patterns_detected = []

    # --- 1. Detect AI patterns ---
    text_lower = text.lower()
    for pattern in _AI_PATTERN_INDICATORS:
        if pattern in text_lower:
            patterns_detected.append(pattern)

    # --- 2. Replace formulaic AI phrases ---
    _phrase_counter = {}

    for pattern, alternatives in _AI_PHRASE_REPLACEMENTS.items():
        matches = list(re.finditer(pattern, humanized, re.IGNORECASE))
        if matches:
            for match in reversed(matches):  # reverse to preserve indices
                key = pattern
                idx = _phrase_counter.get(key, 0)
                replacement = alternatives[idx % len(alternatives)]
                _phrase_counter[key] = idx + 1

                # Preserve capitalization
                if match.group(0)[0].isupper():
                    replacement = replacement[0].upper() + replacement[1:]

                old_text = match.group(0)
                humanized = humanized[:match.start()] + replacement + humanized[match.end():]
                changes.append({
                    "type": "phrase_naturalization",
                    "original": old_text,
                    "fixed": replacement,
                    "category": "humanize",
                })

    # --- 3. Reduce overused AI transition words ---
    _transition_counter = {}
    sentences = re.split(r'(?<=[.!?])\s+', humanized)
    naturalized_sentences = []

    for sentence in sentences:
        s = sentence.strip()
        if not s:
            naturalized_sentences.append(s)
            continue

        original_s = s
        first_word_match = re.match(r'^([A-Za-z]+)', s)
        if first_word_match:
            first_word = first_word_match.group(1).lower()
            if first_word in _AI_TRANSITION_REPLACEMENTS:
                # Count how many times this transition has been used
                count = _transition_counter.get(first_word, 0)
                alternatives = _AI_TRANSITION_REPLACEMENTS[first_word]

                # Only replace if this transition appears more than once
                # (first occurrence can stay, subsequent ones get varied)
                if count > 0:
                    replacement = alternatives[count % len(alternatives)]
                    if s[0].isupper():
                        replacement = replacement[0].upper() + replacement[1:]
                    # Replace just the first word, handle comma after
                    if s[len(first_word_match.group(1)):len(first_word_match.group(1))+1] == ',':
                        new_s = replacement + s[len(first_word_match.group(1))+1:]
                    else:
                        new_s = replacement + s[len(first_word_match.group(1)):]
                    changes.append({
                        "type": "transition_variation",
                        "original": original_s[:40] + "...",
                        "fixed": new_s[:40] + "...",
                        "category": "humanize",
                    })
                    s = new_s

                _transition_counter[first_word] = count + 1

        naturalized_sentences.append(s)

    humanized = " ".join(naturalized_sentences)

    # --- 4. Vary sentence beginnings ---
    _starter_counter = {}
    sentences = re.split(r'(?<=[.!?])\s+', humanized)
    varied_sentences = []

    for sentence in sentences:
        s = sentence.strip()
        if not s:
            varied_sentences.append(s)
            continue

        original_s = s
        s_lower = s.lower()

        for starter, alternatives in _AI_STARTER_VARIATIONS.items():
            if s_lower.startswith(starter):
                count = _starter_counter.get(starter, 0)
                # Replace only if this starter has been used before
                if count > 0:
                    replacement = alternatives[count % len(alternatives)]
                    if s[0].isupper():
                        replacement = replacement[0].upper() + replacement[1:]
                    # Replace the starter, keeping the rest
                    new_s = replacement + s[len(starter):]
                    changes.append({
                        "type": "sentence_starter_variation",
                        "original": original_s[:50] + ("..." if len(original_s) > 50 else ""),
                        "fixed": new_s[:50] + ("..." if len(new_s) > 50 else ""),
                        "category": "humanize",
                    })
                    s = new_s
                    break

                _starter_counter[starter] = count + 1

        varied_sentences.append(s)

    humanized = " ".join(varied_sentences)

    # --- 5. Vary sentence length: split very long sentences ---
    sentences = re.split(r'(?<=[.!?])\s+', humanized)
    length_adjusted = []

    for sentence in sentences:
        s = sentence.strip()
        if not s:
            length_adjusted.append(s)
            continue

        words_in_s = s.split()
        if len(words_in_s) > 35:
            # Try to split at a semicolon or conjunction
            split_points = []
            for conj in [r'\s+; however,\s+', r'\s+; moreover,\s+', r'\s+; consequently,\s+',
                         r'\s+; therefore,\s+', r'\s+; additionally,\s+',
                         r', and\s+', r', but\s+', r', while\s+', r', whereas\s+']:
                for m in re.finditer(conj, s, re.IGNORECASE):
                    left = s[:m.start()].split()
                    right = s[m.end():].split()
                    if len(left) > 8 and len(right) > 8:
                        split_points.append(m)

            if split_points:
                # Split at the middle-most point
                mid = len(s) // 2
                best = min(split_points, key=lambda m: abs((m.start() + m.end()) // 2 - mid))
                left_part = s[:best.start()].strip().rstrip(',').rstrip(';')
                right_part = s[best.end():].strip()
                if not left_part.endswith(('.', '!', '?')):
                    left_part += '.'
                if right_part and right_part[0].islower():
                    right_part = right_part[0].upper() + right_part[1:]
                new_s = left_part + ' ' + right_part
                if new_s != s:
                    changes.append({
                        "type": "sentence_split",
                        "original": original_s[:50] + ("..." if len(original_s) > 50 else ""),
                        "fixed": new_s[:50] + ("..." if len(new_s) > 50 else ""),
                        "category": "humanize",
                    })
                    s = new_s

        length_adjusted.append(s)

    humanized = " ".join(length_adjusted)

    # --- 6. Remove redundant qualifiers that AI tends to overuse ---
    redundant_qualifiers = [
        (r'\b(?:it is )?important to (?:note|mention|highlight|emphasize) that\b', "", 0),
        (r'\b(?:it is )?worth noting that\b', "", 0),
        (r'\b(?:it should be )?(?:noted|mentioned|emphasized) that\b', "", 0),
        (r'\bas previously mentioned\b', "", 0),
        (r'\bas stated earlier\b', "", 0),
        (r'\bas discussed above\b', "", 0),
    ]

    for pattern, _, _ in redundant_qualifiers:
        if re.search(pattern, humanized, re.IGNORECASE):
            new_humanized = re.sub(pattern, '', humanized, flags=re.IGNORECASE)
            if new_humanized != humanized:
                # Clean up: capitalize next letter if sentence start
                new_humanized = re.sub(r'^\s+', '', new_humanized)
                new_humanized = re.sub(r'\.\s+([a-z])', lambda m: '. ' + m.group(1).upper(), new_humanized)
                changes.append({
                    "type": "redundancy_removal",
                    "original": "filler qualifier phrase",
                    "fixed": "removed for directness",
                    "category": "humanize",
                })
                humanized = new_humanized

    # Clean up double spaces from replacements
    while "  " in humanized:
        humanized = humanized.replace("  ", " ")
    # Fix space before punctuation
    humanized = re.sub(r'\s+([,.!?;:])', r'\1', humanized)
    # Capitalize first letter after period if not already
    humanized = re.sub(r'([.!?]\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), humanized)

    # --- Calculate naturalness score ---
    naturalness_score = _calculate_naturalness_score(original, humanized, patterns_detected, changes)

    if humanized == original:
        summary = "Your text already reads naturally. No significant AI patterns detected."
    else:
        summary = (
            f"Naturalized text with {len(changes)} improvement(s): "
            f"reduced {len(patterns_detected)} AI pattern(s), "
            f"varied transitions and sentence structure. "
            f"Naturalness score improved to {naturalness_score}/100."
        )

    return {
        "original": original,
        "humanized": humanized,
        "changes": changes,
        "patterns_detected": patterns_detected,
        "naturalness_score": naturalness_score,
        "summary": summary,
    }


def _calculate_naturalness_score(original: str, humanized: str, patterns: list, changes: list) -> int:
    """Calculate a naturalness score (0-100) based on AI pattern reduction."""
    score = 50  # Start at middle

    # Fewer AI patterns = higher score
    original_lower = original.lower()
    total_patterns = sum(1 for p in _AI_PATTERN_INDICATORS if p in original_lower)
    remaining_patterns = len(patterns) - len([p for p in patterns if p not in humanized.lower()])
    if total_patterns > 0:
        reduction = (total_patterns - remaining_patterns) / total_patterns
        score += int(reduction * 25)
    else:
        score += 15  # Already had few patterns

    # More changes made = more naturalized
    if len(changes) >= 10:
        score += 15
    elif len(changes) >= 5:
        score += 10
    elif len(changes) >= 1:
        score += 5

    # Sentence length variation
    orig_sentences = re.split(r'[.!?]+', original)
    orig_lengths = [len(s.split()) for s in orig_sentences if s.strip()]
    new_sentences = re.split(r'[.!?]+', humanized)
    new_lengths = [len(s.split()) for s in new_sentences if s.strip()]

    if len(orig_lengths) > 1 and len(new_lengths) > 1:
        import statistics
        try:
            orig_cv = statistics.stdev(orig_lengths) / statistics.mean(orig_lengths) if statistics.mean(orig_lengths) > 0 else 0
            new_cv = statistics.stdev(new_lengths) / statistics.mean(new_lengths) if statistics.mean(new_lengths) > 0 else 0
            if new_cv > orig_cv:
                score += 10  # More variation is good
        except Exception:
            pass

    return max(0, min(100, score))
