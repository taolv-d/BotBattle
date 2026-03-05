"""狼人杀阶段定义"""
from enum import Enum


class WerewolfPhases(Enum):
    """狼人杀游戏阶段"""
    NIGHT_WEREWOLF = "night_werewolf"     # 狼人行动
    NIGHT_SEER = "night_seer"             # 预言家行动
    NIGHT_WITCH = "night_witch"           # 女巫行动
    DAY_DISCUSS = "day_discuss"           # 白天讨论
    DAY_VOTE = "day_vote"                 # 投票放逐
