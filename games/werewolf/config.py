from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


class Role(Enum):
    """角色枚举"""
    WEREWOLF = "werewolf"
    VILLAGER = "villager"
    SEER = "seer"
    WITCH = "witch"
    HUNTER = "hunter"
    GUARD = "guard"


class DeathCause(Enum):
    """死亡原因枚举"""
    WOLF_ATTACK = "wolf_attack"              # 被狼刀
    VOTE_OUT = "vote_out"                    # 被投票放逐
    POISON = "poison"                        # 被女巫毒杀
    SELF_EXPLODE = "self_explode"            # 自爆
    DUEL = "duel"                            # 决斗死亡
    SAME_NIGHT_SAVE_CONFLICT = "same_night_save_conflict"  # 同守同救
    HUNTER_SHOT = "hunter_shot"              # 被猎人开枪


@dataclass
class GameConfig:
    """游戏配置类"""
    player_count: int
    roles: List[Dict[str, Any]]
    personalities: List[str]
    rules: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.rules is None:
            self.rules = {}
        # 默认规则
        self.rules.setdefault("witch_can_self_heal", True)
        self.rules.setdefault("hunter_can_shoot_if_poisoned", False)
        self.rules.setdefault("witch_same_night_dual_use", False)
        self.rules.setdefault("witch_cannot_poison_first_night", False)
        self.rules.setdefault("hunter_can_shoot_if_same_save_conflict", False)
        self.rules.setdefault("president_can_inherit", True)

    def validate(self) -> tuple[bool, List[str], List[str]]:
        """
        验证配置是否合法

        Returns:
            (是否合法，错误消息列表，警告消息列表)
        """
        errors = []
        warnings = []

        # 1. 检查玩家数量与角色数量匹配
        total_players = sum(r["count"] for r in self.roles)
        if total_players != self.player_count:
            errors.append(f"角色总数{total_players}与玩家数量{self.player_count}不匹配")

        # 2. 检查必要角色
        role_names = [r["role"] for r in self.roles]
        if "werewolf" not in role_names:
            errors.append("必须包含狼人角色")

        # 3. 检查狼人数量合理（不超过一半）
        wolf_count = next((r["count"] for r in self.roles if r["role"] == "werewolf"), 0)
        if wolf_count < 1:
            errors.append("狼人数量至少为 1")
        elif wolf_count > self.player_count // 2:
            errors.append(f"狼人数量{wolf_count}超过玩家数一半")

        # 4. 检查人格数量足够
        if len(self.personalities) < self.player_count:
            errors.append(f"人格数量{len(self.personalities)}少于玩家数量")

        # 5. 检查神职数量合理（警告而非错误）
        # 注意：9 人标准局有 3 个神职，所以>=2 是合理的
        god_roles = ["seer", "witch", "hunter", "guard"]
        god_count = sum(r["count"] for r in self.roles if r["role"] in god_roles)
        if god_count < 2:
            warnings.append(f"神职数量{god_count}较少，可能影响游戏平衡")

        # 6. 检查村民数量合理
        villager_count = next((r["count"] for r in self.roles if r["role"] == "villager"), 0)
        if villager_count < 1:
            errors.append("村民数量至少为 1")

        is_valid = len(errors) == 0
        return is_valid, errors, warnings