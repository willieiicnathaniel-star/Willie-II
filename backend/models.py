"""
THEeye - Data Models
Pydantic schemas for all platform entities.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ---------------------------------------------------------------------------
# Literature Discovery
# ---------------------------------------------------------------------------

class Author(BaseModel):
    name: str
    affiliation: Optional[str] = None


class Paper(BaseModel):
    """A single research paper retrieved from a database."""
    title: str
    authors: list[Author] = []
    year: Optional[int] = None
    journal: Optional[str] = None
    issn: Optional[str] = None
    doi: Optional[str] = None
    abstract: Optional[str] = None
    cited_by_count: int = 0
    quartile: Optional[str] = None  # Q1, Q2, Q3, Q4
    is_open_access: bool = False
    oa_url: Optional[str] = None
    tldr: Optional[str] = None  # Semantic Scholar AI summary
    source_db: str = ""  # which database it came from
    openalex_id: Optional[str] = None
    concepts: list[str] = []
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    pdf_url: Optional[str] = None
    keywords: list[str] = []


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query string")
    databases: list[str] = Field(
        default=["openalex", "crossref", "semantic_scholar"],
        description="Which databases to search"
    )
    quartiles: list[str] = Field(
        default=["Q1", "Q2", "Q3"],
        description="Filter results to these quartiles only"
    )
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    min_citations: int = 0
    max_results: int = 25
    open_access_only: bool = False


class SearchResponse(BaseModel):
    query: str
    total_found: int
    papers: list[Paper]
    search_timestamp: str


# ---------------------------------------------------------------------------
# Data Extraction
# ---------------------------------------------------------------------------

class ExtractedData(BaseModel):
    """Structured data extracted from a paper."""
    paper_title: str
    doi: Optional[str] = None
    research_question: Optional[str] = None
    methodology: Optional[str] = None
    sample_size: Optional[str] = None
    data_source: Optional[str] = None
    variables: list[str] = []
    key_findings: list[str] = []
    effect_size: Optional[str] = None
    limitations: Optional[str] = None
    extraction_method: str = "template"  # template or llm


class ExtractionRequest(BaseModel):
    paper: Paper
    use_llm: bool = False


class ExtractionBatchRequest(BaseModel):
    papers: list[Paper]
    use_llm: bool = False


# ---------------------------------------------------------------------------
# Drafting Assistant
# ---------------------------------------------------------------------------

class DraftRequest(BaseModel):
    section_type: str = Field(
        ..., description="One of: literature_review, introduction, abstract, conclusion, summary"
    )
    topic: str
    papers: list[Paper] = []
    extracted_data: list[ExtractedData] = []
    style: str = "academic"  # academic, concise, detailed
    use_llm: bool = False
    max_words: int = 1000


class DraftResponse(BaseModel):
    section_type: str
    topic: str
    content: str
    citations: list[dict] = []  # [{ref_number, authors, year, title, journal, doi}]
    word_count: int
    disclaimer: str


# ---------------------------------------------------------------------------
# Provenance & Integrity Audit
# ---------------------------------------------------------------------------

class ProvenanceRecord(BaseModel):
    """Tracks the origin of every piece of information."""
    action: str  # search, extract, draft
    timestamp: str
    query_or_input: str
    sources_used: list[str] = []  # DOIs or paper titles
    ai_generated: bool = False
    human_verified: bool = False
    details: Optional[str] = None


class AuditReport(BaseModel):
    session_id: str
    created_at: str
    records: list[ProvenanceRecord]
    disclosure_statement: str
    total_sources: int
    ai_assisted_sections: list[str]
    verification_status: str  # "pending", "partial", "verified"


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    institution: str = ""
    research_field: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str
    remember: bool = False


class AuthResponse(BaseModel):
    user: dict
    token: str


# ---------------------------------------------------------------------------
# Quick Generate (single prompt → final output)
# ---------------------------------------------------------------------------

class QuickGenerateRequest(BaseModel):
    prompt: str = Field(..., description="Research prompt, e.g., 'Write a literature review on FDI and economic growth in Africa'")
    section_type: str = Field(default="literature_review",
                              description="Section to generate: literature_review, introduction, methodology, abstract, conclusion, summary")
    databases: list[str] = Field(default=["openalex", "crossref", "semantic_scholar", "google_scholar", "econpapers", "eric"])
    quartiles: list[str] = Field(default=["Q1", "Q2", "Q3"])
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    max_results: int = 15
    max_words: int = 1000


class DocumentExportRequest(BaseModel):
    """Request to export generated text in various document formats."""
    text: str = Field(..., description="The main body text to export")
    title: str = Field(default="THEeye Research Output", description="Document title")
    citations: list[dict] = Field(default=[], description="List of citation dicts with authors, year, title, journal, doi")
    disclaimer: str = Field(default="", description="Integrity disclaimer text")
    section_type: str = Field(default="", description="Section type (e.g., literature_review)")
    topic: str = Field(default="", description="Research topic")
    word_count: int = Field(default=0, description="Word count of the generated text")
    total_sources: int = Field(default=0, description="Number of source papers")
    format: str = Field(default="docx", description="Export format: docx, pdf, html, md, txt")


class QuickGenerateResponse(BaseModel):
    topic: str
    section_type: str
    papers: list[Paper]
    extracted_data: list[ExtractedData]
    comparison_table: list[dict]
    draft: DraftResponse
    disclosure: str
    total_sources: int


# ---------------------------------------------------------------------------
# Data Analysis (R / Stata 18)
# ---------------------------------------------------------------------------

class AnalysisRequest(BaseModel):
    method: str = Field(..., description="Analysis method: ols, panel_fixed, logistic, iv_2sls, did, time_series, robustness, descriptive, correlation")
    language: str = Field(default="r", description="Programming language: r or stata")
    dependent_variable: str = Field(default="y", description="Dependent variable name")
    independent_variables: list[str] = Field(default=[], description="Independent variable names")
    control_variables: list[str] = Field(default=[], description="Control variable names")
    data_file: str = Field(default="data.csv", description="Data file name")
    entity_variable: str = Field(default="country", description="Panel entity variable (for panel data)")
    time_variable: str = Field(default="year", description="Time variable (for panel/time series)")
    cluster_variable: str = Field(default="", description="Clustering variable for SE")
    robust_se: bool = True
    instruments: list[str] = Field(default=[], description="Instrument variables (for IV)")
    treatment_variable: str = Field(default="treated", description="Treatment variable (for DiD)")
    post_variable: str = Field(default="post", description="Post period variable (for DiD)")
    options: dict = Field(default={}, description="Additional options")


class AnalysisResponse(BaseModel):
    method: str
    language: str
    code: str
    description: str
    packages_required: list[str] = []


class AnalysisRecommendationRequest(BaseModel):
    research_topic: str
    variables: list[str] = []
    data_type: str = Field(default="cross_section", description="cross_section, panel, or time_series")


# ---------------------------------------------------------------------------
# Writing Tools
# ---------------------------------------------------------------------------

class WritingAnalysisRequest(BaseModel):
    text: str = Field(..., description="Text to analyze")
    journal_name: str = Field(default="", description="Target journal name for specific suggestions")


class WritingToolInfo(BaseModel):
    tool_id: str
    name: str
    url: str
    description: str
    features: list[str] = []
    how_to_use: list[str] = []


# ---------------------------------------------------------------------------
# Reference Management
# ---------------------------------------------------------------------------

class ReferenceExportRequest(BaseModel):
    papers: list[Paper]
    format: str = Field(default="bibtex", description="Export format: bibtex, ris, csl_json, endnote, apa, mla, chicago, harvard")


class ReferenceExportResponse(BaseModel):
    format: str
    format_name: str
    content: str
    filename: str
    count: int


class CitationFormatRequest(BaseModel):
    papers: list[Paper]
    style: str = Field(default="apa", description="Citation style: apa, mla, chicago, harvard")


class CitationVerificationRequest(BaseModel):
    text: str = Field(..., description="Text containing inline citations to verify")
    references: list[dict] = Field(default=[], description="Reference list to check against. Each item: {ref_number, authors, year, title, journal, doi}")


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

class ConfigUpdateRequest(BaseModel):
    updates: dict = Field(..., description="Configuration key-value pairs to update")


class ContentUpdateRequest(BaseModel):
    key: str
    content: str


class UserRoleUpdateRequest(BaseModel):
    role: str = Field(..., description="Role to assign: user or admin")


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


class AdminResetPasswordRequest(BaseModel):
    user_id: str
    new_password: str


class ProfileUpdateRequest(BaseModel):
    name: str = None
    institution: str = None
    research_field: str = None


class AiTestRequest(BaseModel):
    provider: str = Field(..., description="Provider ID: gemini, groq, deepseek, mistral, qwen, openai, anthropic, doubao")
    api_key: str = Field(default=None, description="Optional API key to test (uses configured key if omitted)")


# ---------------------------------------------------------------------------
# Document Drafting & Roadmap Engine
# ---------------------------------------------------------------------------

class RoadmapRequest(BaseModel):
    document_type: str = Field(..., description="Document type: research_article, thesis, literature_review, book_report, review_paper, conference_paper, research_proposal")
    format: str = Field(default="general", description="Format key (e.g., Q1, Q2, undergraduate_usa, phd_chinese, systematic, etc.)")
    topic: str = Field(..., description="Research topic or title")
    field: str = Field(default="", description="Academic field (e.g., Economics, Public Health)")


class RoadmapSection(BaseModel):
    title: str
    purpose: str
    est_words: int
    guidelines: str


class RoadmapResponse(BaseModel):
    document_type: str
    document_type_label: str
    format: str
    format_description: str
    topic: str
    field: str
    sections: list[RoadmapSection]
    total_estimated_words: int
    total_sections: int
    roadmap_markdown: str
    disclaimer: str


class TopicSuggestionRequest(BaseModel):
    field: str = Field(..., description="Research field key: economics, political_science, sociology, public_health, environment, education, technology, law, business, agriculture, interdisciplinary")
    keywords: str = Field(default="", description="Optional comma-separated keywords to focus topic generation")
    focus_novelty: bool = Field(default=True, description="If true, prioritize topics that have not been researched before")
    max_topics: int = Field(default=10, description="Maximum number of topic suggestions to return")


class TopicSuggestion(BaseModel):
    topic: str
    field: str
    sub_area: str
    novelty_factors: list[str]
    suggested_methodology: list[str]
    research_gap: str
    estimated_difficulty: str
    potential_journals: list[str]


class TopicSuggestionResponse(BaseModel):
    field: str
    sub_areas: list[str]
    topics: list[TopicSuggestion]
    total: int
    note: str


class OpenAccessArticleRequest(BaseModel):
    topic: str = Field(..., description="Research topic to find open-access articles for")
    max_results: int = Field(default=15, description="Maximum number of articles to return")


class OpenAccessArticle(BaseModel):
    title: str
    authors: list[str]
    year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    abstract: Optional[str] = None
    cited_by_count: int = 0
    is_open_access: bool = True
    pdf_url: str
    oa_url: Optional[str] = None
    source: str = ""
    license: Optional[str] = None


class OpenAccessArticleResponse(BaseModel):
    topic: str
    total_found: int
    articles: list[dict]
    search_timestamp: str


class DownloadPdfRequest(BaseModel):
    url: str = Field(..., description="Direct PDF URL to download")
