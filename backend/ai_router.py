"""
THEeye AI Router — Multi-model text generation with auto-routing and fallback.

Supports models with FREE API tiers:
  - Google Gemini  (gemini-2.0-flash, gemini-1.5-flash, gemini-1.5-pro)
  - Groq           (Llama 3.3 70B, Mixtral 8x7B, Gemma 2)
  - DeepSeek       (deepseek-chat, deepseek-coder)
  - Mistral AI     (mistral-small-latest, mistral-tiny)
  - Qwen / DashScope (qwen-max, qwen-plus, qwen-turbo)

Also supports PAID models (require API keys):
  - OpenAI         (gpt-5, gpt-5-mini, gpt-4o)
  - Anthropic      (claude-sonnet-4, claude-3-5-sonnet, claude-3-haiku)

Academic drafting priority: Claude Sonnet 4 > GPT-5 > Qwen-Max >
  Claude 3.5 Sonnet > GPT-4o > Qwen-Plus > DeepSeek > Gemini > Groq > Mistral

Auto-routing: Each task type has a preferred model priority order.
Fallback: If a model fails (rate limit, error, no key), tries the next.
Template fallback: If all models fail, returns None — caller uses template.
"""

import os
import httpx
from typing import Optional

# ---------------------------------------------------------------------------
# Provider Registry
# ---------------------------------------------------------------------------

PROVIDERS = {
    "gemini": {
        "display_name": "Google Gemini",
        "env_key": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "models": ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
        "free_tier": True,
        "api_style": "gemini",
    },
    "groq": {
        "display_name": "Groq (Llama / Mixtral)",
        "env_key": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"],
        "free_tier": True,
        "api_style": "openai",
    },
    "deepseek": {
        "display_name": "DeepSeek",
        "env_key": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-coder"],
        "free_tier": True,
        "api_style": "openai",
    },
    "mistral": {
        "display_name": "Mistral AI",
        "env_key": "MISTRAL_API_KEY",
        "base_url": "https://api.mistral.ai/v1",
        "models": ["mistral-small-latest", "mistral-tiny"],
        "free_tier": True,
        "api_style": "openai",
    },
    "qwen": {
        "display_name": "Qwen (Alibaba DashScope)",
        "env_key": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-max", "qwen-plus", "qwen-turbo"],
        "free_tier": True,
        "api_style": "openai",
    },
    "openai": {
        "display_name": "OpenAI (GPT-5)",
        "env_key": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-5", "gpt-5-mini", "gpt-4o"],
        "free_tier": False,
        "api_style": "openai",
    },
    "anthropic": {
        "display_name": "Anthropic (Claude)",
        "env_key": "ANTHROPIC_API_KEY",
        "base_url": "https://api.anthropic.com/v1",
        "models": ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
        "free_tier": False,
        "api_style": "anthropic",
    },
}

# ---------------------------------------------------------------------------
# Task Routing — task_type -> ordered list of (provider, model)
# ---------------------------------------------------------------------------

TASK_ROUTING = {
    "academic_drafting": [
        ("anthropic", "claude-sonnet-4-20250514"),
        ("openai", "gpt-5"),
        ("qwen", "qwen-max"),
        ("anthropic", "claude-3-5-sonnet-20241022"),
        ("openai", "gpt-4o"),
        ("qwen", "qwen-plus"),
        ("deepseek", "deepseek-chat"),
        ("gemini", "gemini-1.5-pro"),
        ("groq", "llama-3.3-70b-versatile"),
        ("mistral", "mistral-small-latest"),
    ],
    "topic_suggestion": [
        ("groq", "llama-3.3-70b-versatile"),
        ("gemini", "gemini-2.0-flash"),
        ("mistral", "mistral-small-latest"),
        ("deepseek", "deepseek-chat"),
        ("qwen", "qwen-turbo"),
    ],
    "roadmap_generation": [
        ("gemini", "gemini-2.0-flash"),
        ("deepseek", "deepseek-chat"),
        ("qwen", "qwen-turbo"),
        ("groq", "llama-3.3-70b-versatile"),
    ],
    "grammar_fix": [
        ("gemini", "gemini-2.0-flash"),
        ("mistral", "mistral-tiny"),
        ("groq", "gemma2-9b-it"),
        ("deepseek", "deepseek-chat"),
    ],
    "paraphrase": [
        ("deepseek", "deepseek-chat"),
        ("gemini", "gemini-1.5-pro"),
        ("qwen", "qwen-plus"),
        ("groq", "llama-3.3-70b-versatile"),
    ],
    "academic_enhance": [
        ("deepseek", "deepseek-chat"),
        ("gemini", "gemini-1.5-pro"),
        ("groq", "llama-3.3-70b-versatile"),
        ("mistral", "mistral-small-latest"),
    ],
    "code_generation": [
        ("deepseek", "deepseek-coder"),
        ("qwen", "qwen-plus"),
        ("gemini", "gemini-2.0-flash"),
        ("groq", "llama-3.3-70b-versatile"),
    ],
    "quick_generate": [
        ("anthropic", "claude-sonnet-4-20250514"),
        ("openai", "gpt-5"),
        ("qwen", "qwen-max"),
        ("anthropic", "claude-3-5-sonnet-20241022"),
        ("openai", "gpt-4o"),
        ("qwen", "qwen-plus"),
        ("deepseek", "deepseek-chat"),
        ("gemini", "gemini-1.5-pro"),
        ("groq", "llama-3.3-70b-versatile"),
        ("mistral", "mistral-small-latest"),
    ],
    "general": [
        ("gemini", "gemini-2.0-flash"),
        ("groq", "llama-3.3-70b-versatile"),
        ("deepseek", "deepseek-chat"),
        ("mistral", "mistral-small-latest"),
        ("qwen", "qwen-turbo"),
    ],
}

# ---------------------------------------------------------------------------
# System Prompts per Task
# ---------------------------------------------------------------------------

SYSTEM_PROMPTS = {
    "academic_drafting": (
        "You are an expert academic writer producing publication-quality text "
        "suitable for Q1–Q3 indexed journals. Follow these rules strictly:\n\n"
        "0. OUTPUT DISCIPLINE (CRITICAL): Do NOT repeat, echo, paraphrase, or "
        "reference the prompt or instructions. Do NOT include preambles such as "
        "'Here is...' or 'Sure, I'll write...'. Do NOT include postambles such as "
        "'Let me know...' or 'I hope this helps.' Start DIRECTLY with the ## "
        "heading of the academic content. End with the last paragraph of content "
        "— no closing remarks.\n"
        "1. STRUCTURE: Use Markdown headings to organize content hierarchically:\n"
        "   - ## for the main section title (e.g., ## Literature Review: [Topic])\n"
        "   - ### for thematic sub-sections (e.g., ### Institutional Quality and Growth)\n"
        "   - #### for further sub-divisions within a theme when warranted\n"
        "2. ACADEMIC TONE: Write in formal, objective, scholarly English. Use "
        "third-person perspective, precise terminology, and hedged claims "
        "(e.g., 'the evidence suggests,' 'these findings indicate'). Avoid "
        "colloquialisms, contractions, and first-person pronouns unless "
        "conventionally appropriate.\n"
        "3. SYNTHESIS: Do not merely summarize sources sequentially. Group "
        "findings thematically, compare and contrast methodologies, evaluate "
        "convergences and divergences, and synthesize across studies.\n"
        "4. CITATIONS: Use APA in-text citation format [e.g., (Author, Year)] "
        "and only cite the sources provided in the context. NEVER fabricate "
        "references. Number citations sequentially as they appear.\n"
        "5. PARAGRAPH STRUCTURE: Each paragraph should begin with a clear topic "
        "sentence, followed by evidence and analysis, and end with a transition "
        "or concluding observation. Aim for 4–8 sentences per paragraph.\n"
        "6. COMPLETENESS: Ensure the text has a clear introduction framing the "
        "section, well-developed body paragraphs, and a concluding synthesis "
        "or summary paragraph that ties findings together and identifies gaps.\n"
        "7. JOURNAL STANDARD: The writing must meet the rigor expected in "
        "Q1–Q3 indexed journals: precise operational definitions, attention "
        "to methodological quality, awareness of limitations, and engagement "
        "with theoretical frameworks.\n"
        "Return ONLY the academic text in Markdown format. No meta-commentary."
    ),
    "topic_suggestion": (
        "You are a research advisor helping a scholar identify novel research "
        "topics. Suggest specific, feasible, and novel research topics that "
        "address genuine gaps in the literature. For each topic, briefly explain "
        "why it matters and what methodology would be suitable."
    ),
    "roadmap_generation": (
        "You are an academic writing consultant. Create a detailed document "
        "roadmap/outline with section titles, purposes, estimated word counts, "
        "and writing guidelines. Return the roadmap in Markdown format."
    ),
    "grammar_fix": (
        "You are a professional proofreader. Fix all grammar, spelling, and "
        "punctuation errors in the provided text. Preserve the original meaning, "
        "tone, and formatting. Return ONLY the corrected text — no explanations."
    ),
    "paraphrase": (
        "You are an expert paraphraser. Rewrite the provided text to improve "
        "clarity, readability, and flow while preserving the original meaning. "
        "Vary sentence structure and vocabulary. Return ONLY the paraphrased text."
    ),
    "academic_enhance": (
        "You are an academic editor. Enhance the provided text to make it more "
        "scholarly and formal. Replace informal language with academic "
        "alternatives, improve transitions, and strengthen arguments. Return "
        "ONLY the enhanced text — no explanations."
    ),
    "code_generation": (
        "You are an expert programmer and data analyst. Generate clean, "
        "well-commented, runnable code based on the user's request. Include "
        "comments explaining each step. Return the code in a Markdown code block."
    ),
    "quick_generate": (
        "You are an expert academic researcher and writer. Using the provided "
        "search results, generate a well-structured academic text with in-text "
        "citations (APA format). Only cite the sources provided.\n\n"
        "CRITICAL: Do NOT repeat, echo, or reference the prompt. Do NOT include "
        "preambles ('Here is...', 'Certainly...') or postambles ('Let me know...'). "
        "Start DIRECTLY with the ## heading. Return ONLY the academic text in "
        "Markdown format."
    ),
    "general": (
        "You are a knowledgeable AI assistant. Respond clearly and concisely "
        "to the user's request."
    ),
}


# ---------------------------------------------------------------------------
# Key Management
# ---------------------------------------------------------------------------

def _get_api_key(provider: str) -> Optional[str]:
    """Get the API key for a provider.

    Checks the admin-configured SystemConfig first (set via the Admin Panel),
    then falls back to environment variables.
    """
    # 1. Check admin config (overrides env vars when set)
    try:
        from .admin import get_config
        config = get_config()
        config_key = f"{provider}_api_key"
        val = config.get(config_key, "")
        if val and val.strip():
            return val.strip()
    except Exception:
        pass

    # 2. Fall back to environment variables
    env_key = PROVIDERS[provider]["env_key"]
    return os.environ.get(env_key, "").strip() or None


def get_available_providers() -> list:
    """Return list of providers that have API keys configured."""
    available = []
    for provider_id, info in PROVIDERS.items():
        if _get_api_key(provider_id):
            available.append({
                "provider": provider_id,
                "display_name": info["display_name"],
                "models": info["models"],
                "free_tier": info["free_tier"],
            })
    return available


def get_routing_info() -> dict:
    """Return the full routing configuration for admin/debug display."""
    return {
        "providers": {
            pid: {
                "display_name": p["display_name"],
                "models": p["models"],
                "free_tier": p["free_tier"],
                "has_key": bool(_get_api_key(pid)),
            }
            for pid, p in PROVIDERS.items()
        },
        "task_routing": TASK_ROUTING,
    }


def _key_source(provider: str) -> str:
    """Return 'admin' if key comes from admin config, 'env' if from env var, else 'none'."""
    try:
        from .admin import get_config
        config = get_config()
        val = config.get(f"{provider}_api_key", "")
        if val and val.strip():
            return "admin"
    except Exception:
        pass
    env_key = PROVIDERS[provider]["env_key"]
    if os.environ.get(env_key, "").strip():
        return "env"
    return "none"


def _mask_key(key: Optional[str]) -> str:
    """Mask an API key, showing only the first 4 and last 4 characters."""
    if not key:
        return ""
    if len(key) <= 12:
        return "*" * len(key)
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


def get_ai_status() -> dict:
    """Return detailed AI provider status for the Admin Panel.

    For each provider, reports whether a key is configured, where it comes from
    (admin config vs env var), and a masked preview of the key.
    """
    providers = {}
    for pid, info in PROVIDERS.items():
        key = _get_api_key(pid)
        providers[pid] = {
            "display_name": info["display_name"],
            "models": info["models"],
            "free_tier": info["free_tier"],
            "api_style": info["api_style"],
            "env_key": info["env_key"],
            "has_key": bool(key),
            "key_source": _key_source(pid),
            "key_preview": _mask_key(key),
        }
    return {
        "providers": providers,
        "task_routing": {
            task: [f"{p}/{m}" for p, m in models]
            for task, models in TASK_ROUTING.items()
        },
        "available_count": sum(1 for pid in PROVIDERS if _get_api_key(pid)),
        "total_count": len(PROVIDERS),
    }


async def test_provider_connection(provider: str, api_key: str = None) -> dict:
    """Test a provider's API key by making a minimal request.

    Args:
        provider: Provider ID (e.g. 'gemini', 'groq')
        api_key: If provided, test this key; otherwise test the currently configured key.

    Returns:
        dict with 'success' (bool), 'message' (str), 'model' (str)
    """
    if provider not in PROVIDERS:
        return {"success": False, "message": f"Unknown provider: {provider}"}

    info = PROVIDERS[provider]
    key = api_key or _get_api_key(provider)
    if not key:
        return {"success": False, "message": "No API key configured for this provider."}

    model = info["models"][0]
    style = info["api_style"]
    base_url = info["base_url"]

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if style == "gemini":
                url = f"{base_url}/models/{model}:generateContent?key={key}"
                body = {
                    "contents": [{"role": "user", "parts": [{"text": "Hi"}]}],
                    "generationConfig": {"maxOutputTokens": 5},
                }
                resp = await client.post(url, json=body)
            elif style == "anthropic":
                headers = {
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                }
                body = {
                    "model": model, "max_tokens": 5,
                    "messages": [{"role": "user", "content": "Hi"}],
                }
                resp = await client.post(f"{base_url}/messages", json=body, headers=headers)
            else:
                headers = {
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                }
                body = {
                    "model": model, "max_tokens": 5,
                    "messages": [{"role": "user", "content": "Hi"}],
                }
                resp = await client.post(f"{base_url}/chat/completions", json=body, headers=headers)

        if resp.status_code == 200:
            return {"success": True, "message": f"Connection successful via {model}.", "model": model}
        elif resp.status_code == 401 or resp.status_code == 403:
            return {"success": False, "message": f"Authentication failed (HTTP {resp.status_code}). Check your API key.", "model": model}
        elif resp.status_code == 429:
            return {"success": True, "message": f"Key is valid (rate-limited on test call). Model: {model}.", "model": model}
        else:
            return {"success": False, "message": f"HTTP {resp.status_code}: {resp.text[:200]}", "model": model}
    except httpx.TimeoutException:
        return {"success": False, "message": "Request timed out. The provider may be slow or unreachable.", "model": model}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)[:200]}", "model": model}


# ---------------------------------------------------------------------------
# Provider Implementations
# ---------------------------------------------------------------------------

async def _call_openai_compatible(
    provider: str, model: str, system_prompt: str, user_prompt: str,
    max_tokens: int, temperature: float, timeout: float = 30.0
) -> str:
    """Call an OpenAI-compatible API (Groq, DeepSeek, Mistral, Qwen, OpenAI)."""
    base_url = PROVIDERS[provider]["base_url"]
    api_key = _get_api_key(provider)
    if not api_key:
        raise ValueError(f"No API key for {provider}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    # OpenAI GPT-5+ uses max_completion_tokens; other providers use max_tokens
    if provider == "openai":
        body["max_completion_tokens"] = max_tokens
    else:
        body["max_tokens"] = max_tokens
    body["temperature"] = temperature

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(f"{base_url}/chat/completions", json=body, headers=headers)
        if resp.status_code == 429:
            raise ValueError(f"Rate limited by {provider}")
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()


async def _call_gemini(
    model: str, system_prompt: str, user_prompt: str,
    max_tokens: int, temperature: float, timeout: float = 30.0
) -> str:
    """Call Google Gemini API."""
    api_key = _get_api_key("gemini")
    if not api_key:
        raise ValueError("No API key for gemini")

    base_url = PROVIDERS["gemini"]["base_url"]
    url = f"{base_url}/models/{model}:generateContent?key={api_key}"

    body = {
        "contents": [
            {"role": "user", "parts": [{"text": user_prompt}]}
        ],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        },
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=body)
        if resp.status_code == 429:
            raise ValueError("Rate limited by gemini")
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("Gemini returned no candidates")
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts).strip()


async def _call_anthropic(
    model: str, system_prompt: str, user_prompt: str,
    max_tokens: int, temperature: float, timeout: float = 30.0
) -> str:
    """Call Anthropic Claude API."""
    api_key = _get_api_key("anthropic")
    if not api_key:
        raise ValueError("No API key for anthropic")

    base_url = PROVIDERS["anthropic"]["base_url"]
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_prompt}
        ],
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(f"{base_url}/messages", json=body, headers=headers)
        if resp.status_code == 429:
            raise ValueError("Rate limited by anthropic")
        resp.raise_for_status()
        data = resp.json()
        content = data.get("content", [])
        return "".join(b.get("text", "") for b in content if b.get("type") == "text").strip()


# ---------------------------------------------------------------------------
# Output Cleaning — strip echoed prompts, preambles, and postambles
# ---------------------------------------------------------------------------

import re as _re

# Patterns that indicate a preamble line the AI should not have produced
_PREAMBLE_PATTERNS = [
    r"^(here\s+is|below\s+is|sure[,!]|certainly[,!]|of\s+course[,!]|"
    r"i['']ll\s+write|i\s+will\s+write|let\s+me\s+write|"
    r"this\s+is\s+(?:a|an)\s|following\s+is\s+(?:a|an)\s|"
    r"based\s+on\s+(?:the\s+)?(?:provided\s+)?(?:sources|context|search))",
    r"^(write\s+(?:a|an)\s+\w+.*(?:about|on|regarding)\s*:?)",
    r"^(topic\s*:\s*.{3,})",
    r"^(section\s*:\s*.{3,})",
    r"^(target\s+length\s*:)",
    r"^(requirements?\s*:)",
    r"^(structure\s+for\s+)",
    r"^(use\s+the\s+following\s+sources)",
]

# Patterns that indicate a postamble line
_POSTAMBLE_PATTERNS = [
    r"^(let\s+me\s+know\s+if)",
    r"^(i\s+hope\s+this\s+helps)",
    r"^(please\s+(?:note|review|let\s+me\s+know))",
    r"^(feel\s+free\s+to)",
    r"^(note\s*:\s*(?:this|the|all|please))",
    r"^(disclaimer\s*:\s*)",
    r"^(this\s+(?:text|content|draft)\s+(?:was|is)\s+(?:generated|ai))",
    r"^(if\s+you\s+(?:need|want|have))",
    r"^(would\s+you\s+like\s+me)",
    r"^(i\s+can\s+(?:also|help|adjust))",
    r"^(the\s+above\s+(?:text|content))",
    r"^\-{3,}\s*$",  # horizontal rules often used as separators before postamble
    r"^\*{3,}\s*$",
]

_PREAMBLE_RE = _re.compile("|".join(_PREAMBLE_PATTERNS), _re.IGNORECASE)
_POSTAMBLE_RE = _re.compile("|".join(_POSTAMBLE_PATTERNS), _re.IGNORECASE)


def _clean_ai_output(text: str, original_prompt: str = "") -> str:
    """Strip preambles, postambles, and echoed prompt lines from AI output.

    Args:
        text: The raw text returned by the AI model.
        original_prompt: The user_prompt that was sent (used to detect echoes).

    Returns:
        Cleaned text that starts and ends with actual academic content.
    """
    if not text or not text.strip():
        return text

    lines = text.strip().split("\n")
    cleaned_lines = list(lines)

    # --- Strip preamble lines from the top ---
    # Remove leading blank lines and preamble lines until we hit actual content
    while cleaned_lines:
        stripped = cleaned_lines[0].strip()
        if not stripped:
            cleaned_lines.pop(0)
            continue
        # Check if this line matches a preamble pattern
        if _PREAMBLE_RE.match(stripped):
            cleaned_lines.pop(0)
            continue
        # Check if this line echoes part of the original prompt
        if original_prompt and _is_prompt_echo(stripped, original_prompt):
            cleaned_lines.pop(0)
            continue
        # Check if this line looks like an instruction rather than content
        # (starts with a capital letter, contains "write" or "generate", and
        # doesn't start with ## which would be a heading)
        if not stripped.startswith("#") and _looks_like_instruction(stripped):
            cleaned_lines.pop(0)
            continue
        break

    # --- Strip postamble lines from the bottom ---
    while cleaned_lines:
        stripped = cleaned_lines[-1].strip()
        if not stripped:
            cleaned_lines.pop()
            continue
        if _POSTAMBLE_RE.match(stripped):
            cleaned_lines.pop()
            continue
        # If the last line is a horizontal rule, remove it
        if _re.match(r"^[\-*=_]{3,}\s*$", stripped):
            cleaned_lines.pop()
            continue
        break

    result = "\n".join(cleaned_lines).strip()
    return result if result else text.strip()


def _is_prompt_echo(line: str, prompt: str) -> bool:
    """Check if a line echoes part of the original prompt."""
    line_lower = line.lower().strip()
    prompt_lower = prompt.lower()

    # Check if the line contains a significant substring from the prompt
    # (at least 15 chars to avoid false positives)
    if len(line_lower) >= 15:
        # Check if a chunk of the prompt appears in this line
        for i in range(0, len(prompt_lower) - 15, 5):
            chunk = prompt_lower[i:i + 20]
            if chunk in line_lower:
                return True

    # Check for "Write a [section] about: [topic]" pattern
    if _re.match(r"^write\s+(?:a|an)\s+\w+.*(?:about|on|regarding)\s*:?", line_lower):
        return True

    return False


def _looks_like_instruction(line: str) -> bool:
    """Check if a line looks like an instruction rather than academic content."""
    line_lower = line.lower().strip()
    # Lines that start with instruction-like verbs
    instruction_starts = (
        "write ", "generate ", "create ", "produce ", "draft ",
        "target length", "requirements", "structure for",
        "use the following", "write the ",
    )
    for start in instruction_starts:
        if line_lower.startswith(start):
            return True
    return False


# ---------------------------------------------------------------------------
# Unified Generation with Auto-Routing & Fallback
# ---------------------------------------------------------------------------

async def generate_text(
    user_prompt: str,
    task_type: str = "general",
    system_prompt: Optional[str] = None,
    max_tokens: int = 2000,
    temperature: float = 0.7,
    timeout: float = 30.0,
) -> tuple:
    """Generate text using the best available AI model for the task.

    Auto-routes to the preferred model for the task type, with automatic
    fallback to the next model if the current one fails.

    Returns:
        (generated_text, model_display_name) on success
        (None, None) if all models fail — caller should use template fallback
    """
    if system_prompt is None:
        system_prompt = SYSTEM_PROMPTS.get(task_type, SYSTEM_PROMPTS["general"])

    routing = TASK_ROUTING.get(task_type, TASK_ROUTING["general"])
    errors = []

    for provider, model in routing:
        api_key = _get_api_key(provider)
        if not api_key:
            errors.append(f"{provider}/{model}: no API key")
            continue

        try:
            style = PROVIDERS[provider]["api_style"]

            if style == "gemini":
                text = await _call_gemini(
                    model, system_prompt, user_prompt,
                    max_tokens, temperature, timeout
                )
            elif style == "anthropic":
                text = await _call_anthropic(
                    model, system_prompt, user_prompt,
                    max_tokens, temperature, timeout
                )
            else:
                text = await _call_openai_compatible(
                    provider, model, system_prompt, user_prompt,
                    max_tokens, temperature, timeout
                )

            if text and len(text) > 10:
                # Clean output: strip echoed prompts, preambles, postambles
                if task_type not in ("grammar_fix", "paraphrase", "academic_enhance"):
                    text = _clean_ai_output(text, user_prompt)
                else:
                    # For text-enhancement tasks, only strip preambles/postambles
                    # (don't check for prompt echoes — the input IS the text)
                    text = _clean_ai_output(text, "")
                display = f"{PROVIDERS[provider]['display_name']} ({model})"
                print(f"[AI Router] Task '{task_type}' served by {display}")
                return text, display

        except Exception as e:
            err_msg = str(e)[:150]
            errors.append(f"{provider}/{model}: {err_msg}")
            print(f"[AI Router] {provider}/{model} failed: {err_msg}")
            continue

    print(f"[AI Router] All models failed for task '{task_type}'. Errors: {errors}")
    return None, None


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

async def enhance_text_with_ai(text: str, task_type: str) -> tuple:
    """Send text to AI for enhancement (grammar fix, paraphrase, academic enhance).

    Returns:
        (enhanced_text, model_display_name) on success
        (None, None) if all models fail
    """
    if not text or not text.strip():
        return None, None

    system_prompt = SYSTEM_PROMPTS.get(task_type, SYSTEM_PROMPTS["general"])
    result, model = await generate_text(
        user_prompt=text,
        task_type=task_type,
        system_prompt=system_prompt,
        max_tokens=3000,
        temperature=0.3,
    )
    return result, model


async def generate_academic_text(
    topic: str,
    section_type: str,
    context: str,
    max_words: int = 1000,
) -> tuple:
    """Generate academic text for a specific section type.

    Args:
        topic: The research topic
        section_type: literature_review, introduction, abstract, conclusion, summary
        context: Additional context (source summaries, extracted data, etc.)
        max_words: Target word count

    Returns:
        (generated_text, model_display_name) on success
        (None, None) if all models fail
    """
    # Section-specific structural guidance
    structure_guides = {
        "literature_review": (
            "STRUCTURE for Literature Review:\n"
            "- Begin with ## Literature Review: {topic}\n"
            "- Write a framing introduction paragraph (no sub-heading) that scope\n"
            "  the review, states the number of sources, and outlines the thematic\n"
            "  organization.\n"
            "- Create ### sub-headings for each thematic cluster (e.g., ### Institutional\n"
            "  Quality and Governance, ### Economic Growth Determinants). Group 2–4\n"
            "  papers per theme. Under each sub-heading, write 2–3 paragraphs that\n"
            "  synthesize findings, compare methodologies, and evaluate convergence.\n"
            "- Use #### sub-sub-headings only if a theme has enough papers to warrant\n"
            "  further division.\n"
            "- End with ### Synthesis and Research Gaps — summarise overarching\n"
            "  patterns, note contradictions, identify methodological gaps, and\n"
            "  propose directions for future research.\n"
        ),
        "introduction": (
            "STRUCTURE for Introduction:\n"
            "- Begin with ## Introduction\n"
            "- Paragraph 1: Broad context and significance of the topic.\n"
            "- Paragraph 2: Narrow to the specific research problem and gap.\n"
            "- Use ### sub-headings if the introduction covers multiple dimensions\n"
            "  (e.g., ### Background, ### Research Gap, ### Objectives).\n"
            "- Paragraph 3: State the research question(s) or objectives clearly.\n"
            "- Paragraph 4: Briefly preview the structure of the paper.\n"
        ),
        "abstract": (
            "STRUCTURE for Abstract (150–250 words, single paragraph unless\n"
            "the target journal requires structured abstracts):\n"
            "- Begin with ## Abstract\n"
            "- Write ONE dense paragraph covering: (1) purpose/objective, (2) data\n"
            "  and methodology, (3) key findings, (4) implications/contribution.\n"
            "- Do NOT use sub-headings for an unstructured abstract.\n"
            "- If the journal requires a structured abstract, use ### sub-headings:\n"
            "  ### Purpose, ### Methodology, ### Findings, ### Implications.\n"
        ),
        "conclusion": (
            "STRUCTURE for Conclusion:\n"
            "- Begin with ## Conclusion\n"
            "- Paragraph 1: Restate the research problem and summarise key findings.\n"
            "- Use ### sub-headings if covering multiple themes (e.g., ### Summary\n"
            "  of Findings, ### Policy Implications, ### Limitations, ### Future\n"
            "  Research).\n"
            "- Paragraph 2+: Discuss implications, acknowledge limitations, and\n"
            "  propose avenues for future research.\n"
            "- Final paragraph: Closing statement on the contribution and broader\n"
            "  significance.\n"
        ),
        "summary": (
            "STRUCTURE for Summary:\n"
            "- Begin with ## Summary\n"
            "- Write 2–3 paragraphs that distil the main arguments and findings.\n"
            "- Use ### sub-headings if the summary spans multiple themes.\n"
            "- End with a concluding paragraph that highlights the take-away\n"
            "  message.\n"
        ),
    }

    section_label = section_type.replace("_", " ")
    structure_guide = structure_guides.get(section_type, "")

    user_prompt = (
        f"SECTION TYPE: {section_label}\n"
        f"RESEARCH TOPIC: {topic}\n"
        f"TARGET LENGTH: approximately {max_words} words.\n\n"
        f"{structure_guide}\n"
        f"SOURCE MATERIAL — cite ONLY these using APA in-text format "
        f"[e.g., (Author, Year)]. Do NOT fabricate references:\n\n"
        f"{context}\n\n"
        f"FORMATTING RULES:\n"
        f"- Markdown headings (##, ###, ####) as specified above.\n"
        f"- Formal academic English for Q1–Q3 indexed journals.\n"
        f"- Synthesize thematically; do NOT list papers sequentially.\n"
        f"- Each paragraph: topic sentence, evidence with citations, analysis.\n"
        f"- Clear beginning (framing), middle (analysis), end (synthesis).\n\n"
        f"BEGIN OUTPUT NOW — start directly with the ## heading. "
        f"Do NOT repeat these instructions."
    )

    max_tokens = min(max_words * 4, 6000)

    return await generate_text(
        user_prompt=user_prompt,
        task_type="academic_drafting",
        max_tokens=max_tokens,
        temperature=0.7,
        timeout=90.0,
    )
