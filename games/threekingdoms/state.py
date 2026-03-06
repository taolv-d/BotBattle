"""三国杀数据结构"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class Role(Enum):
    """身份"""
    LORD = "主公"        # 主公
    LOYALIST = "忠臣"    # 忠臣
    REBEL = "反贼"       # 反贼
    RENEGADE = "内奸"    # 内奸


class Phase(Enum):
    """游戏阶段"""
    GAME_START = "game_start"       # 游戏开始
    TURN_START = "turn_start"       # 回合开始
    JUDGE = "judge"                 # 判定阶段
    DRAW = "draw"                   # 摸牌阶段
    PLAY = "play"                   # 出牌阶段
    DISCARD = "discard"             # 弃牌阶段
    TURN_END = "turn_end"           # 回合结束
    DYING = "dying"                 # 濒死结算
    GAME_OVER = "game_over"         # 游戏结束


class CardType(Enum):
    """卡牌类型"""
    BASIC = "basic"         # 基本牌
    TRICK = "trick"         # 锦囊牌
    EQUIPMENT = "equipment" # 装备牌


class BasicType(Enum):
    """基本牌类型"""
    SLASH = "slash"     # 杀
    DODGE = "dodge"     # 闪
    PEACH = "peach"     # 桃
    WINE = "wine"       # 酒


class TrickType(Enum):
    """锦囊牌类型"""
    # 非延时锦囊
    RIVER_DENY = "river_deny"       # 过河拆桥
    HAND_STEAL = "hand_steal"       # 顺手牵羊
    PEACH_GARDEN = "peach_garden"   # 桃园结义
    BARBARIAN = "barbarian"         # 南蛮入侵
    ARROW_VOLLEY = "arrow_volley"   # 万箭齐发
    DUEL = "duel"                   # 决斗
    NULLIFICATION = "nullification" # 无懈可击

    # 延时锦囊
    LEARNING = "learning"           # 乐不思蜀
    SUPPLY_BLOCK = "supply_block"   # 兵粮寸断
    LIGHTNING = "lightning"         # 闪电


class EquipmentType(Enum):
    """装备牌类型"""
    WEAPON = "weapon"           # 武器
    ARMOR = "armor"             # 防具
    HORSE_MINUS = "horse_minus" # -1 马（进攻马）
    HORSE_PLUS = "horse_plus"   # +1 马（防御马）


# === 修复 P2-6: 武将技能定义 ===
class GeneralSkill(Enum):
    """武将技能"""
    # 主公武将
    LIUBEI_JIANG = "jiang"          # 激将：主公技，可以令其他蜀势力角色出杀
    CAOCAO_HUJIA = "hujia"          # 护驾：主公技，可以令其他魏势力角色出闪
    SUNQUAN_ZHI = "zhi"             # 制衡：出牌阶段限一次，可以弃置任意张牌，然后摸等量的牌
    
    # 蜀势力
    ZHAOYUN_LONG = "long"           # 龙胆：可以将杀当闪、闪当杀使用
    ZHUGELIANG_KONG = "kong"        # 空城：锁定技，若没有手牌，不能成为杀或决斗的目标
    GUANYU_WU = "wu"                # 武圣：可以将红色牌当杀使用
    HUANGYUE_JI = "ji"              # 集智：使用锦囊牌时可以摸一张牌
    ZHANGFEI_PAO = "pao"            # 咆哮：出杀无次数限制
    
    # 魏势力
    XIAHOU_DUN = "dun"              # 刚烈：受到伤害后可以判定，若结果为黑色则来源掉血
    SIMAYI_GUI = "gui"              # 鬼才：可以改判定
    XIADUN_ROU = "rou"              # 肉盾（简化）
    
    # 吴势力
    ZHOUYU_FAN = "fan"              # 反间：可以令一名角色猜花色，猜错掉血
    QIAO_GUO = "guo"                # 国色：可以将方片牌当乐不思蜀使用
    HUANGGAI_KU = "ku"              # 苦肉：出牌阶段可以自减 1 点体力，然后摸两张牌
    
    # 群势力
    LVBU_FENG = "feng"              # 无双：出杀需要两张闪才能抵消
    DIAOCHAN_BI = "bi"              # 闭月：回合结束时可以摸一张牌


@dataclass
class General:
    """武将定义"""
    name: str                       # 武将名
    kingdom: str                    # 势力：蜀/魏/吴/群
    hp: int                         # 体力值
    skills: list[GeneralSkill]      # 技能列表
    description: str = ""           # 武将描述


# 标准武将列表
STANDARD_GENERALS = {
    "刘备": General("刘备", "蜀", 4, [GeneralSkill.LIUBEI_JIANG], "蜀汉主公，可以激将其他蜀势力角色"),
    "曹操": General("曹操", "魏", 4, [GeneralSkill.CAOCAO_HUJIA], "魏国主公，可以护驾其他魏势力角色"),
    "孙权": General("孙权", "吴", 4, [GeneralSkill.SUNQUAN_ZHI], "吴国主公，可以制衡换牌"),
    "赵云": General("赵云", "蜀", 4, [GeneralSkill.ZHAOYUN_LONG], "常山赵子龙，杀闪互用"),
    "诸葛亮": General("诸葛亮", "蜀", 3, [GeneralSkill.ZHUGELIANG_KONG], "卧龙，空城计"),
    "关羽": General("关羽", "蜀", 4, [GeneralSkill.GUANYU_WU], "武圣，红色牌当杀"),
    "黄月英": General("黄月英", "蜀", 3, [GeneralSkill.HUANGYUE_JI], "诸葛之妻，使用锦囊摸牌"),
    "张飞": General("张飞", "蜀", 4, [GeneralSkill.ZHANGFEI_PAO], "猛张飞，出杀无限制"),
    "夏侯惇": General("夏侯惇", "魏", 4, [GeneralSkill.XIAHOU_DUN], "独眼将军，刚烈反击"),
    "司马懿": General("司马懿", "魏", 3, [GeneralSkill.SIMAYI_GUI], "冢虎，改判定"),
    "周瑜": General("周瑜", "吴", 3, [GeneralSkill.ZHOUYU_FAN], "美周郎，反间伤人"),
    "大乔": General("大乔", "吴", 3, [GeneralSkill.QIAO_GUO], "国色天香"),
    "黄盖": General("黄盖", "吴", 4, [GeneralSkill.HUANGGAI_KU], "苦肉计"),
    "吕布": General("吕布", "群", 4, [GeneralSkill.LVBU_FENG], "飞将，无双"),
    "貂蝉": General("貂蝉", "群", 3, [GeneralSkill.DIAOCHAN_BI], "闭月羞花"),
}


@dataclass
class Card:
    """卡牌基类"""
    name: str                   # 牌名
    suit: str                   # 花色 ♠♥♣♦
    number: int                 # 点数 1-13
    card_type: CardType         # 卡牌类型
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "suit": self.suit,
            "number": self.number,
            "card_type": self.card_type.value,
        }


@dataclass
class BasicCard(Card):
    """基本牌"""
    subtype: BasicType          # 基本牌类型


@dataclass
class TrickCard(Card):
    """锦囊牌"""
    subtype: TrickType          # 锦囊类型
    is_delayed: bool = False    # 是否延时锦囊


@dataclass
class EquipmentCard(Card):
    """装备牌"""
    subtype: EquipmentType      # 装备类型
    attack_range: int = 1       # 武器攻击范围（仅武器有效）
    effect: str = ""            # 装备效果描述


@dataclass
class Equipment:
    """装备区"""
    weapon: Optional[EquipmentCard] = None       # 武器
    armor: Optional[EquipmentCard] = None        # 防具
    horse_minus: Optional[EquipmentCard] = None  # -1 马（进攻马）
    horse_plus: Optional[EquipmentCard] = None   # +1 马（防御马）
    
    def get_attack_range(self) -> int:
        """获取攻击范围（武器决定）"""
        if self.weapon:
            return self.weapon.attack_range
        return 1  # 默认攻击范围
    
    def equip(self, card: EquipmentCard) -> Optional[EquipmentCard]:
        """
        装备卡牌，返回被替换的旧装备
        
        Args:
            card: 要装备的牌
        
        Returns:
            被替换的旧装备，如果没有则为 None
        """
        old_equipment = None
        
        if card.subtype == EquipmentType.WEAPON:
            old_equipment = self.weapon
            self.weapon = card
        elif card.subtype == EquipmentType.ARMOR:
            old_equipment = self.armor
            self.armor = card
        elif card.subtype == EquipmentType.HORSE_MINUS:
            old_equipment = self.horse_minus
            self.horse_minus = card
        elif card.subtype == EquipmentType.HORSE_PLUS:
            old_equipment = self.horse_plus
            self.horse_plus = card
        
        return old_equipment
    
    def to_dict(self) -> dict:
        return {
            "weapon": self.weapon.name if self.weapon else None,
            "armor": self.armor.name if self.armor else None,
            "horse_minus": self.horse_minus.name if self.horse_minus else None,
            "horse_plus": self.horse_plus.name if self.horse_plus else None,
            "attack_range": self.get_attack_range(),
        }


@dataclass
class ThreeKingdomsPlayer:
    """三国杀玩家状态"""
    id: int
    name: str
    general: str                # 武将名
    role: Role                  # 身份
    celebrity_name: str = ""       # 名人名字
    position: int = 0           # 座位位置（1-玩家数量）
    hp: int = 4                 # 当前体力
    max_hp: int = 4             # 体力上限
    hand_cards: list[Card] = field(default_factory=list)  # 手牌列表
    equipped: Equipment = field(default_factory=Equipment)  # 装备区
    judged: list[Card] = field(default_factory=list)  # 判定区（延时锦囊）
    is_alive: bool = True
    is_human: bool = False      # 是否人类玩家
    is_bot: bool = True         # 是否 AI 玩家
    agent: Optional[object] = None  # AI 代理（可选）
    skill_state: dict = field(default_factory=dict)  # 技能状态
    slash_count: int = 0        # 本回合已出杀次数

    def get_display_name(self, show_celebrity: bool = True) -> str:
        """获取显示名字"""
        if show_celebrity and self.celebrity_name:
            return f"{self.name}({self.celebrity_name})"
        return self.name

    def to_dict(self, reveal_all: bool = False) -> dict:
        """
        转换为字典

        Args:
            reveal_all: 是否公开所有信息（上帝视角）

        Returns:
            玩家状态字典
        """
        if reveal_all:
            return {
                "id": self.id,
                "name": self.name,
                "celebrity_name": self.celebrity_name,
                "general": self.general,
                "role": self.role.value,
                "hp": self.hp,
                "max_hp": self.max_hp,
                "hand_cards": [c.to_dict() for c in self.hand_cards],
                "hand_count": len(self.hand_cards),
                "equipped": self.equipped.to_dict(),
                "judged": [c.name for c in self.judged],
                "is_alive": self.is_alive,
                "skill_state": self.skill_state,
            }
        else:
            # 只公开部分信息
            return {
                "id": self.id,
                "name": self.name,
                "celebrity_name": self.celebrity_name,
                "general": self.general,
                "hp": self.hp,
                "max_hp": self.max_hp,
                "hand_count": len(self.hand_cards),
                "equipped": self.equipped.to_dict(),
                "judged": [c.name for c in self.judged],
                "is_alive": self.is_alive,
            }
    
    def get_distance_to(self, target: "ThreeKingdomsPlayer") -> int:
        """
        计算到目标玩家的距离
        修复：实现基于座位位置的距离计算
        - 基础距离 = |玩家 A 位置 - 玩家 B 位置|（环形计算）
        - -1 马减少距离（进攻马）
        - +1 马增加被距离（防御马）

        Args:
            target: 目标玩家

        Returns:
            距离值
        """
        if not self.is_alive or not target.is_alive:
            return 999  # 死亡玩家无法计算距离
        
        # 计算环形距离（顺时针）
        position_diff = (target.position - self.position) % 10  # 假设最多 10 人
        if position_diff == 0:
            base_distance = 0  # 同一个位置（不应该发生）
        else:
            # 取顺时针和逆时针的较短距离
            reverse_diff = 10 - position_diff
            base_distance = min(position_diff, reverse_diff)
        
        # -1 马减少距离（进攻马）
        if self.equipped.horse_minus:
            base_distance -= 1
            print(f"[DEBUG] {self.name} 装备 -1 马，距离 -1")

        # +1 马增加被距离（防御马）
        if target.equipped.horse_plus:
            base_distance += 1
            print(f"[DEBUG] {target.name} 装备 +1 马，距离 +1")

        return max(1, base_distance)  # 最小距离为 1
    
    def can_attack(self, target: "ThreeKingdomsPlayer") -> bool:
        """
        判断是否可以攻击目标
        
        Args:
            target: 目标玩家
        
        Returns:
            是否可以攻击
        """
        if not self.is_alive or not target.is_alive:
            return False
        
        distance = self.get_distance_to(target)
        attack_range = self.equipped.get_attack_range()
        
        return distance <= attack_range
