from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RuntimeErrorInfo:
    code: str
    message: str
    category: str
    details: Dict[str, Any] = field(default_factory=dict)
    retryable: bool = False
    status_code: int = 400

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "category": self.category,
            "details": self.details,
            "retryable": self.retryable,
        }


class RuntimeApiError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        category: str,
        *,
        details: Optional[Dict[str, Any]] = None,
        retryable: bool = False,
        status_code: int = 400,
    ):
        super().__init__(message)
        self.info = RuntimeErrorInfo(
            code=code,
            message=message,
            category=category,
            details=details or {},
            retryable=retryable,
            status_code=status_code,
        )


def success_response(data: Any, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "ok": True,
        "data": data,
        "error": None,
        "meta": meta or {},
    }


def error_response(error: RuntimeErrorInfo, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "ok": False,
        "data": None,
        "error": error.to_dict(),
        "meta": meta or {},
    }
