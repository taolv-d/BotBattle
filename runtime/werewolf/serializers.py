from datetime import datetime
from typing import Any, Dict, Optional


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def serialize_player(player: Any, view_type: str = "god", viewer_player_id: Optional[int] = None) -> Dict[str, Any]:
    role_value = _enum_value(player.role)
    death_cause = _enum_value(player.death_cause)

    role = role_value if view_type == "god" or player.id == viewer_player_id else None
    camp = None
    if view_type == "god":
        camp = "werewolf" if role_value == "werewolf" else "good"
    elif player.id == viewer_player_id:
        camp = "werewolf" if role_value == "werewolf" else "good"

    return {
        "player_id": player.id,
        "display_name": player.name,
        "is_alive": player.is_alive,
        "role": role,
        "public_role": None,
        "camp": camp,
        "is_human": player.is_human,
        "personality": player.personality if view_type == "god" else None,
        "death_cause": death_cause,
        "has_last_words": player.has_last_words,
        "is_president": False,
    }


def serialize_state(session: Any, view_type: str = "god", viewer_player_id: Optional[int] = None) -> Dict[str, Any]:
    orchestrator = session.orchestrator
    state = orchestrator.state
    players = []
    for player_id in sorted(state.players.keys()):
        player = state.players[player_id]
        item = serialize_player(player, view_type=view_type, viewer_player_id=viewer_player_id)
        item["is_president"] = state.president_id == player_id
        players.append(item)

    return {
        "game_id": state.game_id,
        "session_id": session.session_id,
        "mode": session.mode,
        "view_type": view_type,
        "lifecycle_status": session.lifecycle_status,
        "phase": state.phase,
        "day_number": state.day_number,
        "night_number": state.night_number,
        "president_id": state.president_id,
        "alive_player_ids": state.get_alive_players(),
        "players": players,
        "pending_input": session.pending_input,
        "review_status": session.review_status,
        "result": _serialize_result(state),
        "meta": {
            "updated_at": datetime.now().isoformat(),
            "last_sequence": session.event_store.get_last_sequence(),
            "log_file": getattr(session.logger, "log_file", None),
        },
    }


def _serialize_result(state: Any) -> Optional[Dict[str, Any]]:
    if not state.game_over:
        return None
    return {
        "winner": state.winner,
        "reason": state.reason,
    }
