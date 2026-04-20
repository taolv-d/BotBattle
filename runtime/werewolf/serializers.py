from datetime import datetime
from typing import Any, Dict, List, Optional


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _camp_from_role(role_value: Optional[str]) -> Optional[str]:
    if not role_value:
        return None
    return "werewolf" if role_value == "werewolf" else "good"


def serialize_player(player: Any, state: Any, view_type: str = "god", viewer_player_id: Optional[int] = None) -> Dict[str, Any]:
    role_value = _enum_value(player.role)
    death_cause = _enum_value(player.death_cause)

    role = role_value if view_type == "god" or player.id == viewer_player_id else None
    camp = None
    if view_type == "god" or player.id == viewer_player_id:
        camp = _camp_from_role(role_value)

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
        "is_president": state.president_id == player.id,
    }


def _serialize_private_info(state: Any, viewer_player_id: Optional[int], view_type: str) -> Optional[Dict[str, Any]]:
    if view_type != "player" or viewer_player_id is None:
        return None

    player = state.players.get(viewer_player_id)
    if not player:
        return None

    role_value = _enum_value(player.role)
    info: Dict[str, Any] = {
        "player_id": viewer_player_id,
        "role": role_value,
        "camp": _camp_from_role(role_value),
        "checked_results": [],
        "wolf_teammates": [],
        "guarded_players": list(player.guarded_players or []),
        "last_guarded": player.guarded_players[-1] if player.guarded_players else None,
        "heal_used": bool(player.heal_used),
        "poison_used": bool(player.poison_used),
    }

    if role_value == "seer":
        checked_results: List[Dict[str, Any]] = []
        for checked_id in player.checked_players or []:
            target = state.players.get(checked_id)
            if not target:
                continue
            checked_results.append({
                "player_id": checked_id,
                "role": _enum_value(target.role),
                "camp": _camp_from_role(_enum_value(target.role)),
                "is_alive": target.is_alive,
            })
        info["checked_results"] = checked_results

    if role_value == "werewolf":
        teammates = []
        for teammate in state.players.values():
            teammate_role = _enum_value(teammate.role)
            if teammate.id != viewer_player_id and teammate_role == "werewolf":
                teammates.append({
                    "player_id": teammate.id,
                    "is_alive": teammate.is_alive,
                })
        info["wolf_teammates"] = teammates

    return info


def serialize_state(session: Any, view_type: str = "god", viewer_player_id: Optional[int] = None) -> Dict[str, Any]:
    orchestrator = session.orchestrator
    state = orchestrator.state
    players = []
    for player_id in sorted(state.players.keys()):
        player = state.players[player_id]
        players.append(serialize_player(player, state, view_type=view_type, viewer_player_id=viewer_player_id))

    pending_input = session.pending_input
    if session.input_adapter:
        pending_input = session.input_adapter.get_pending_request(view_type=view_type, viewer_player_id=viewer_player_id)

    return {
        "game_id": state.game_id,
        "session_id": session.session_id,
        "mode": session.mode,
        "view_type": view_type,
        "viewer_player_id": viewer_player_id,
        "lifecycle_status": session.lifecycle_status,
        "phase": state.phase,
        "day_number": state.day_number,
        "night_number": state.night_number,
        "president_id": state.president_id,
        "alive_player_ids": state.get_alive_players(),
        "players": players,
        "private_info": _serialize_private_info(state, viewer_player_id, view_type),
        "pending_input": pending_input,
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
