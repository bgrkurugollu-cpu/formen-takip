from __future__ import annotations

import enum


class ToolErrorCode(str, enum.Enum):
    TOOL_VALIDATION_ERROR = "TOOL_VALIDATION_ERROR"
    TOOL_NOT_ALLOWED = "TOOL_NOT_ALLOWED"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    TOOL_DATA_NOT_FOUND = "TOOL_DATA_NOT_FOUND"
    TOOL_DATA_QUALITY_ERROR = "TOOL_DATA_QUALITY_ERROR"
    LLM_TOOL_LOOP_LIMIT = "LLM_TOOL_LOOP_LIMIT"
    LLM_INVALID_TOOL_CALL = "LLM_INVALID_TOOL_CALL"
    LLM_INVALID_STRUCTURED_OUTPUT = "LLM_INVALID_STRUCTURED_OUTPUT"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_PROVIDER_ERROR = "LLM_PROVIDER_ERROR"
    ANALYSIS_TIMEOUT = "ANALYSIS_TIMEOUT"


class ToolError(Exception):
    """Bir aracın çalıştırılması sırasında oluşan, LLM'e yapılandırılmış biçimde geri
    bildirilecek hata. LLM bu durumda veri uydurmamalı, eksikliği nihai analizde
    belirtmelidir — orkestratör bunu zorunlu kılmaz ama sistem promptu bunu açıkça ister."""

    def __init__(self, code: ToolErrorCode, message: str, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable

    def to_dict(self) -> dict:
        return {"tool_error": True, "error_code": self.code.value, "message": self.message, "retryable": self.retryable}
