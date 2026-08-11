from __future__ import annotations

from pydantic import BaseModel

_UNSUPPORTED_KEYWORDS = (
    "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
    "minLength", "maxLength", "pattern", "format", "default",
)


def _tighten(node: object) -> None:
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
    schema = model.model_json_schema()
    _tighten(schema)
    return schema
