"""
THEeye - Admin Module
System configuration, content management, and platform statistics.

Allows the administrator to:
  - View and edit system settings
  - Manage drafting templates and disclosure statements
  - View platform usage statistics
  - Configure database sources and API keys
"""

from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional
import json


# ---------------------------------------------------------------------------
# System Configuration
# ---------------------------------------------------------------------------

@dataclass
class SystemConfig:
    """Editable system-wide configuration."""
    # Platform info
    platform_name: str = "THEeye"
    platform_version: str = "3.0.0"
    platform_description: str = "AI-Assisted Research Platform"

    # Contact email for API polite pools
    contact_email: str = "research@theeye.local"

    # API keys (stored as empty strings - admin can set them)
    semantic_scholar_api_key: str = ""
    openalex_email: str = "research@theeye.local"
    crossref_email: str = "research@theeye.local"

    # Search defaults
    default_max_results: int = 25
    default_quartiles: list = field(default_factory=lambda: ["Q1", "Q2", "Q3"])
    default_databases: list = field(default_factory=lambda: [
        "openalex", "crossref", "semantic_scholar",
        "google_scholar", "econpapers", "eric"
    ])

    # Drafting defaults
    default_max_words: int = 1000
    default_style: str = "academic"

    # Integrity settings
    require_disclosure: bool = True
    auto_add_disclaimer: bool = True
    track_provenance: bool = True

    # Feature toggles
    enable_data_analysis: bool = True
    enable_writing_tools: bool = True
    enable_reference_management: bool = True
    enable_literature_review: bool = True

    # Data analysis tools
    r_enabled: bool = True
    rstudio_enabled: bool = True
    stata_enabled: bool = True
    stata_version: str = "18"

    # Writing tools
    grammarly_enabled: bool = True
    quillbot_enabled: bool = True
    paperpal_enabled: bool = True

    # Reference management
    mendeley_enabled: bool = True
    zotero_enabled: bool = True
    notepal_enabled: bool = True

    # Registration settings
    allow_public_registration: bool = True
    require_email_verification: bool = False


_config = SystemConfig()


def get_config() -> dict:
    """Get the current system configuration."""
    return _config.__dict__.copy()


def update_config(updates: dict) -> dict:
    """Update system configuration with partial updates."""
    for key, value in updates.items():
        if hasattr(_config, key):
            setattr(_config, key, value)
    return get_config()


def get_feature_flags() -> dict:
    """Get only the feature toggle settings."""
    return {
        "enable_data_analysis": _config.enable_data_analysis,
        "enable_writing_tools": _config.enable_writing_tools,
        "enable_reference_management": _config.enable_reference_management,
        "enable_literature_review": _config.enable_literature_review,
        "r_enabled": _config.r_enabled,
        "rstudio_enabled": _config.rstudio_enabled,
        "stata_enabled": _config.stata_enabled,
        "grammarly_enabled": _config.grammarly_enabled,
        "quillbot_enabled": _config.quillbot_enabled,
        "paperpal_enabled": _config.paperpal_enabled,
        "mendeley_enabled": _config.mendeley_enabled,
        "zotero_enabled": _config.zotero_enabled,
        "notepal_enabled": _config.notepal_enabled,
        "allow_public_registration": _config.allow_public_registration,
    }


# ---------------------------------------------------------------------------
# Content Management (editable templates & disclosures)
# ---------------------------------------------------------------------------

_content_store: dict[str, str] = {
    "disclosure_statement": (
        "This document was prepared using THEeye, an AI-assisted research platform. "
        "All content was generated based on peer-reviewed sources retrieved from "
        "OpenAlex, Crossref, Semantic Scholar, and other academic databases. "
        "Every claim is traceable to its original source via DOI or direct citation. "
        "The author has reviewed and verified all AI-assisted content for accuracy "
        "and appropriateness in accordance with academic integrity standards."
    ),
    "integrity_disclaimer": (
        "AI Disclosure: Portions of this document were generated with AI assistance. "
        "All AI-generated text is based on verified academic sources and has been "
        "reviewed by the author. Sources are cited throughout and listed in the references."
    ),
    "methodology_template": (
        "This study employs a systematic approach to literature review and data analysis. "
        "Papers were sourced from {databases} with quartile filtering ({quartiles}). "
        "Data extraction was performed using structured templates identifying methodology, "
        "sample size, variables, and key findings."
    ),
    "citation_format_default": "apa",
    "welcome_message": (
        "Welcome to THEeye - your AI-assisted research platform. "
        "Search databases, extract data, generate drafts, and manage references "
        "all in one place."
    ),
}


def get_content(key: str = None) -> dict | str:
    """Get content by key, or all content if no key specified."""
    if key:
        return {"key": key, "content": _content_store.get(key, "")}
    return _content_store.copy()


def update_content(key: str, content: str) -> dict:
    """Update a content item."""
    _content_store[key] = content
    return {"key": key, "content": content, "updated": True}


def list_content_keys() -> list[dict]:
    """List all editable content keys with descriptions."""
    return [
        {"key": "disclosure_statement", "description": "Default disclosure statement added to generated drafts"},
        {"key": "integrity_disclaimer", "description": "AI integrity disclaimer for academic compliance"},
        {"key": "methodology_template", "description": "Template for methodology sections (supports {databases}, {quartiles})"},
        {"key": "citation_format_default", "description": "Default citation format: apa, mla, chicago, harvard"},
        {"key": "welcome_message", "description": "Welcome message shown on the platform homepage"},
    ]


# ---------------------------------------------------------------------------
# Platform Statistics
# ---------------------------------------------------------------------------

_stats = {
    "total_searches": 0,
    "total_drafts_generated": 0,
    "total_extractions": 0,
    "total_quick_generates": 0,
    "total_users_registered": 0,
    "database_usage": {},
    "section_types_generated": {},
    "last_activity": None,
}


def record_stat(action: str, details: dict = None):
    """Record a platform activity for statistics."""
    _stats["last_activity"] = datetime.now(timezone.utc).isoformat()

    if action == "search":
        _stats["total_searches"] += 1
        if details and "databases" in details:
            for db in details["databases"]:
                _stats["database_usage"][db] = _stats["database_usage"].get(db, 0) + 1
    elif action == "draft":
        _stats["total_drafts_generated"] += 1
        if details and "section_type" in details:
            st = details["section_type"]
            _stats["section_types_generated"][st] = _stats["section_types_generated"].get(st, 0) + 1
    elif action == "extract":
        _stats["total_extractions"] += 1
    elif action == "quick_generate":
        _stats["total_quick_generates"] += 1
    elif action == "user_registered":
        _stats["total_users_registered"] += 1


def get_stats() -> dict:
    """Get platform statistics."""
    return _stats.copy()


def reset_stats() -> dict:
    """Reset all statistics (admin only)."""
    global _stats
    _stats = {
        "total_searches": 0,
        "total_drafts_generated": 0,
        "total_extractions": 0,
        "total_quick_generates": 0,
        "total_users_registered": 0,
        "database_usage": {},
        "section_types_generated": {},
        "last_activity": None,
    }
    return {"status": "reset", "stats": _stats}


# ---------------------------------------------------------------------------
# Database Source Management
# ---------------------------------------------------------------------------

_database_sources = {
    "openalex": {
        "name": "OpenAlex",
        "url": "https://api.openalex.org",
        "description": "Open catalog of scholarly works, authors, and institutions",
        "requires_key": False,
        "enabled": True,
        "category": "general",
    },
    "crossref": {
        "name": "Crossref",
        "url": "https://api.crossref.org",
        "description": "DOI registration agency with metadata for 150M+ works",
        "requires_key": False,
        "enabled": True,
        "category": "general",
    },
    "semantic_scholar": {
        "name": "Semantic Scholar",
        "url": "https://api.semanticscholar.org",
        "description": "AI-powered search with TLDR summaries",
        "requires_key": False,
        "enabled": True,
        "category": "general",
    },
    "google_scholar": {
        "name": "Google Scholar",
        "url": "https://scholar.google.com",
        "description": "Broad academic search engine (via Semantic Scholar proxy)",
        "requires_key": False,
        "enabled": True,
        "category": "general",
    },
    "econpapers": {
        "name": "EconPapers / RePEc",
        "url": "https://econpapers.repec.org",
        "description": "Economics research papers from RePEc",
        "requires_key": False,
        "enabled": True,
        "category": "economics",
    },
    "eric": {
        "name": "ERIC",
        "url": "https://eric.ed.gov",
        "description": "Education Resources Information Center",
        "requires_key": False,
        "enabled": True,
        "category": "education",
    },
    "paper_connect": {
        "name": "Paper Connect",
        "url": "https://www.paperconnect.net",
        "description": "Literature connection and citation mapping tool",
        "requires_key": False,
        "enabled": True,
        "category": "general",
    },
}


def get_database_sources() -> dict:
    """Get all configured database sources."""
    return _database_sources.copy()


def toggle_database_source(source_id: str) -> dict:
    """Enable or disable a database source."""
    if source_id not in _database_sources:
        raise ValueError(f"Unknown database source: {source_id}")
    _database_sources[source_id]["enabled"] = not _database_sources[source_id]["enabled"]
    return _database_sources[source_id]


# ---------------------------------------------------------------------------
# Tool Integrations Registry
# ---------------------------------------------------------------------------

_tool_integrations = {
    # Data Analysis Tools
    "r": {
        "name": "R",
        "category": "data_analysis",
        "description": "Statistical computing and graphics language",
        "url": "https://www.r-project.org",
        "download_url": "https://cran.r-project.org/",
        "enabled": True,
        "integration_type": "code_generation",
    },
    "rstudio": {
        "name": "RStudio",
        "category": "data_analysis",
        "description": "Integrated development environment for R",
        "url": "https://posit.co/products/cloud/public/",
        "download_url": "https://posit.co/download/rstudio-desktop/",
        "enabled": True,
        "integration_type": "ide",
    },
    "stata": {
        "name": "Stata 18",
        "category": "data_analysis",
        "description": "Statistical software for data science",
        "url": "https://www.stata.com",
        "download_url": "https://www.stata.com/install-guide/",
        "enabled": True,
        "integration_type": "code_generation",
    },
    # Writing Tools
    "grammarly": {
        "name": "Grammarly",
        "category": "writing",
        "description": "AI-powered grammar, style, and clarity checker",
        "url": "https://www.grammarly.com",
        "enabled": True,
        "integration_type": "external_link",
    },
    "quillbot": {
        "name": "QuillBot",
        "category": "writing",
        "description": "Paraphrasing and writing enhancement tool",
        "url": "https://quillbot.com",
        "enabled": True,
        "integration_type": "external_link",
    },
    "paperpal": {
        "name": "Paperpal",
        "category": "writing",
        "description": "Academic writing assistant by Cactus Communications",
        "url": "https://paperpal.com",
        "enabled": True,
        "integration_type": "external_link",
    },
    # Reference Management
    "mendeley": {
        "name": "Mendeley",
        "category": "reference_management",
        "description": "Reference manager and academic social network",
        "url": "https://www.mendeley.com",
        "enabled": True,
        "integration_type": "export",
    },
    "zotero": {
        "name": "Zotero",
        "category": "reference_management",
        "description": "Free, open-source reference manager",
        "url": "https://www.zotero.org",
        "enabled": True,
        "integration_type": "export",
    },
    "notepal": {
        "name": "NotePal",
        "category": "reference_management",
        "description": "Research note-taking and reference management",
        "url": "https://notepal.com",
        "enabled": True,
        "integration_type": "external_link",
    },
}


def get_tool_integrations(category: str = None) -> dict:
    """Get all tool integrations, optionally filtered by category."""
    if category:
        return {k: v for k, v in _tool_integrations.items() if v["category"] == category}
    return _tool_integrations.copy()


def toggle_tool_integration(tool_id: str) -> dict:
    """Enable or disable a tool integration."""
    if tool_id not in _tool_integrations:
        raise ValueError(f"Unknown tool: {tool_id}")
    _tool_integrations[tool_id]["enabled"] = not _tool_integrations[tool_id]["enabled"]
    return _tool_integrations[tool_id]
