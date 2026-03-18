from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum
from .config import Role, DeathCause


@dataclass
class Player:
    """玩家状态"""
    id: int
    name: str
    role: Role
    personality: str
    is_alive: bool = True
    is_human: bool = False

    # 角色特定状态
    checked_players: List[int] = None  # 预言家已查验
    guarded_players: List[int] = None  # 守卫已守护（只包含上一夜）
    heal_used: bool = False  # 女巫解药已用
    poison_used: bool = False  # 女巫毒药已用
    death_cause: Optional[DeathCause] = None
    has_last_words: bool = False  # 是否有遗言
    president_inherit_id: Optional[int] = None  # 警长继承者 ID

    def __post_init__(self):
        """初始化可变字段"""
        if self.checked_players is None:
            self.checked_players = []
        if self.guarded_players is None:
            self.guarded_players = []
        # 布尔字段已有默认值，__post_init__ 中不需要重复设置
        # 但保留检查作为防御性编程
        if self.heal_used is None:
            self.heal_used = False
        if self.poison_used is None:
            self.poison_used = False
        if self.has_last_words is None:
            self.has_last_words = False
        if self.president_inherit_id is None:
            self.president_inherit_id = None


@dataclass
class GameState:
    """游戏状态"""
    game_id: str = ""
    player_count: int = 0
    day_number: int = 0
    night_number: int = 0
    president_id: Optional[int] = None
    players: Dict[int, Player] = None
    game_over: bool = False
    winner: Optional[str] = None
    reason: Optional[str] = None

    def __post_init__(self):
        if self.players is None:
            self.players = {}

    def get_alive_players(self) -> List[int]:
        return [p.id for p in self.players.values() if p.is_alive]

    def get_werewolves(self) -> List[int]:
        return [p.id for p in self.players.values()
                if p.role == Role.WEREWOLF and p.is_alive]

    def get_villagers(self) -> List[int]:
        return [p.id for p in self.players.values()
                if p.role == Role.VILLAGER and p.is_alive]

    def get_gods(self) -> List[int]:
        return [p.id for p in self.players.values()
                if p.role in [Role.SEER, Role.WITCH, Role.HUNTER, Role.GUARD]
                and p.is_alive]

    def is_game_over(self) -> bool:
        """
        检查游戏是否结束（屠边规则）

        检查顺序：
        1. 先检查狼人是否全灭（好人胜利）
        2. 再检查屠边条件（村民全灭 OR 神职全灭 → 狼人胜利）
        3. 极端情况：村民和神职同时全灭 → 狼人胜利

        注意：游戏结束判断在猎人技能执行后立即检查
        """
        wolves = self.get_werewolves()
        villagers = self.get_villagers()
        gods = self.get_gods()

        # 1. 狼人全灭 → 好人胜利（优先检查）
        if len(wolves) == 0:
            self.game_over = True
            self.winner = "good"
            self.reason = "all_wolves_dead"
            return True

        # 2. 屠边规则：村民全灭 OR 神职全灭 → 狼人胜利
        if len(villagers) == 0 or len(gods) == 0:
            self.game_over = True
            self.winner = "werewolf"
            if len(villagers) == 0 and len(gods) == 0:
                # 极端情况：村民和神职同时全灭
                self.reason = "all_good_dead"
            elif len(villagers) == 0:
                self.reason = "all_villagers_dead"
            else:
                self.reason = "all_gods_dead"
            return True

        return False

    def get_last_words_flag(self, death_cause: DeathCause, current_night: int) -> bool:
        """
        判断是否有遗言

        参数:
            death_cause: 死亡原因
            current_night: 当前夜晚编号（用于判断是否首夜）

        规则：
        1. 首夜死亡 → 有遗言
        2. 白天被放逐 → 有遗言
        3. 后续夜晚死亡 → 无遗言
        4. 同守同救死亡 → 有遗言（正常死亡）
        5. 自爆 → 无遗言
        6. 决斗死亡 → 有遗言
        7. 被猎人开枪 → 有遗言（首夜）
        """
        if death_cause == DeathCause.VOTE_OUT:
            return True  # 被放逐有遗言
        elif death_cause == DeathCause.SELF_EXPLODE:
            return False  # 自爆无遗言
        elif death_cause == DeathCause.SAME_NIGHT_SAVE_CONFLICT:
            return True  # 同守同救有遗言
        elif death_cause == DeathCause.DUEL:
            return True  # 决斗有遗言
        elif death_cause == DeathCause.HUNTER_SHOT:
            return current_night == 1  # 被猎人开枪（首夜有遗言）
        elif death_cause == DeathCause.WOLF_ATTACK:
            return current_night == 1  # 首夜被刀有遗言
        elif death_cause == DeathCause.POISON:
            return current_night == 1  # 首夜被毒有遗言
        else:
            return False  # 默认无遗言