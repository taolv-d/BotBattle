"""狼人杀角色定义"""
from enum import Enum


class WerewolfRoles(Enum):
    """狼人杀角色"""
    WEREWOLF = "werewolf"  # 狼人
    VILLAGER = "villager"  # 村民
    SEER = "seer"          # 预言家
    WITCH = "witch"        # 女巫
    HUNTER = "hunter"      # 猎人
    
    @classmethod
    def get_description(cls, role: "WerewolfRoles") -> str:
        """获取角色描述"""
        descriptions = {
            cls.WEREWOLF: "夜晚可以袭击其他玩家，白天需要伪装身份",
            cls.VILLAGER: "没有特殊能力，需要找出狼人",
            cls.SEER: "每晚可以查验一名玩家的身份",
            cls.WITCH: "有一瓶解药和一瓶毒药",
            cls.HUNTER: "死亡时可以带走一名玩家",
        }
        return descriptions.get(role, "未知角色")
