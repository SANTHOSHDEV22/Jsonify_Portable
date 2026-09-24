"""Configuration model for the bring-your-own-endpoint AI layer.

Jsonify ships no AI credentials and talks to no AI service by default.
An :class:`AiProviderConfig` only becomes usable once the user points it at
an OpenAI-compatible chat-completions endpoint themselves — a hosted
provider, or a local server such as Ollama/LM Studio (``base_url`` pointed
at ``localhost``). This module has no I/O; see
``services.ai_config_service`` for persistence and ``services.ai_service``
for the actual HTTP call.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_CHAT_PATH = "/chat/completions"


@dataclass(frozen=True, slots=True)
class AiProviderConfig:
    """Connection details for one OpenAI-compatible endpoint."""

    base_url: str = ""
    api_key: str = ""
    model: str = ""

    @property
    def is_configured(self) -> bool:
        """Whether there's enough to attempt a call.

        ``api_key`` is intentionally not required here — many local
        servers (Ollama, LM Studio) accept requests without one.
        """

        return bool(self.base_url.strip()) and bool(self.model.strip())

    def chat_completions_url(self) -> str:
        """The full chat-completions endpoint URL for this provider."""

        return self.base_url.rstrip("/") + DEFAULT_CHAT_PATH
