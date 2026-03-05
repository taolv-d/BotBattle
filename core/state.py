"""游戏状态定义"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import json


class Phase(Enum):
    """游戏阶段"""
    NIGHT = "night"
    DAY_DISCUSS = "day_discuss"
    DAY_VOTE = "day_vote"
    GAME_OVER = "game_over"


class Role(Enum):
    """角色类型"""
    WEREWOLF = "werewolf"
    VILLAGER = "villager"
    SEER = "seer"
    WITCH = "witch"
    HUNTER = "hunter"


@dataclass
class Player:
    """玩家"""
    id: int
    name: str
    role: Optional[Role] = None
    personality: Optional[str] = None
    is_alive: bool = True
    is_human: bool = False
    is_bot: bool = True
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value if self.role else None,
            "personality": self.personality,
            "is_alive": self.is_alive,
            "is_human": self.is_human,
        }


@dataclass
class GameState:
    """游戏状态"""
    player_count: int = 9
    players: dict[int, Player] = field(default_factory=dict)
    phase: Phase = Phase.NIGHT
    day_number: int = 0
    night_number: int = 0
    
    # 夜晚行动结果
    werewolf_target: Optional[int] = None
    seer_check_target: Optional[int] = None
    seer_check_result: Optional[Role] = None
    witch_heal_target: Optional[int] = None
    witch_poison_target: Optional[int] = None
    
    # 投票结果
    vote_target: Optional[int] = None
    vote_counts: dict[int, int] = field(default_factory=dict)
    
    # 游戏结束标志
    game_over: bool = False
    winner: Optional[str] = None  # "werewolf" or "villager"
    
    # 历史记录（用于日志）
    history: list[dict] = field(default_factory=list)
    
    def add_history(self, event_type: str, data: dict) -> None:
        self.history.append({"type": event_type, "data": data})
    
    def get_alive_players(self) -> list[Player]:
        return [p for p in self.players.values() if p.is_alive]
    
    def get_alive_werewolves(self) -> list[Player]:
        return [p for p in self.players.values() if p.is_alive and p.role == Role.WEREWOLF]
    
    def get_alive_villagers(self) -> list[Player]:
        return [p for p in self.players.values() if p.is_alive and p.role != Role.WEREWOLF]
    
    def check_game_over(self) -> bool:
        """检查游戏是否结束"""
        werewolves = self.get_alive_werewolves()
        villagers = self.get_alive_villagers()
        
        if len(werewolves) == 0:
            self.game_over = True
            self.winner = "villager"
            return True
        
        if len(werewolves) >= len(villagers):
            self.game_over = True
            self.winner = "werewolf"
            return True
        
        return False
    
    def to_json(self) -> str:
        return json.dumps({
            "player_count": self.player_count,
            "players": {k: v.to_dict() for k, v in self.players.items()},
            "phase": self.phase.value,
            "day_number": self.day_number,
            "night_number": self.night_number,
            "game_over": self.game_over,
            "winner": self.winner,
        }, ensure_ascii=False, indent=2)
