from dataclasses import dataclass, field
from datetime import datetime
from threading import Thread
from typing import Any, Dict, Optional

from .event_store import WerewolfEventStore


@dataclass
class WerewolfSession:
    session_id: str
    mode: str
    human_player_id: Optional[int]
    config_summary: Dict[str, Any]
    orchestrator: Any
    logger: Any
    review_enabled: bool
    thread: Optional[Thread] = None
    lifecycle_status: str = "created"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error_info: Optional[Dict[str, Any]] = None
    pending_input: Optional[Dict[str, Any]] = None
    event_store: WerewolfEventStore = field(default_factory=WerewolfEventStore)
    review_status: Dict[str, Any] = field(default_factory=lambda: {
        "status": "disabled",
        "summary": None,
        "paths": None,
        "error": None,
    })

    @property
    def game_id(self) -> str:
        return self.orchestrator.state.game_id
