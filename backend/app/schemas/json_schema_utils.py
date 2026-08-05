from __future__ import annotations

from pydantic import BaseModel

# OpenAI structured-outputs / strict function-calling modu, JSON Schema'nın yalnızca bir alt
# kümesini destekler — sayısal/metinsel kısıtlar (minimum/maximum, pattern, vb.) API tarafından
# reddedilebilir. Bu alanlar kaldırılır; asıl doğrulama zaten Pydantic modeliyle yapılır.
_UNSUPPORTED_KEYWORDS = (
    "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
    "minLength", "maxLength", "pattern", "format", "default",
)


def _tighten(node: object) -> None:
    """JSON şema düğümünü OpenAI'ın strict modu için gerekli hale getirir: her nesnede
    `additionalProperties: false` ve TÜM alanlar `required` listesinde olmalı (varsayılan
    değerli alanlar dahil — strict modda "opsiyonel alan" kavramı yoktur)."""
    if isinstance(node, dict):
        for keyword in _UNSUPPORTED_KEYWORDS:
            node.pop(keyword, None)
        if "properties" in node:
            node["required"] = list(node["properties"].keys())
            node["additionalProperties"] = False
        for value in node.values():
            _tighten(value)
    elif isinstance(node, list):
        for item in node:
            _tighten(item)


def strict_json_schema(model: type[BaseModel]) -> dict:
    """`model`in Pydantic şemasından, OpenAI'ın strict JSON şema modunun kabul ettiği bir
    şema üretir (bkz. app/services/llm_service.py ve app/services/tools/definitions.py)."""
    schema = model.model_json_schema()
    _tighten(schema)
    return schema
