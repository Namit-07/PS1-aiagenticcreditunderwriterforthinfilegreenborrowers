"""Structured output parsing from LLM responses (Team B)."""

import json
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def parse_json_str(raw: str) -> dict[str, Any]:
    """Best-effort parsing of an LLM response into a dict.

    Strips markdown code fences before parsing. Placeholder (Team B).
    """
    text = raw.strip()
    if text.startswith("```"):
        # Remove leading/trailing code fences
        lines = text.splitlines()
        lines = [line for line in lines if not line.startswith("```")]
        text = "\n".join(lines).strip()
    return json.loads(text)


def validate_model(model: type[T], payload: dict[str, Any]) -> T:
    """Validate a dict against a Pydantic model; raise on failure."""
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"LLM output failed validation: {exc}") from exc