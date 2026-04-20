"""LLM client abstraction: provider-agnostic interface with OpenAI/Anthropic/Mock adapters."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod

import structlog

from src.config.settings import LLMConfig

logger = structlog.get_logger()


class BaseLLMClient(ABC):
    """Abstract LLM client interface."""

    @abstractmethod
    async def generate(self, prompt: str, system: str | None = None) -> str:
        """Generate text from the LLM.

        Args:
            prompt: User prompt.
            system: Optional system prompt.

        Returns:
            Generated text.
        """


class OpenAIClient(BaseLLMClient):
    """OpenAI API adapter."""

    def __init__(self, config: LLMConfig) -> None:
        self.model = config.resolve_model()
        self.api_key = config.api_key

    async def generate(self, prompt: str, system: str | None = None) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key)
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0,
        )
        return response.choices[0].message.content or ""


class AnthropicClient(BaseLLMClient):
    """Anthropic API adapter."""

    def __init__(self, config: LLMConfig) -> None:
        self.model = config.resolve_model()
        self.api_key = config.api_key

    async def generate(self, prompt: str, system: str | None = None) -> str:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.api_key)
        response = await client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system or "",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing. Returns structured JSON responses."""

    async def generate(self, prompt: str, system: str | None = None) -> str:
        return json.dumps(
            {
                "extracted": {
                    "target_price": None,
                    "rating": None,
                    "earnings": None,
                    "analyst": None,
                    "sector": None,
                },
                "generated": {
                    "key_points": ["테스트 요약 포인트"],
                    "one_line": "테스트 한 줄 요약",
                    "opinion_summary": None,
                    "full_summary": None,
                },
            },
            ensure_ascii=False,
        )


def create_llm_client(config: LLMConfig) -> BaseLLMClient:
    """Factory: create appropriate LLM client based on config."""
    if config.provider == "mock":
        return MockLLMClient()
    elif config.provider == "anthropic":
        return AnthropicClient(config)
    else:
        return OpenAIClient(config)
