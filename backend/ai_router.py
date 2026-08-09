"""
THEeye AI Router — Multi-model text generation with auto-routing and fallback.

Supports models with FREE API tiers:
  - Google Gemini  (gemini-2.0-flash, gemini-1.5-flash, gemini-1.5-pro)
  - Groq           (Llama 3.3 70B, Mixtral 8x7B, Gemma 2)
  - DeepSeek       (deepseek-chat, deepseek-coder)
  - Mistral AI     (mistral-small-latest, mistral-tiny)
  - Qwen / DashScope (qwen-turbo, qwen-plus)

Also supports PAID models (require API keys):
  - OpenAI         (gpt-5, gpt-4o)
  - Anthropic      (claude-3-5-sonnet, claude-3-opus)

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
        "models": ["qwen-turbo", "qwen-plus"],
        "free_tier": True,
        "api_style": "openai",
    },
    "openai": {
        "display_name": "OpenAI (GPT-5)",
        "env_key": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini"],
        "free_tier": False,
        "api_style": "openai",
    },
    "anthropic": {
        "display_name": "Anthropic (Claude)",
        "env_key": "ANTHROPIC_API_KEY",
        "base_url": "https://api.anthropic.com/v1",
        "models": ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
        "free_tier": False,
        "api_style": "anthropic",
    },
}

# ---------------------------------------------------------------------------
# Task Routing — task_type -> ordered list of (provider, model)
# ---------------------------------------------------------------------------

TASK_ROUTING = {
    "academic_drafting": [
        ("deepseek", "deepseek-chat"),
        ("gemini", "gemini-1.5-pro"),
        ("groq", "llama-3.3-70b-versatile"),
        ("mistral", "mistral-small-latest"),
        ("qwen", "qwen-plus"),
        ("openai", "gpt-4o"),
        ("anthropic", "claude-3-5-sonnet-20241022"),
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
        ("deepseek", "deepseek-chat"),
        ("gemini", "gemini-1.5-pro"),
        ("groq", "llama-3.3-70b-versatile"),
        ("mistral", "mistral-small-latest"),
        ("qwen", "qwen-plus"),
        ("openai", "gpt-4o"),
        ("anthropic", "claude-3-5-sonnet-20241022"),
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
        "You are an expert academic writer. Generate a well-structured, scholarly "
        "text based on the user's request. Use formal academic English, include "
        "in-text citations in APA format where appropriate, and organize content "
        "with clear headings. Do NOT fabricate sources — only cite the sources "
        "provided in the context. Return the text in Markdown format."
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
        "You are an expert academic researcher and writer. Based on the user's "
        "prompt and the provided search results, generate a well-structured "
        "academic text with in-text citations (APA format). Only cite the "
        "sources provided. Return the text in Markdown format."
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
    """Get the API key for a provider from environment variables."""
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
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

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
    user_prompt = (
        f"Write a {section_type.replace('_', ' ')} about: {topic}\n\n"
        f"Target length: approximately {max_words} words.\n\n"
        f"Use the following sources and data as evidence. Only cite these sources:\n\n"
        f"{context}\n\n"
        f"Write the {section_type.replace('_', ' ')} now:"
    )

    max_tokens = min(max_words * 3, 4000)

    return await generate_text(
        user_prompt=user_prompt,
        task_type="academic_drafting",
        max_tokens=max_tokens,
        temperature=0.7,
    )
