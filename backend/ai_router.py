"""
THEeye AI Router — Multi-model text generation with auto-routing and fallback.

Supports models with FREE API tiers:
  - Google Gemini  (gemini-2.0-flash, gemini-1.5-flash, gemini-1.5-pro)
  - Groq           (Llama 3.3 70B, Mixtral 8x7B, Gemma 2)
  - DeepSeek       (deepseek-chat, deepseek-coder)
  - Mistral AI     (mistral-small-latest, mistral-tiny)
  - Qwen / DashScope (qwen-max, qwen-plus, qwen-turbo)
  - Doubao         (doubao-seed-1.6, doubao-seed-1.6-flash) — ByteDance Volcano Engine

Also supports PAID models (require API keys):
  - OpenAI         (gpt-5, gpt-5-mini, gpt-4o)
  - Anthropic      (claude-sonnet-4, claude-3-5-sonnet, claude-3-haiku)

Academic drafting priority: Claude Sonnet 4 > GPT-5 > Qwen-Max > Doubao-Seed-1.6 >
  Claude 3.5 Sonnet > GPT-4o > Qwen-Plus > Doubao-Flash > DeepSeek > Gemini > Groq > Mistral

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
    "doubao": {
        "display_name": "Doubao (ByteDance Volcano Engine)",
        "env_key": "DOUBAO_API_KEY",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "models": ["doubao-seed-1-6-251015", "doubao-seed-1-6-flash-250828"],
        "free_tier": True,
        "api_style": "openai",
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
        ("doubao", "doubao-seed-1-6-251015"),
        ("anthropic", "claude-3-5-sonnet-20241022"),
        ("openai", "gpt-4o"),
        ("qwen", "qwen-plus"),
        ("doubao", "doubao-seed-1-6-flash-250828"),
        ("deepseek", "deepseek-chat"),
        ("gemini", "gemini-1.5-pro"),
        ("groq", "llama-3.3-70b-versatile"),
        ("mistral", "mistral-small-latest"),
    ],
    "topic_suggestion": [
        ("groq", "llama-3.3-70b-versatile"),
        ("gemini", "gemini-2.0-flash"),
        ("doubao", "doubao-seed-1-6-flash-250828"),
        ("mistral", "mistral-small-latest"),
        ("deepseek", "deepseek-chat"),
        ("qwen", "qwen-turbo"),
    ],
    "roadmap_generation": [
        ("gemini", "gemini-2.0-flash"),
        ("doubao", "doubao-seed-1-6-flash-250828"),
        ("deepseek", "deepseek-chat"),
        ("qwen", "qwen-turbo"),
        ("groq", "llama-3.3-70b-versatile"),
    ],
    "grammar_fix": [
        ("gemini", "gemini-2.0-flash"),
        ("doubao", "doubao-seed-1-6-flash-250828"),
        ("mistral", "mistral-tiny"),
        ("groq", "gemma2-9b-it"),
        ("deepseek", "deepseek-chat"),
    ],
    "paraphrase": [
        ("deepseek", "deepseek-chat"),
        ("doubao", "doubao-seed-1-6-251015"),
        ("gemini", "gemini-1.5-pro"),
        ("qwen", "qwen-plus"),
        ("groq", "llama-3.3-70b-versatile"),
    ],
    "academic_enhance": [
        ("deepseek", "deepseek-chat"),
        ("doubao", "doubao-seed-1-6-251015"),
        ("gemini", "gemini-1.5-pro"),
        ("groq", "llama-3.3-70b-versatile"),
        ("mistral", "mistral-small-latest"),
    ],
    "code_generation": [
        ("deepseek", "deepseek-coder"),
        ("doubao", "doubao-seed-1-6-251015"),
        ("qwen", "qwen-plus"),
        ("gemini", "gemini-2.0-flash"),
        ("groq", "llama-3.3-70b-versatile"),
    ],
    "quick_generate": [
        ("anthropic", "claude-sonnet-4-20250514"),
        ("openai", "gpt-5"),
        ("qwen", "qwen-max"),
        ("doubao", "doubao-seed-1-6-251015"),
        ("anthropic", "claude-3-5-sonnet-20241022"),
        ("openai", "gpt-4o"),
        ("qwen", "qwen-plus"),
        ("doubao", "doubao-seed-1-6-flash-250828"),
        ("deepseek", "deepseek-chat"),
        ("gemini", "gemini-1.5-pro"),
        ("groq", "llama-3.3-70b-versatile"),
        ("mistral", "mistral-small-latest"),
    ],
    "general": [
        ("gemini", "gemini-2.0-flash"),
        ("groq", "llama-3.3-70b-versatile"),
        ("doubao", "doubao-seed-1-6-flash-250828"),
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
        "You are an expert academic writer producing publication-quality text for "
        "Q1-Q3 indexed journals.\n\n"
        "=== OUTPUT DISCIPLINE (CRITICAL) ===\n"
        "1. Start DIRECTLY with a ## heading. NO preambles like 'Here is...' or 'Sure.'\n"
        "2. End with the last content paragraph. NO postambles like 'Let me know...'\n"
        "3. Do NOT repeat, echo, or reference any part of the prompt.\n"
        "4. Do NOT include labels like 'SECTION TYPE', 'RESEARCH TOPIC', 'SOURCE MATERIAL',\n"
        "   'FORMATTING RULES', 'BEGIN OUTPUT', or 'TARGET LENGTH'.\n"
        "5. Do NOT list the sources back. Use them ONLY for in-text citations.\n"
        "6. Return ONLY the academic text in Markdown. No meta-commentary.\n\n"
        "=== HEADING STRUCTURE (MANDATORY) ===\n"
        "You MUST use this heading hierarchy:\n"
        "  ## Main Section Title\n"
        "  [1 framing paragraph]\n"
        "  ### Sub-Heading 1\n"
        "  [2-3 paragraphs]\n"
        "  ### Sub-Heading 2\n"
        "  [2-3 paragraphs]\n"
        "  ### Synthesis and Research Gaps\n"
        "  [1-2 closing paragraphs]\n\n"
        "For a Literature Review, use thematic ### sub-headings like:\n"
        "  ### Institutional Quality and Governance\n"
        "  ### Economic Growth Determinants\n"
        "  ### Synthesis and Research Gaps\n\n"
        "For an Introduction:\n"
        "  ### Background and Context\n"
        "  ### Research Problem and Gap\n"
        "  ### Objectives and Contribution\n\n"
        "For a Conclusion:\n"
        "  ### Summary of Key Findings\n"
        "  ### Policy Implications\n"
        "  ### Limitations and Future Research\n\n"
        "=== ACADEMIC STANDARDS ===\n"
        "- Formal, objective, scholarly English (third person, hedged claims).\n"
        "- APA in-text citations: (Author, Year). Cite ONLY provided sources.\n"
        "- NEVER fabricate references.\n"
        "- Synthesize thematically. Do NOT list papers sequentially.\n"
        "- 4-8 sentences per paragraph with topic sentence, evidence, analysis.\n"
        "- Clear beginning (framing), middle (analysis), end (synthesis)."
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
        "You are an expert academic researcher and writer.\n\n"
        "=== OUTPUT DISCIPLINE (CRITICAL) ===\n"
        "1. Start DIRECTLY with a ## heading. NO preambles.\n"
        "2. End with the last content paragraph. NO postambles.\n"
        "3. Do NOT repeat or echo the prompt. Do NOT include source lists.\n"
        "4. Return ONLY the academic text in Markdown.\n\n"
        "=== HEADING STRUCTURE (MANDATORY) ===\n"
        "  ## Main Section Title\n"
        "  ### Thematic Sub-Headings (at least 2-3)\n"
        "  ### Synthesis and Research Gaps\n\n"
        "=== ACADEMIC STANDARDS ===\n"
        "- Formal scholarly English. APA in-text citations: (Author, Year).\n"
        "- Cite ONLY provided sources. NEVER fabricate.\n"
        "- Synthesize thematically, not sequentially."
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
    r"^(section\s*(?:type)?\s*:\s*.{3,})",
    r"^(research\s+topic\s*:\s*.{3,})",
    r"^(target\s+length\s*:)",
    r"^(requirements?\s*:)",
    r"^(formatting\s+rules?\s*:)",
    r"^(structure\s+for\s+)",
    r"^(use\s+the\s+following\s+sources)",
    r"^(source\s+material)",
    r"^(begin\s+output)",
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
        # NEVER strip markdown headings (lines starting with #)
        if stripped.startswith("#"):
            break
        # Check if this line matches a preamble pattern
        if _PREAMBLE_RE.match(stripped):
            cleaned_lines.pop(0)
            continue
        # Check if this line echoes part of the original prompt
        if original_prompt and _is_prompt_echo(stripped, original_prompt):
            cleaned_lines.pop(0)
            continue
        # Check if this line looks like an instruction rather than content
        if _looks_like_instruction(stripped):
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


# Patterns for prompt residues that can appear ANYWHERE in the output
_PROMPT_RESIDUE_PATTERNS = [
    _re.compile(r"^section\s*(?:type)?\s*:\s*", _re.IGNORECASE),
    _re.compile(r"^research\s+topic\s*:\s*", _re.IGNORECASE),
    _re.compile(r"^target\s+length\s*:\s*", _re.IGNORECASE),
    _re.compile(r"^formatting\s+rules?\s*:", _re.IGNORECASE),
    _re.compile(r"^begin\s+output\b", _re.IGNORECASE),
    _re.compile(r"^source\s+material\b", _re.IGNORECASE),
    _re.compile(r"^structure\s+for\s+", _re.IGNORECASE),
    _re.compile(r"^use\s+the\s+following\s+sources?", _re.IGNORECASE),
    _re.compile(r"^requirements?\s*:\s*", _re.IGNORECASE),
    # Source-list entries: [1] Author (Year). Title. Journal.
    _re.compile(r"^\[\d+\]\s+[A-Z][a-zA-Z]+.*\(\d{4}\)"),
    # Indented "Abstract:" lines from source material
    _re.compile(r"^\s{4,}abstract\s*:", _re.IGNORECASE),
]

# Lines that look like instructions rather than academic content
_INSTRUCTION_LINE_RE = _re.compile(
    r"^(write|generate|create|produce|draft)\s+(?:a|an|the)\s+",
    _re.IGNORECASE,
)


def _strip_prompt_residues(text: str, original_prompt: str = "") -> str:
    """Remove prompt echoes and source-material residues from ANYWHERE in the text.

    Unlike _clean_ai_output (which only strips top/bottom), this function scans
    every line and removes:
      - Prompt section headers (SECTION TYPE:, RESEARCH TOPIC:, SOURCE MATERIAL, etc.)
      - Source-list entries ([1] Author (Year). Title. Journal.)
      - Indented Abstract: lines from source material
      - Instruction-like lines (Write a..., Generate a..., etc.)
      - Near-exact copies of prompt instruction lines

    Also collapses excessive blank lines left behind by removed lines.
    """
    if not text or not text.strip():
        return text

    lines = text.split("\n")
    kept: list[str] = []

    # Pre-extract prompt instruction lines for near-exact matching
    prompt_lines_lower = set()
    if original_prompt:
        for pl in original_prompt.split("\n"):
            pl_lower = pl.lower().strip()
            if len(pl_lower) >= 30:
                prompt_lines_lower.add(pl_lower)

    for line in lines:
        stripped = line.strip()

        # Always keep blank lines (we'll collapse extras later)
        if not stripped:
            kept.append(line)
            continue

        # NEVER remove markdown headings
        if stripped.startswith("#"):
            kept.append(line)
            continue

        # Check against residue patterns
        is_residue = False
        for pat in _PROMPT_RESIDUE_PATTERNS:
            if pat.match(stripped):
                is_residue = True
                break

        if not is_residue and _INSTRUCTION_LINE_RE.match(stripped):
            is_residue = True

        # Check for near-exact prompt line matches
        if not is_residue and prompt_lines_lower:
            line_lower = stripped.lower()
            if len(line_lower) >= 30:
                for pl in prompt_lines_lower:
                    if line_lower == pl:
                        is_residue = True
                        break
                    # Check if a 50-char chunk of the prompt line appears in this line
                    if len(pl) >= 50:
                        for i in range(0, len(pl) - 50, 10):
                            if pl[i:i + 50] in line_lower:
                                is_residue = True
                                break
                    if is_residue:
                        break

        if not is_residue:
            kept.append(line)

    # Collapse 3+ consecutive blank lines into 2
    result_lines: list[str] = []
    blank_count = 0
    for line in kept:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 2:
                result_lines.append(line)
        else:
            blank_count = 0
            result_lines.append(line)

    # Strip leading/trailing blanks
    while result_lines and not result_lines[0].strip():
        result_lines.pop(0)
    while result_lines and not result_lines[-1].strip():
        result_lines.pop()

    result = "\n".join(result_lines).strip()
    return result if result else text.strip()


def _is_prompt_echo(line: str, prompt: str) -> bool:
    """Check if a line echoes part of the original prompt.

    Conservative: only flags lines that clearly repeat prompt LABELS
    (e.g., 'SECTION TYPE:', 'RESEARCH TOPIC:', 'TARGET LENGTH:') or
    lines that are near-exact copies of prompt instruction lines.
    Does NOT flag headings or content that merely shares the topic name.
    """
    line_lower = line.lower().strip()

    # Only check for prompt label echoes — NOT topic name matches
    prompt_labels = [
        "section type:", "research topic:", "target length:",
        "formatting rules:", "source material", "begin output",
        "requirements:", "structure for",
    ]
    for label in prompt_labels:
        if line_lower.startswith(label):
            return True

    # Check for "Write a [section] about: [topic]" pattern (old prompt format)
    if _re.match(r"^write\s+(?:a|an)\s+\w+.*(?:about|on|regarding)\s*:?", line_lower):
        return True

    # Check for near-exact match of a full prompt line (40+ chars)
    # This catches cases where the AI copies an entire instruction line
    if len(line_lower) >= 40:
        prompt_lines = [l.lower().strip() for l in prompt.split("\n") if len(l.strip()) >= 40]
        for pl in prompt_lines:
            # Check if the line is >80% similar to a prompt line
            if line_lower == pl:
                return True
            # Check for substantial overlap (50+ char substring)
            if len(pl) >= 50:
                for i in range(0, len(pl) - 50, 10):
                    chunk = pl[i:i + 50]
                    if chunk in line_lower:
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


def _ensure_heading(text: str, section_type: str, topic: str) -> str:
    """Ensure the AI output starts with a proper ## heading.

    If the output doesn't start with a markdown heading, prepend one
    based on the section type and topic.
    """
    if not text or not text.strip():
        return text

    stripped = text.strip()
    if stripped.startswith("#"):
        return text  # Already has a heading

    section_labels = {
        "literature_review": f"## Literature Review: {topic}",
        "introduction": "## Introduction",
        "abstract": "## Abstract",
        "conclusion": "## Conclusion",
        "summary": "## Summary",
    }
    heading = section_labels.get(section_type, f"## {topic}")

    return f"{heading}\n\n{stripped}"


# Default sub-heading sets for sections that lack them
_SUBHEADING_SETS = {
    "literature_review": [
        "### Conceptual Framework and Theoretical Perspectives",
        "### Empirical Evidence and Thematic Synthesis",
        "### Methodological Approaches in the Literature",
        "### Synthesis and Research Gaps",
    ],
    "introduction": [
        "### Background and Context",
        "### Research Problem and Gap",
        "### Objectives and Contribution",
    ],
    "conclusion": [
        "### Summary of Key Findings",
        "### Policy and Practical Implications",
        "### Limitations and Future Research",
    ],
    "summary": [
        "### Main Arguments",
        "### Key Findings",
        "### Concluding Remarks",
    ],
}


def _ensure_subheadings(text: str, section_type: str) -> str:
    """Ensure the text has ### sub-headings when the section type warrants them.

    If the AI output has a ## heading but no ### sub-headings, this function
    splits the body paragraphs and inserts thematic ### sub-headings.

    For abstracts (single-paragraph sections), sub-headings are NOT added.
    """
    if not text or not text.strip():
        return text

    # Abstracts are typically a single paragraph — skip
    if section_type == "abstract":
        return text

    subheadings = _SUBHEADING_SETS.get(section_type)
    if not subheadings:
        return text  # Unknown section type — don't modify

    lines = text.split("\n")

    # Count existing ### sub-headings (exclude the main ## heading)
    has_subheadings = any(
        line.strip().startswith("###") for line in lines
    )
    if has_subheadings:
        return text  # Already has sub-headings — respect AI's structure

    # Split into: main_heading_part + body_paragraphs
    main_heading_line = None
    body_start_idx = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("#"):
            main_heading_line = line
            # Skip blank lines after heading
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            body_start_idx = j
            break

    # Collect body paragraphs (paragraphs separated by blank lines)
    body_lines = lines[body_start_idx:]
    paragraphs: list[list[str]] = []
    current_para: list[str] = []

    for line in body_lines:
        if line.strip() == "":
            if current_para:
                paragraphs.append(current_para)
                current_para = []
        else:
            current_para.append(line)
    if current_para:
        paragraphs.append(current_para)

    # Need at least 3 paragraphs to warrant sub-headings
    if len(paragraphs) < 3:
        return text

    # Distribute paragraphs across sub-headings
    num_subs = min(len(subheadings), len(paragraphs))
    # Group paragraphs: first section gets intro + first theme, last gets synthesis
    result_lines: list[str] = []

    if main_heading_line is not None:
        result_lines.append(main_heading_line)
        result_lines.append("")

    # Distribute paragraphs evenly across available sub-headings.
    # Ensures every sub-heading (including the last "Synthesis") gets a group.
    num_groups = min(num_subs, len(paragraphs))
    chunk_size = len(paragraphs) // num_groups
    remainder = len(paragraphs) % num_groups

    groups: list = []
    start = 0
    for i in range(num_groups):
        size = chunk_size + (1 if i < remainder else 0)
        end = start + size
        groups.append(paragraphs[start:end])
        start = end

    for i, group in enumerate(groups):
        if i < len(subheadings):
            result_lines.append(subheadings[i])
            result_lines.append("")
        # group is a list of paragraphs; each paragraph is a list of line strings
        for para in group:
            for line in para:
                result_lines.append(line)
            result_lines.append("")  # blank line between paragraphs

    # Strip trailing blank lines
    while result_lines and isinstance(result_lines[-1], str) and not result_lines[-1].strip():
        result_lines.pop()

    return "\n".join(result_lines)


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
    section_label = section_type.replace("_", " ")

    # Minimal user prompt — structural guidance lives in the system prompt.
    # Less instruction text = less surface for the AI to echo back.
    user_prompt = (
        f"Write a {section_label} on \"{topic}\" (~{max_words} words).\n"
        f"Use ONLY these sources for citations (APA format):\n{context}"
    )

    max_tokens = min(max_words * 4, 6000)

    text, model = await generate_text(
        user_prompt=user_prompt,
        task_type="academic_drafting",
        max_tokens=max_tokens,
        temperature=0.7,
        timeout=90.0,
    )

    if text:
        # Layer 1: _clean_ai_output already ran inside generate_text
        #         (strips top/bottom preambles & postambles)
        # Layer 2: Strip prompt residues from ANYWHERE in the text
        text = _strip_prompt_residues(text, user_prompt)
        # Layer 3: Ensure the output starts with a proper ## heading
        text = _ensure_heading(text, section_type, topic)
        # Layer 4: Ensure ### sub-headings exist (injects if missing)
        text = _ensure_subheadings(text, section_type)

    return text, model
