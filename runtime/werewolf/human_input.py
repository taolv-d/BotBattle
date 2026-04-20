import asyncio
import time
import uuid
from threading import Lock
from typing import Any, Dict, Optional


class HumanInputCoordinator:
    def __init__(self, timeout_seconds: float = 1.0):
        self.timeout_seconds = timeout_seconds
        self._lock = Lock()
        self._current_request: Optional[Dict[str, Any]] = None
        self._submitted_payload: Optional[Dict[str, Any]] = None

    def has_pending_request(self) -> bool:
        with self._lock:
            return self._current_request is not None

    def get_pending_request(self, view_type: str = "god", viewer_player_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        with self._lock:
            request = dict(self._current_request) if self._current_request else None
        if not request:
            return None
        if view_type == "player" and viewer_player_id != request.get("player_id"):
            return None
        return request

    async def request_input(
        self,
        *,
        player_id: int,
        input_type: str,
        phase: str,
        prompt: str,
        suggestion: Any,
        suggestion_label: str,
        suggestion_submit_value: str,
        options: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        timeout_seconds = timeout_seconds if timeout_seconds is not None else self.timeout_seconds
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        now = time.time()
        request = {
            "request_id": request_id,
            "player_id": player_id,
            "input_type": input_type,
            "phase": phase,
            "prompt": prompt,
            "options": options or [],
            "suggestion": suggestion,
            "suggestion_label": suggestion_label,
            "suggestion_submit_value": suggestion_submit_value,
            "metadata": metadata or {},
            "created_at": now,
            "expires_at": now + timeout_seconds,
            "timeout_seconds": timeout_seconds,
        }
        with self._lock:
            self._current_request = request
            self._submitted_payload = None

        deadline = now + timeout_seconds
        while time.time() < deadline:
            with self._lock:
                submitted = self._submitted_payload
                if submitted and submitted.get("request_id") == request_id:
                    self._submitted_payload = None
                    self._current_request = None
                    return {
                        "status": "submitted",
                        "request": request,
                        "payload": submitted,
                    }
            await asyncio.sleep(0.05)

        with self._lock:
            self._current_request = None
            self._submitted_payload = None
        return {
            "status": "timeout",
            "request": request,
            "payload": None,
        }

    def submit_input(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        request_id = payload.get("request_id")
        with self._lock:
            if not self._current_request:
                raise ValueError("No active input request.")
            if request_id != self._current_request.get("request_id"):
                raise ValueError("Input request does not match the active request.")
            self._submitted_payload = dict(payload)
            return dict(self._current_request)