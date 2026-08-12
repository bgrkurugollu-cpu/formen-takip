from __future__ import annotations

import json
import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger("app.llm")


class LLMNotConfiguredError(Exception):
    pass


class LLMRequestError(Exception):
    pass


class LLMTimeoutError(Exception):
    pass


class LLMResponseInvalidError(Exception):
    pass


class LLMToolCallingUnsupportedError(Exception):
    pass


def is_configured() -> bool:
    return get_settings().llm_available


def _post(payload: dict) -> dict:
    settings = get_settings()
    if not settings.llm_available:
        raise LLMNotConfiguredError("LLM devre dışı veya API anahtarı tanımlı değil.")

    headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
    try:
        response = httpx.post(
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            headers=headers, json={"model": settings.llm_model, **payload}, timeout=settings.llm_timeout_seconds,
        )
    except httpx.TimeoutException as exc:
        raise LLMTimeoutError(f"LLM isteği {settings.llm_timeout_seconds}s içinde yanıtlanmadı.") from exc
    except httpx.HTTPError as exc:
        raise LLMRequestError(f"LLM isteği başarısız: {type(exc).__name__}") from exc

    if response.status_code >= 400:
        body_text = response.text[:500]
        if response.status_code == 400 and ("tool" in body_text.lower() and "not support" in body_text.lower()):
            raise LLMToolCallingUnsupportedError(f"Model tool calling desteklemiyor: {body_text}")
        raise LLMRequestError(f"LLM sağlayıcısı {response.status_code} döndürdü.")

    try:
        return response.json()
    except json.JSONDecodeError as exc:
        raise LLMResponseInvalidError("LLM cevabı JSON olarak ayrıştırılamadı.") from exc


def call_llm(system_prompt: str, user_message: str, json_schema: dict | None = None, schema_name: str = "response") -> dict:
    response_format = (
        {"type": "json_schema", "json_schema": {"name": schema_name, "strict": True, "schema": json_schema}}
        if json_schema is not None
        else {"type": "json_object"}
    )
    body = _post(
        {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "response_format": response_format,
            "temperature": 0.2,
        }
    )
    try:
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)
    except (KeyError, IndexError, json.JSONDecodeError, TypeError) as exc:
        raise LLMResponseInvalidError("LLM cevabı beklenen formatta değil.") from exc


def call_chat(
    messages: list[dict], tools: list[dict] | None = None, tool_choice: str | None = None,
    response_format: dict | None = None,
) -> dict:
    payload: dict = {"messages": messages, "temperature": 0.2}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice or "auto"
    if response_format:
        payload["response_format"] = response_format

    body = _post(payload)
    try:
        return body["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMResponseInvalidError("LLM cevabında mesaj bulunamadı.") from exc
