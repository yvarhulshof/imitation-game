"""Tests for LLM client functionality."""

import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

from app.ai.llm_client import (
    LLMClient,
    LLMError,
    LLMTimeoutError,
    LLMParseError,
    LLMCircuitBreakerError,
)


class TestLLMClientInit:
    """Tests for LLMClient initialization."""

    def test_init_with_defaults(self):
        """Should use default config values."""
        client = LLMClient()
        assert client.model == "gemini-2.0-flash"
        assert client.timeout == 10
        assert client.max_retries == 2

    def test_init_with_custom_values(self):
        """Should accept custom configuration."""
        client = LLMClient(
            api_key="test-key",
            model="custom-model",
            timeout=30,
            max_retries=5,
        )
        assert client.api_key == "test-key"
        assert client.model == "custom-model"
        assert client.timeout == 30
        assert client.max_retries == 5


class TestLLMClientJSONParsing:
    """Tests for JSON response parsing."""

    def test_parse_valid_json(self):
        """Should parse valid JSON directly."""
        client = LLMClient()
        result = client._parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_json_in_code_block(self):
        """Should extract JSON from markdown code block."""
        client = LLMClient()
        response = '''```json
{"key": "value", "number": 42}
```'''
        result = client._parse_json_response(response)
        assert result == {"key": "value", "number": 42}

    def test_parse_json_in_unlabeled_code_block(self):
        """Should extract JSON from unlabeled code block."""
        client = LLMClient()
        response = '''```
{"target": "player_123"}
```'''
        result = client._parse_json_response(response)
        assert result == {"target": "player_123"}

    def test_parse_json_embedded_in_text(self):
        """Should find JSON object in surrounding text."""
        client = LLMClient()
        response = '''Here's my response:
{"send": true, "message": "Hello everyone!"}
That's my decision.'''
        result = client._parse_json_response(response)
        assert result == {"send": True, "message": "Hello everyone!"}

    def test_parse_invalid_json_raises(self):
        """Should raise JSONDecodeError for invalid JSON."""
        client = LLMClient()
        with pytest.raises(json.JSONDecodeError):
            client._parse_json_response("This is not JSON at all")

    def test_parse_nested_json(self):
        """Should parse nested JSON structures."""
        client = LLMClient()
        response = '{"target": "p1", "reasoning": {"suspicion": "high", "evidence": ["vote", "chat"]}}'
        result = client._parse_json_response(response)
        assert result["target"] == "p1"
        assert result["reasoning"]["suspicion"] == "high"


class TestLLMClientCircuitBreaker:
    """Tests for circuit breaker functionality."""

    def test_circuit_breaker_tracks_failures(self):
        """Should track consecutive failures."""
        client = LLMClient()
        assert client._consecutive_failures == 0
        client._consecutive_failures = 3
        assert client._consecutive_failures == 3

    def test_circuit_breaker_reset(self):
        """Should be able to reset circuit breaker."""
        client = LLMClient()
        client._consecutive_failures = 5
        client.reset_circuit_breaker()
        assert client._consecutive_failures == 0


class TestLLMClientGenerate:
    """Tests for LLM generate method with mocked API."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_after_threshold(self):
        """Should block requests after too many failures."""
        client = LLMClient(api_key="test")
        client._consecutive_failures = 5

        with pytest.raises(LLMCircuitBreakerError):
            await client.generate("Test prompt")

    @pytest.mark.asyncio
    async def test_generate_with_json_response(self):
        """Should parse JSON response correctly."""
        client = LLMClient(api_key="test")

        # Mock the _make_request method
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = '{"target": "player_1", "reasoning": "suspicious"}'

            result = await client.generate("Test prompt", response_format="json")

            assert result == {"target": "player_1", "reasoning": "suspicious"}
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_text_response(self):
        """Should return raw text for text format."""
        client = LLMClient(api_key="test")

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = "This is my notes for the game."

            result = await client.generate("Test prompt", response_format="text")

            assert result == "This is my notes for the game."

    @pytest.mark.asyncio
    async def test_generate_retries_on_timeout(self):
        """Should retry on timeout."""
        client = LLMClient(api_key="test", max_retries=2)

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise asyncio.TimeoutError()
            return '{"success": true}'

        with patch.object(client, '_make_request', side_effect=side_effect):
            result = await client.generate("Test prompt", response_format="json")
            assert result == {"success": True}
            assert call_count == 3  # 1 initial + 2 retries

    @pytest.mark.asyncio
    async def test_generate_fails_after_max_retries(self):
        """Should fail after exhausting retries."""
        client = LLMClient(api_key="test", max_retries=1)

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = asyncio.TimeoutError()

            with pytest.raises(LLMTimeoutError):
                await client.generate("Test prompt")

            # Should have attempted 2 times (1 initial + 1 retry)
            assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_resets_failures_on_success(self):
        """Should reset failure count on success."""
        client = LLMClient(api_key="test")
        client._consecutive_failures = 3

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = '{"ok": true}'

            await client.generate("Test prompt", response_format="json")

            assert client._consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_generate_increments_failures_on_total_failure(self):
        """Should increment failure count when all retries fail."""
        client = LLMClient(api_key="test", max_retries=0)
        client._consecutive_failures = 0

        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("API Error")

            with pytest.raises(LLMError):
                await client.generate("Test prompt")

            assert client._consecutive_failures == 1
