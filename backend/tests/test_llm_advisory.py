"""Tests for the LLM advisory service."""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.llm_advisory import explain_bind_failure


@pytest.mark.asyncio
async def test_no_key_returns_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM_API_KEY not set returns an error."""
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    result = await explain_bind_failure(["--title", "sample"], [])
    assert "error" in result
    assert "not set" in result["error"]


@pytest.mark.asyncio
async def test_openai_key_returns_advisory_on_success(monkeypatch: pytest.MonkeyPatch, mocker) -> None:
    """OpenAI key returns advisory when provider responds 200."""
    monkeypatch.setenv("LLM_API_KEY", "sk-test123")

    async def _post_success(url, **kwargs):
        return AsyncMock()
    # Build a real-ish response
    from unittest.mock import MagicMock
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json = lambda: {
        "choices": [{"message": {"content": "Failed to bind argv because --title is not a recognized flag"}}]
    }

    with patch("app.services.llm_advisory.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await explain_bind_failure(["--title", "sample"], [])
        assert "advisory" in result
        assert "Failed to bind" in result["advisory"]


@pytest.mark.asyncio
async def test_anthropic_key_inferred(monkeypatch: pytest.MonkeyPatch, mocker) -> None:
    """Anthropic key is inferred from key prefix."""
    monkeypatch.setenv("LLM_API_KEY", "ant-test123")

    from unittest.mock import MagicMock
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json = lambda: {
        "content": [{"text": "The --title flag is not recognized by any surface handler"}]
    }

    with patch("app.services.llm_advisory.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await explain_bind_failure(["--title", "sample"], [])
        assert "advisory" in result
        assert "not recognized" in result["advisory"]


@pytest.mark.asyncio
async def test_invalid_provider_returns_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unknown key prefix returns error."""
    monkeypatch.setenv("LLM_API_KEY", "randomkey123")
    result = await explain_bind_failure(["--title", "sample"], [])
    assert "error" in result
