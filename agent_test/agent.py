from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence


class ModelProvider(Protocol):
    """Interface any LLM provider should implement."""

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        context: Sequence[str] | None = None,
    ) -> str:
        ...


class MemoryModule(Protocol):
    """Interface for any memory backend attached to the agent."""

    def add(self, key: str, value: Any) -> None:
        ...

    def get(self, key: str, default: Any = None) -> Any:
        ...

    def search(self, query: str, limit: int = 5) -> list[str]:
        ...


@dataclass
class InMemoryStore:
    """Default local memory implementation used when no backend is supplied."""

    store: dict[str, Any] = field(default_factory=dict)

    def add(self, key: str, value: Any) -> None:
        self.store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.store.get(key, default)

    def search(self, query: str, limit: int = 5) -> list[str]:
        matches: list[str] = []
        query_lower = query.lower()

        for key, value in self.store.items():
            text = str(value).lower()
            if query_lower in text or query_lower in key.lower():
                matches.append(f"{key}: {value}")
                if len(matches) >= limit:
                    break

        return matches


class SimpleModelProvider:
    """Example provider stub for a local or external adapter."""

    def __init__(self, model_name: str = "demo-model") -> None:
        self.model_name = model_name

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        context: Sequence[str] | None = None,
    ) -> str:
        context_text = "\n".join(context or [])
        return (
            f"[{self.model_name}]\n"
            f"System: {system_prompt or 'None'}\n"
            f"Context: {context_text or 'No memory context'}\n"
            f"Prompt: {prompt}"
        )


class Agent:
    """Minimal agent template with optional memory integration."""

    def __init__(
        self,
        provider: ModelProvider,
        memory: MemoryModule | None = None,
        system_prompt: str = "You are a helpful assistant.",
    ) -> None:
        self.provider = provider
        self.memory = memory or InMemoryStore()
        self.system_prompt = system_prompt

    def remember(self, key: str, value: Any) -> None:
        self.memory.add(key, value)

    def recall(self, key: str, default: Any = None) -> Any:
        return self.memory.get(key, default)

    def retrieve_context(self, query: str, limit: int = 5) -> list[str]:
        if hasattr(self.memory, "search"):
            return self.memory.search(query, limit=limit)
        return []

    def respond(self, user_input: str, *, use_memory: bool = True) -> str:
        context = self.retrieve_context(user_input) if use_memory else []
        prompt = user_input

        if context:
            prompt = "\n\n".join(["Relevant memory:", *context, "User request:", user_input])

        return self.provider.generate(
            prompt,
            system_prompt=self.system_prompt,
            context=context,
        )


# Example factory for swapping providers or memory backends.
def create_agent(
    provider: ModelProvider,
    memory: MemoryModule | None = None,
    system_prompt: str = "You are a helpful assistant.",
) -> Agent:
    return Agent(provider=provider, memory=memory, system_prompt=system_prompt)
