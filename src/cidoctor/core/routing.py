"""Model routing for CI Doctor.

Resolves a model name to a provider spec: names starting with ``gemini`` go
to Gemini; names in the installed Ollama list go to Ollama; anything else
raises :class:`ConfigError` with an ``ollama pull`` hint.
"""

from __future__ import annotations

from dataclasses import dataclass

from cidoctor.core.errors import ConfigError


@dataclass(frozen=True)
class ProviderSpec:
    """A resolved provider specification."""

    provider: str  # "gemini" or "ollama"
    model: str
    host: str | None = None  # Ollama host, if provider is "ollama"


def resolve_model(name: str, installed: list[str]) -> ProviderSpec:
    """Resolve a model name to a provider spec.

    Args:
        name: model name (e.g. ``gemini-3.5-flash-lite``, ``llama3``).
        installed: list of installed Ollama model names.

    Returns:
        A :class:`ProviderSpec`.

    Raises:
        ConfigError: if the name is not recognized.
    """
    if name.startswith("gemini"):
        return ProviderSpec(provider="gemini", model=name)

    if name in installed:
        return ProviderSpec(provider="ollama", model=name)

    hint = ""
    if installed:
        hint = f" Available Ollama models: {', '.join(installed)}."
    raise ConfigError(
        f"Unknown model {name!r}. Run: ollama pull {name}{hint}"
    )


__all__ = ["ProviderSpec", "resolve_model"]
