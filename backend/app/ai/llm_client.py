"""LLM Client - Wrapper for Gemini API with retry/timeout logic."""

import asyncio
import json
import logging
import re
from typing import Any

from google import genai
from google.genai import types

from app.config import GOOGLE_API_KEY, LLM_MODEL, LLM_TIMEOUT, LLM_MAX_RETRIES

logger = logging.getLogger(__name__)


class LLMClient:
    """Async wrapper for Gemini API with retry and timeout logic."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
    ):
        self.api_key = api_key or GOOGLE_API_KEY
        self.model = model or LLM_MODEL
        self.timeout = timeout or LLM_TIMEOUT
        self.max_retries = max_retries or LLM_MAX_RETRIES
        self._client: genai.Client | None = None
        self._consecutive_failures = 0
        self._circuit_breaker_threshold = 5

    def _get_client(self) -> genai.Client:
        """Get or create the Gemini client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("GOOGLE_API_KEY not configured")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def generate(
        self,
        prompt: str,
        response_format: str = "json",
        system_instruction: str | None = None,
    ) -> dict[str, Any] | str:
        """
        Generate a response from the LLM.

        Args:
            prompt: The prompt to send to the LLM
            response_format: "json" or "text"
            system_instruction: Optional system instruction

        Returns:
            Parsed JSON dict if response_format="json", raw text otherwise
        """
        # Circuit breaker check
        if self._consecutive_failures >= self._circuit_breaker_threshold:
            logger.warning("Circuit breaker open - too many consecutive failures")
            raise LLMCircuitBreakerError("Too many consecutive LLM failures")

        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._make_request(
                    prompt, system_instruction, response_format
                )
                self._consecutive_failures = 0  # Reset on success

                if response_format == "json":
                    return self._parse_json_response(response)
                return response

            except asyncio.TimeoutError:
                last_error = LLMTimeoutError(f"LLM request timed out after {self.timeout}s")
                logger.warning(f"LLM timeout on attempt {attempt + 1}/{self.max_retries + 1}")

            except json.JSONDecodeError as e:
                last_error = LLMParseError(f"Failed to parse JSON response: {e}")
                logger.warning(f"JSON parse error on attempt {attempt + 1}: {e}")

            except Exception as e:
                last_error = LLMError(f"LLM request failed: {e}")
                logger.warning(f"LLM error on attempt {attempt + 1}: {e}")

            # Exponential backoff between retries
            if attempt < self.max_retries:
                backoff = 2 ** attempt
                await asyncio.sleep(backoff)

        self._consecutive_failures += 1
        raise last_error or LLMError("Unknown error")

    async def _make_request(
        self,
        prompt: str,
        system_instruction: str | None,
        response_format: str,
    ) -> str:
        """Make the actual API request with timeout."""
        client = self._get_client()

        # Build generation config
        config = types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=1024,
        )

        if system_instruction:
            config.system_instruction = system_instruction

        # Add JSON response hint if needed
        if response_format == "json":
            config.response_mime_type = "application/json"

        def sync_generate():
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            return response.text

        # Run sync API in thread pool with timeout
        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, sync_generate),
            timeout=self.timeout,
        )

    def _parse_json_response(self, response: str) -> dict[str, Any]:
        """Parse JSON from LLM response, handling markdown code blocks."""
        # Try direct parse first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try finding JSON object in response
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        raise json.JSONDecodeError("No valid JSON found in response", response, 0)

    def reset_circuit_breaker(self) -> None:
        """Reset the circuit breaker."""
        self._consecutive_failures = 0


class LLMError(Exception):
    """Base exception for LLM errors."""
    pass


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""
    pass


class LLMParseError(LLMError):
    """Raised when LLM response cannot be parsed."""
    pass


class LLMCircuitBreakerError(LLMError):
    """Raised when circuit breaker is open due to too many failures."""
    pass
