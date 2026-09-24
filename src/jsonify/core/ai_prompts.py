"""Pure prompt-builders for the optional AI layer (``services.ai_service``).

No network calls happen here — these functions only assemble the
OpenAI-compatible ``messages`` list an AI call would send, so they're
testable without a configured endpoint. Callers decide whether and when to
actually send the result; nothing in this module sends data anywhere.
"""

from __future__ import annotations

_SYSTEM_PREAMBLE = (
    "You are a JSON tooling assistant embedded in a desktop app called Jsonify. "
    "Be concise and concrete. When you propose a query or code, put it in its "
    "own fenced code block so the app can extract it."
)


def build_structure_analysis_prompt(
    profile_summary: str, anomaly_lines: list[str]
) -> list[dict[str, str]]:
    """Ask the model to describe/critique a payload's shape.

    ``profile_summary`` is ``JsonProfile.summary_text()`` and
    ``anomaly_lines`` are ``Anomaly.message`` strings — aggregated
    statistics only, never raw field values, since this may include data
    the user has not reviewed for sensitivity.
    """

    anomalies_text = "\n".join(f"- {line}" for line in anomaly_lines) or "None detected."
    user_prompt = (
        "Here is a structural profile of a JSON payload (field names, types, "
        "null rates, cardinality — no actual values):\n\n"
        f"{profile_summary}\n\n"
        f"Automatically detected anomalies:\n{anomalies_text}\n\n"
        "In a few sentences: describe what this data most likely represents, "
        "flag anything that looks like a data-quality or API-design issue, "
        "and suggest one or two follow-up checks worth running."
    )
    return _messages(user_prompt)


def build_query_generation_prompt(
    instruction: str, sample_summary: str, language: str
) -> list[dict[str, str]]:
    """Ask the model to translate a natural-language request into a query.

    ``language`` is ``"jq"`` or ``"jsonpath"``. The caller must show the
    generated expression to the user and let them run it explicitly — this
    function only builds the prompt, it never executes anything.
    """

    if language not in ("jq", "jsonpath"):
        raise ValueError(f"Unsupported query language: {language!r}")

    user_prompt = (
        f"Given this JSON structure:\n\n{sample_summary}\n\n"
        f'Write a single {language} expression that does: "{instruction}".\n'
        f"Respond with only the {language} expression in a fenced code block, "
        "no explanation."
    )
    return _messages(user_prompt)


def build_api_debug_prompt(request_summary: str, response_summary: str) -> list[dict[str, str]]:
    """Ask the model to explain a failed or unexpected API response."""

    user_prompt = (
        "An API request produced an unexpected result. Explain the likely "
        "cause and suggest the next thing to try.\n\n"
        f"Request:\n{request_summary}\n\n"
        f"Response:\n{response_summary}"
    )
    return _messages(user_prompt)


def build_test_case_prompt(schema_summary: str, count: int) -> list[dict[str, str]]:
    """Ask the model to suggest edge-case test payloads beyond what the
    deterministic generator (``core.payload_generator``) already covers —
    e.g. boundary values, malformed variants, unusual-but-valid shapes."""

    user_prompt = (
        f"Given this JSON Schema:\n\n{schema_summary}\n\n"
        f"Suggest {count} edge-case test payloads that a deterministic "
        "generator would be unlikely to produce (boundary values, unusual "
        "but schema-valid combinations, realistic malformed variants). "
        "Respond with a JSON array of payloads in a single fenced code block."
    )
    return _messages(user_prompt)


def _messages(user_prompt: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": _SYSTEM_PREAMBLE},
        {"role": "user", "content": user_prompt},
    ]
