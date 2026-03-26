import json
from collections import deque
from typing import Any, Deque, Dict, List, Optional


class WerewolfEventStore:
    """Projects raw logger entries into stable UI events."""

    def __init__(self, max_events: int = 1000):
        self.max_events = max_events
        self._events: Deque[Dict[str, Any]] = deque(maxlen=max_events)
        self._seen_signatures = set()
        self._next_sequence = 1

    def sync(self, raw_entries: List[Dict[str, Any]]) -> None:
        for entry in raw_entries:
            signature = json.dumps(entry, ensure_ascii=False, sort_keys=True, default=str)
            if signature in self._seen_signatures:
                continue
            self._seen_signatures.add(signature)
            event = self._project_entry(entry)
            if event is None:
                continue
            event["sequence"] = self._next_sequence
            self._next_sequence += 1
            self._events.append(event)

    def get_events(self, last_sequence: int = 0, limit: int = 200) -> List[Dict[str, Any]]:
        events = [event for event in self._events if event["sequence"] > last_sequence]
        if limit > 0:
            events = events[:limit]
        return events

    def get_last_sequence(self) -> int:
        if not self._events:
            return 0
        return self._events[-1]["sequence"]

    def get_window_start_sequence(self) -> int:
        if not self._events:
            return 0
        return self._events[0]["sequence"]

    def _project_entry(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        timestamp = entry.get("timestamp")
        event_type = entry.get("event_type")
        payload = entry.get("data") or entry.get("state") or entry.get("actions") or {}

        visibility = "public"
        projected_type = event_type

        if event_type in {"game_state_snapshot", "agent_interaction"}:
            visibility = "god_only"
        elif event_type in {"night_action", "wolf_coordination"}:
            visibility = "god_only"
            projected_type = "night_action_result"
        elif event_type == "game_result":
            projected_type = "game_finished"
        elif event_type in {"speech", "pk_speech", "president_candidate_speech", "president_pk_speech", "last_words"}:
            visibility = "public"
        elif event_type in {"vote", "vote_result", "phase_changed", "death", "president_changed"}:
            visibility = "public"
        elif event_type is None:
            return None

        return {
            "event_id": f"evt_{self._next_sequence}",
            "timestamp": timestamp,
            "event_type": projected_type,
            "visibility": visibility,
            "payload": payload,
        }
