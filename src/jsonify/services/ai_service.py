"""Calls an OpenAI-compatible chat-completions endpoint.

This is the only module in the AI layer that touches the network, and it
only does so when a caller explicitly invokes :meth:`AiService.complete` —
nothing here runs automatically, on a timer, or as a side effect of
opening a document. If no provider is configured, every call raises
:class:`AiNotConfiguredError` immediately, with no network attempt.
"""

from __future__ import annotations

import httpx

from jsonify.core.ai_provider import AiProviderConfig


class AiNotConfiguredError(RuntimeError):
    """Raised when no AI endpoint has been configured yet."""


class AiRequestError(RuntimeError):
    """Raised when the configured AI endpoint can't be reached or errors."""


class AiService:
    """Sends chat-completion requests to a user-configured endpoint."""

    def __init__(
        self,
        config: AiProviderConfig,
        *,
        timeout_seconds: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._config = config
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def is_configured(self) -> bool:
        return self._config.is_configured

    def complete(self, messages: list[dict[str, str]]) -> str:
        """Send ``messages`` and return the assistant's reply text.

        Raises:
            AiNotConfiguredError: If no endpoint/model has been set.
            AiRequestError: If the request fails or the response is
                malformed.
        """

        if not self._config.is_configured:
            raise AiNotConfiguredError(
                "No AI endpoint configured. Set a base URL and model in AI settings."
            )

        headers = {"Content-Type": "application/json"}
        if self._config.api_key.strip():
            headers["Authorization"] = f"Bearer {self._config.api_key}"

        try:
            with httpx.Client(timeout=self._timeout_seconds, transport=self._transport) as client:
                response = client.post(
                    self._config.chat_completions_url(),
                    headers=headers,
                    json={"model": self._config.model, "messages": messages},
                )
                response.raise_for_status()
                data = response.json()

        except httpx.TimeoutException as error:
            raise AiRequestError(
                f"The AI request timed out after {self._timeout_seconds:g} seconds."
            ) from error

        except httpx.HTTPStatusError as error:
            raise AiRequestError(
                f"AI endpoint returned {error.response.status_code}: {error.response.text[:300]}"
            ) from error

        except httpx.RequestError as error:
            raise AiRequestError(f"Unable to reach the AI endpoint: {error}") from error

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise AiRequestError("AI endpoint returned an unexpected response shape.") from error

        if not isinstance(content, str):
            raise AiRequestError("AI endpoint returned a non-text response.")

        return content
