"""Tests for pure AI prompt-builders (no network involved)."""

from __future__ import annotations

import pytest

from jsonify.core.ai_prompts import (
    build_api_debug_prompt,
    build_query_generation_prompt,
    build_structure_analysis_prompt,
    build_test_case_prompt,
)


def test_structure_analysis_prompt_has_system_and_user_roles() -> None:
    messages = build_structure_analysis_prompt("Root type: object", ["field 'x' is 90% null"])

    assert [m["role"] for m in messages] == ["system", "user"]
    assert "Root type: object" in messages[1]["content"]
    assert "90% null" in messages[1]["content"]


def test_structure_analysis_prompt_handles_no_anomalies() -> None:
    messages = build_structure_analysis_prompt("Root type: object", [])

    assert "None detected." in messages[1]["content"]


def test_query_generation_prompt_mentions_language_and_instruction() -> None:
    messages = build_query_generation_prompt("get all user emails", "Root type: array", "jq")

    assert "jq" in messages[1]["content"]
    assert "get all user emails" in messages[1]["content"]


def test_query_generation_prompt_rejects_unknown_language() -> None:
    with pytest.raises(ValueError, match="Unsupported query language"):
        build_query_generation_prompt("x", "y", "sql")


def test_api_debug_prompt_includes_request_and_response() -> None:
    messages = build_api_debug_prompt("GET /users -> 404", "404 Not Found")

    assert "GET /users -> 404" in messages[1]["content"]
    assert "404 Not Found" in messages[1]["content"]


def test_test_case_prompt_includes_count_and_schema() -> None:
    messages = build_test_case_prompt('{"type": "object"}', 3)

    assert "3 edge-case" in messages[1]["content"]
    assert '{"type": "object"}' in messages[1]["content"]


def test_prompts_never_contain_network_instructions() -> None:
    messages = build_structure_analysis_prompt("summary", [])

    assert "http://" not in messages[0]["content"]
    assert "http://" not in messages[1]["content"]
