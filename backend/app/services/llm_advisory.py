"""LLM advisory service for optional bind-failure explanations.

When LLM_API_KEY is set, calls the configured provider to produce a short
explanation of why an argv-bind failed.  Missing or failing provider calls
return an error and do not invent a successful explanation.
"""

from __future__ import annotations

import os
from typing import Optional

import httpx

BASE_URLS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
}


def _provider_from_key(key: str) -> str:
    """Determine the provider prefix from the API key."""
    key = key.strip()
    if key.startswith("sk-"):  # OpenAI
        return "openai"
    if key.startswith("ant-"):  # Anthropic
        return "anthropic"
    return "openai"  # fallback


def _auth_headers(provider: str, key: str) -> dict:
    """Return auth headers for the given provider."""
    if provider == "anthropic":
        return {"x-api-key": key, "content-type": "application/json"}
    # OpenAI
    return {"Authorization": f"Bearer {key}", "content-type": "application/json"}


async def explain_bind_failure(
    argv: list[str],
    surfaces: list[dict],
    provider: Optional[str] = None,
) -> dict:
    """Request an LLM explanation of a bind failure.

    Parameters
    ----------
    argv : list[str]
        The user-supplied command arguments that failed to bind.
    surfaces : list[dict]
        The surface inventory from the analysis.
    provider : str | None
        Explicit provider ("openai" or "anthropic").  When ``None`` the
        provider is inferred from ``LLM_API_KEY``.

    Returns
    -------
    dict
        ``{"advisory": <explanation string>}`` on success, or
        ``{"error": <error string>}`` when the key is missing, the provider
        cannot be determined, or the call fails.
    """
    key = os.getenv("LLM_API_KEY")
    if not key:
        return {"error": "LLM_API_KEY not set"}

    prov = provider or _provider_from_key(key)
    url = BASE_URLS.get(prov)
    if not url:
        return {"error": f"unknown provider: {prov}"}

    headers = _auth_headers(prov, key)

    inventory_summary = "\n".join(
        f"- {s.get('id', '?')}: {s.get('kind', '?')} {s.get('module', '?')}"
        for s in surfaces
    )

    prompt = f"""The following command-line arguments failed to bind to any declared surface.

User argv: {" ".join(argv)}

Available surfaces:
{inventory_summary}

Please give a concise one-sentence explanation of why the bind failed.
Keep it under 30 words. Do not invent a successful binding.
"""

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, headers=headers, json={
                "model": "gpt-4o-mini" if prov == "openai" else "claude-3-haiku-20240307",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 60,
                "temperature": 0,
            })
            if resp.status_code != 200:
                return {"error": f"provider responded {resp.status_code}"}
            data = resp.json()
            if prov == "openai":
                advisory = data["choices"][0]["message"]["content"].strip()
            else:
                advisory = data["content"][0]["text"].strip()
            return {"advisory": advisory}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"provider call failed: {exc}"}
