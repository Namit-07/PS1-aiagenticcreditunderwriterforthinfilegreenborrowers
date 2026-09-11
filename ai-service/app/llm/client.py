"""LLM client wrapper (Team B): Gemini free tier first, OpenAI-compatible fallback.

The client is NEVER used to compute financial numbers — the deterministic financial
engine owns EMI/FOIR/LTV. LLM outputs feed extraction labels, reconciliation hints,
risk narrative and the credit-memo summary only, and are parsed as structured JSON
with a deterministic fallback when no key / package is available (MOCK_AI_MODE).

Gemini is called over plain REST with ``httpx`` (already a dependency), so no
``google-generativeai`` package is required. Free-tier rate limits (HTTP 429) are
treated like any other failure: the caller falls back to its template output.
"""

from __future__ import annotations

from typing import Any

from app.config import get_settings

settings = get_settings()

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class LLMClient:
    """Thin async wrapper over Gemini (REST) / OpenAI with a mock fallback."""

    def __init__(self, model: str | None = None, temperature: float | None = None) -> None:
        self.model = model
        self.temperature = settings.LLM_TEMPERATURE if temperature is None else temperature
        self._openai = None  # lazy client
        self.last_error: str | None = None

    @property
    def provider(self) -> str:
        return settings.llm_provider

    @property
    def model_name(self) -> str:
        if self.model:
            return self.model
        return settings.llm_model or "mock"

    def describe(self) -> dict[str, Any]:
        return {"provider": self.provider, "model": self.model_name}

    async def complete(
        self,
        system: str,
        user: str,
        *,
        response_format: dict[str, Any] | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Run a completion. In mock mode (or with no key) return a canned string."""
        if self.provider == "mock":
            return '{"mock": true}'
        max_tokens = max_tokens or settings.LLM_MAX_OUTPUT_TOKENS
        want_json = bool(response_format) and str(response_format.get("type", "")).startswith("json")
        if self.provider == "gemini":
            return await self._complete_gemini(system, user, max_tokens, want_json)
        return await self._complete_openai(system, user, max_tokens, want_json)

    async def complete_json(self, system: str, user: str, **kwargs: Any) -> dict[str, Any]:
        """Completion parsed as structured JSON (best-effort, never raises)."""
        from app.llm.structured_output import parse_json_str

        kwargs.setdefault("response_format", {"type": "json_object"})
        try:
            raw = await self.complete(system, user, **kwargs)
            parsed = parse_json_str(raw)
            return parsed if isinstance(parsed, dict) else {"mock": True}
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            return {"mock": True, "error": self.last_error}

    # ---- providers ----------------------------------------------------------
    async def _complete_gemini(self, system: str, user: str, max_tokens: int, want_json: bool) -> str:
        import httpx

        body: dict[str, Any] = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if want_json:
            body["generationConfig"]["responseMimeType"] = "application/json"
        url = GEMINI_ENDPOINT.format(model=self.model_name)
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, params={"key": settings.GEMINI_API_KEY}, json=body)
        if resp.status_code == 429:
            raise RuntimeError("Gemini free-tier rate limit hit (HTTP 429); using template output")
        if resp.status_code >= 400:
            detail = ""
            try:
                detail = str((resp.json().get("error") or {}).get("message", ""))[:200]
            except Exception:
                detail = resp.text[:200]
            raise RuntimeError(f"Gemini call failed (HTTP {resp.status_code}): {detail}")
        data = resp.json()
        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(str(p.get("text", "")) for p in parts if isinstance(p, dict))
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Gemini returned no candidates: {str(data)[:200]}") from exc
        return text.strip() or '{"mock": true}'

    async def _complete_openai(self, system: str, user: str, max_tokens: int, want_json: bool) -> str:
        try:
            from openai import AsyncOpenAI  # type: ignore
        except Exception as exc:
            raise RuntimeError("openai package is not installed") from exc
        if self._openai is None:
            self._openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        kwargs: dict[str, Any] = {}
        if want_json:
            kwargs["response_format"] = {"type": "json_object"}
        resp = await self._openai.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=self.temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        try:
            return (resp.choices[0].message.content or "").strip() or '{"mock": true}'
        except Exception:
            return '{"mock": true}'
