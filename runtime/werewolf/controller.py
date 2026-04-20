import asyncio
import os
import traceback
import uuid
from datetime import datetime
from threading import Thread
from typing import Any, Dict, List, Optional

from config_loader import ConfigManager
from core.network_env import configure_network_env
from games.werewolf.config import GameConfig
from games.werewolf.orchestrator import WerewolfOrchestrator
from runtime.werewolf.errors import RuntimeApiError
from runtime.werewolf.event_store import WerewolfEventStore
from runtime.werewolf.human_input import HumanInputCoordinator
from runtime.werewolf.serializers import serialize_state
from runtime.werewolf.session import WerewolfSession
from services.game_review_service import ReviewConfig, ReviewMode
from services.logger_service import LoggerService


def _create_game_config(config_mgr: ConfigManager) -> GameConfig:
    game_config = config_mgr.get_game_config()
    roles = game_config.get("roles", [
        {"role": "werewolf", "count": 3},
        {"role": "villager", "count": 3},
        {"role": "seer", "count": 1},
        {"role": "witch", "count": 1},
        {"role": "hunter", "count": 1},
    ])

    personalities = config_mgr.get_personality_names() or [
        f"Personality_{index}" for index in range(1, game_config.get("player_count", 9) + 1)
    ]

    game_rules = game_config.get("game_rules", {})
    return GameConfig(
        player_count=game_config.get("player_count", 9),
        roles=roles,
        personalities=personalities,
        rules={
            "witch_can_self_heal": True,
            "hunter_can_shoot_if_poisoned": game_rules.get("hunter_can_skill", True),
            "witch_same_night_dual_use": False,
            "witch_cannot_poison_first_night": False,
            "hunter_can_shoot_if_same_save_conflict": False,
            "president_can_inherit": game_rules.get("has_president_election", True),
        },
    )


class WerewolfRuntimeController:
    """Single-session runtime controller with first-pass player participation support."""

    def __init__(self, config_dir: str = "config", max_events: int = 1000, player_timeout_seconds: float = 1.0):
        self.config_dir = config_dir
        self.max_events = max_events
        self.player_timeout_seconds = player_timeout_seconds
        self.active_session: Optional[WerewolfSession] = None

    def create_session(self, payload: Optional[Dict[str, Any]] = None) -> WerewolfSession:
        payload = payload or {}
        if self.active_session and self.active_session.lifecycle_status not in {"finished", "review_ready", "error"}:
            raise RuntimeApiError(
                "SESSION_ALREADY_EXISTS",
                "An active session already exists.",
                "session",
                details={"session_id": self.active_session.session_id},
            )

        config_mgr = ConfigManager(self.config_dir)
        config_mgr.load_all()
        llm_config = config_mgr.get_llm_config()
        configure_network_env(llm_config)
        if not llm_config.get("api_key") or llm_config.get("api_key") == "YOUR_API_KEY":
            raise RuntimeApiError(
                "VALIDATION_FAILED",
                "LLM API key is not configured.",
                "validation",
                details={"field": "llm.api_key"},
            )

        mode = payload.get("mode", "observer")
        human_player_id = payload.get("human_player_id")
        if mode not in {"observer", "player"}:
            raise RuntimeApiError(
                "VALIDATION_FAILED",
                "Unsupported mode.",
                "validation",
                details={"field": "mode", "value": mode, "supported": ["observer", "player"]},
            )
        if mode == "player" and human_player_id is None:
            raise RuntimeApiError(
                "VALIDATION_FAILED",
                "human_player_id is required in player mode.",
                "validation",
                details={"field": "human_player_id"},
            )
        if human_player_id is not None and not isinstance(human_player_id, int):
            raise RuntimeApiError(
                "VALIDATION_FAILED",
                "human_player_id must be an integer.",
                "validation",
                details={"field": "human_player_id", "value": human_player_id},
            )

        review_enabled = payload.get("review_enabled", True)
        review_mode_name = payload.get("review_mode", "detailed")
        detect_loopholes = payload.get("detect_loopholes", False)
        review_mode = {
            "summary": ReviewMode.SUMMARY,
            "detailed": ReviewMode.DETAILED,
            "analysis": ReviewMode.ANALYSIS,
        }.get(review_mode_name, ReviewMode.DETAILED)

        review_config = ReviewConfig(
            enabled=review_enabled,
            mode=review_mode,
            detect_loopholes=detect_loopholes,
            max_log_entries=500,
        )

        game_config = _create_game_config(config_mgr)
        is_valid, errors, _warnings = game_config.validate()
        if not is_valid:
            raise RuntimeApiError(
                "VALIDATION_FAILED",
                "Game config validation failed.",
                "validation",
                details={"errors": errors},
            )

        if human_player_id is not None and human_player_id not in range(1, game_config.player_count + 1):
            raise RuntimeApiError(
                "VALIDATION_FAILED",
                "human_player_id is outside the current seat range.",
                "validation",
                details={"field": "human_player_id", "value": human_player_id},
            )

        logger = LoggerService(max_memory_entries=max(self.max_events, 1000))
        input_adapter = HumanInputCoordinator(timeout_seconds=self.player_timeout_seconds) if mode == "player" else None
        orchestrator = WerewolfOrchestrator(
            config=game_config,
            llm_config=llm_config,
            logger=logger,
            tts=None,
            review_config=review_config,
            human_input_adapter=input_adapter,
            human_timeout_seconds=self.player_timeout_seconds,
        )

        if human_player_id in orchestrator.state.players:
            orchestrator.state.players[human_player_id].is_human = True

        session = WerewolfSession(
            session_id=f"session_{uuid.uuid4().hex[:8]}",
            mode=mode,
            human_player_id=human_player_id,
            config_summary={
                "player_count": game_config.player_count,
                "roles": game_config.roles,
                "review_enabled": review_enabled,
                "review_mode": review_mode.value,
                "detect_loopholes": detect_loopholes,
                "player_timeout_seconds": self.player_timeout_seconds,
            },
            orchestrator=orchestrator,
            logger=logger,
            review_enabled=review_enabled,
            input_adapter=input_adapter,
        )
        session.event_store = WerewolfEventStore(self.max_events)
        session.review_status = {
            "status": "pending" if review_enabled else "disabled",
            "summary": None,
            "paths": None,
            "error": None,
        }
        self.active_session = session
        self._sync_session(session)
        return session

    def start_session(self) -> WerewolfSession:
        session = self._require_session()
        if session.thread and session.thread.is_alive():
            raise RuntimeApiError(
                "LIFECYCLE_INVALID_TRANSITION",
                "Session is already running.",
                "lifecycle",
                details={"lifecycle_status": session.lifecycle_status},
            )
        if session.lifecycle_status not in {"created", "error"}:
            raise RuntimeApiError(
                "LIFECYCLE_INVALID_TRANSITION",
                "Current session state does not allow start.",
                "lifecycle",
                details={"lifecycle_status": session.lifecycle_status},
            )

        session.lifecycle_status = "initializing"
        session.started_at = datetime.now().isoformat()
        session.thread = Thread(target=self._run_session, args=(session,), daemon=True)
        session.thread.start()
        self._sync_session(session)
        return session

    def get_session_summary(self) -> Dict[str, Any]:
        session = self._require_session()
        self._sync_session(session)
        return {
            "session_id": session.session_id,
            "game_id": session.game_id,
            "mode": session.mode,
            "human_player_id": session.human_player_id,
            "lifecycle_status": session.lifecycle_status,
            "created_at": session.created_at,
            "started_at": session.started_at,
            "finished_at": session.finished_at,
            "config": session.config_summary,
        }

    def get_state(self, view_type: str = "god", viewer_player_id: Optional[int] = None) -> Dict[str, Any]:
        session = self._require_session()
        if view_type not in {"god", "player"}:
            raise RuntimeApiError(
                "VIEW_TYPE_INVALID",
                "Unsupported view type.",
                "view",
                details={"view_type": view_type, "supported": ["god", "player"]},
            )
        if view_type == "player" and viewer_player_id is None:
            raise RuntimeApiError(
                "VIEWER_REQUIRED",
                "viewer_player_id is required for player view.",
                "view",
                details={"view_type": view_type},
            )
        if view_type == "player" and viewer_player_id not in session.orchestrator.state.players:
            raise RuntimeApiError(
                "VIEWER_NOT_FOUND",
                "viewer_player_id does not exist in the current session.",
                "view",
                details={"viewer_player_id": viewer_player_id},
                status_code=404,
            )
        self._sync_session(session)
        return serialize_state(session, view_type=view_type, viewer_player_id=viewer_player_id)

    def get_events(self, last_sequence: int = 0, limit: int = 200, view_type: str = "god", viewer_player_id: Optional[int] = None) -> Dict[str, Any]:
        session = self._require_session()
        if view_type not in {"god", "player"}:
            raise RuntimeApiError(
                "VIEW_TYPE_INVALID",
                "Unsupported view type.",
                "view",
                details={"view_type": view_type, "supported": ["god", "player"]},
            )
        if view_type == "player" and viewer_player_id is None:
            raise RuntimeApiError(
                "VIEWER_REQUIRED",
                "viewer_player_id is required for player view.",
                "view",
                details={"view_type": view_type},
            )
        if view_type == "player" and viewer_player_id not in session.orchestrator.state.players:
            raise RuntimeApiError(
                "VIEWER_NOT_FOUND",
                "viewer_player_id does not exist in the current session.",
                "view",
                details={"viewer_player_id": viewer_player_id},
                status_code=404,
            )
        self._sync_session(session)
        events = session.event_store.get_events(last_sequence=last_sequence, limit=limit)
        if view_type == "player":
            events = self._filter_events_for_player(events, viewer_player_id)
        window_start = session.event_store.get_window_start_sequence()
        return {
            "events": events,
            "last_sequence": session.event_store.get_last_sequence(),
            "window_start_sequence": window_start,
            "window_expired": bool(last_sequence and window_start and last_sequence < window_start),
        }

    def get_review_status(self) -> Dict[str, Any]:
        session = self._require_session()
        self._sync_session(session)
        return session.review_status

    def submit_input(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        session = self._require_session()
        if not session.input_adapter:
            raise RuntimeApiError(
                "INPUT_SUBMIT_FORBIDDEN",
                "The current session does not accept human input.",
                "input",
                status_code=400,
            )
        viewer_player_id = payload.get("player_id")
        if viewer_player_id != session.human_player_id:
            raise RuntimeApiError(
                "INPUT_SUBMIT_FORBIDDEN",
                "Submitted player_id does not match the bound human seat.",
                "input",
                details={"player_id": viewer_player_id, "human_player_id": session.human_player_id},
                status_code=403,
            )
        try:
            request = session.input_adapter.submit_input(payload)
        except ValueError as exc:
            raise RuntimeApiError(
                "INPUT_REQUEST_INVALID",
                str(exc),
                "input",
                status_code=400,
            ) from exc
        return {
            "accepted": True,
            "request_id": request["request_id"],
        }

    def join_session(self, _payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        raise RuntimeApiError(
            "JOIN_NOT_IMPLEMENTED",
            "Join game is reserved for a later iteration.",
            "session",
            status_code=501,
        )

    def _run_session(self, session: WerewolfSession) -> None:
        try:
            asyncio.run(session.orchestrator.run_game())
        except Exception as exc:
            session.error_info = {
                "code": "INTERNAL_ERROR",
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
            session.lifecycle_status = "error"
        finally:
            self._sync_session(session)

    def _sync_session(self, session: WerewolfSession) -> None:
        session.event_store.sync(session.logger.get_entries_snapshot())
        session.pending_input = session.input_adapter.get_pending_request(view_type="god") if session.input_adapter else None

        if session.error_info:
            session.lifecycle_status = "error"
            session.finished_at = session.finished_at or datetime.now().isoformat()
            session.review_status = {
                "status": "failed",
                "summary": None,
                "paths": None,
                "error": session.error_info["message"],
            }
            return

        if session.pending_input:
            session.lifecycle_status = "waiting_input"
            return

        thread_alive = bool(session.thread and session.thread.is_alive())
        state = session.orchestrator.state

        if state.game_over:
            report = session.orchestrator.review_service.load_report(state.game_id)
            if report:
                session.lifecycle_status = "review_ready"
                session.finished_at = session.finished_at or datetime.now().isoformat()
                session.review_status = {
                    "status": "ready",
                    "summary": report.summary,
                    "paths": {
                        "markdown": os.path.join("reviews", f"review_{state.game_id}.md"),
                        "json": os.path.join("reviews", f"review_{state.game_id}.json"),
                    },
                    "error": None,
                }
            elif session.review_enabled and thread_alive:
                session.lifecycle_status = "review_running"
                session.review_status = {
                    "status": "running",
                    "summary": None,
                    "paths": None,
                    "error": None,
                }
            elif session.review_enabled:
                session.lifecycle_status = "finished"
                session.finished_at = session.finished_at or datetime.now().isoformat()
                session.review_status = {
                    "status": "failed",
                    "summary": None,
                    "paths": None,
                    "error": "Review report was not generated successfully.",
                }
            else:
                session.lifecycle_status = "finished"
                session.finished_at = session.finished_at or datetime.now().isoformat()
                session.review_status = {
                    "status": "disabled",
                    "summary": None,
                    "paths": None,
                    "error": None,
                }
            return

        if thread_alive:
            session.lifecycle_status = "running"
        elif session.lifecycle_status == "initializing":
            session.lifecycle_status = "created"

    def _filter_events_for_player(self, events: List[Dict[str, Any]], viewer_player_id: Optional[int]) -> List[Dict[str, Any]]:
        filtered = []
        for event in events:
            visibility = event.get("visibility", "public")
            if visibility == "public":
                filtered.append(event)
                continue
            if visibility == "private_player" and event.get("target_player_id") == viewer_player_id:
                filtered.append(event)
        return filtered

    def _require_session(self) -> WerewolfSession:
        if not self.active_session:
            raise RuntimeApiError(
                "SESSION_NOT_FOUND",
                "No active session.",
                "session",
                status_code=404,
            )
        return self.active_session