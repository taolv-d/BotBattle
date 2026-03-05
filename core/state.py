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
    name: str           # 显示名字（如"1 号玩家"）
    celebrity_name: str = ""  # 名人名字（如"诸葛亮"）
    role: Optional[Role] = None
    personality: Optional[str] = None
    is_alive: bool = True
    is_human: bool = False
    is_bot: bool = True
    death_cause: Optional[str] = None  # 死亡原因：wolf(狼刀), voted_out(投票), poison(毒药), hunter(猎人带走)

    def get_display_name(self, show_celebrity: bool = True) -> str:
        """
        获取显示名字
        
        Args:
            show_celebrity: 是否显示名人名字
            
        Returns:
            显示用的名字
        """
        if show_celebrity and self.celebrity_name:
            return f"{self.name}({self.celebrity_name})"
        return self.name

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "celebrity_name": self.celebrity_name,
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
        """
        检查游戏是否结束
        
        规则：
        1. 狼人全部死亡 → 好人胜利
        2. 狼人数量 > 好人数量 → 狼人胜利（注意：是大于，不是大于等于）
        3. 3 狼 vs 3 好人 → 游戏继续
        """
        werewolves = self.get_alive_werewolves()
        villagers = self.get_alive_villagers()

        if len(werewolves) == 0:
            self.game_over = True
            self.winner = "villager"
            self._log_game_end_reason("所有狼人被淘汰")
            return True

        # 修复：狼人数量必须严格大于好人数量才获胜
        if len(werewolves) > len(villagers):
            self.game_over = True
            self.winner = "werewolf"
            self._log_game_end_reason(f"狼人数量 ({len(werewolves)}) 超过好人数量 ({len(villagers)})")
            return True

        return False
    
    def _log_game_end_reason(self, reason: str) -> None:
        """记录游戏结束原因（用于调试）"""
        print(f"[游戏结束] 原因：{reason}")
        print(f"  存活狼人：{len(self.get_alive_werewolves())} 人")
        print(f"  存活好人：{len(self.get_alive_villagers())} 人")
    
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
