"""三国杀游戏引擎"""
import json
import time
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

from .state import (
    Card, BasicCard, TrickCard, EquipmentCard,
    Equipment, ThreeKingdomsPlayer, Role, Phase,
    CardType, BasicType, TrickType, EquipmentType,
    GeneralSkill, STANDARD_GENERALS, General  # 添加武将相关导入
)
from ui.base import UIBase
from ai.names import NameGenerator
from ai.llm_client import LLMClient


# 标准牌堆定义
def create_standard_deck() -> list[Card]:
    """创建标准三国杀牌堆"""
    deck = []
    
    # 基本牌
    basic_cards = [
        # 杀 (30 张)
        (BasicType.SLASH, "杀", "♠", [7, 8, 9, 10, 11, 12, 13, 5, 6, 7, 8, 9, 10, 11, 12, 13]),
        (BasicType.SLASH, "杀", "♥", [6, 7, 8, 9, 10, 11, 12]),
        (BasicType.SLASH, "杀", "♣", [5, 6, 7, 8, 9, 10, 11, 12, 13]),
        (BasicType.SLASH, "杀", "♦", [4, 5, 6, 7, 8, 9, 10, 11]),
        # 闪 (15 张)
        (BasicType.DODGE, "闪", "♠", [2, 3, 4, 5, 6, 7]),
        (BasicType.DODGE, "闪", "♥", [2, 3, 4, 5, 6, 7]),
        (BasicType.DODGE, "闪", "♣", [2, 3, 4, 5, 6]),
        (BasicType.DODGE, "闪", "♦", [2, 3, 4, 5, 6]),
        # 桃 (8 张)
        (BasicType.PEACH, "桃", "♥", [2, 3, 4, 5, 6, 7, 8, 12]),
        # 酒 (5 张)
        (BasicType.WINE, "酒", "♠", [1, 9]),
        (BasicType.WINE, "酒", "♣", [1, 9]),
        (BasicType.WINE, "酒", "♦", [9]),
    ]
    
    for subtype, name, suit, numbers in basic_cards:
        for num in numbers:
            deck.append(BasicCard(
                name=name, suit=suit, number=num,
                card_type=CardType.BASIC, subtype=subtype
            ))
    
    # 锦囊牌（简化版）
    trick_cards = [
        (TrickType.RIVER_DENY, "过河拆桥", "♠", [3, 4, 10, 11, 12]),
        (TrickType.RIVER_DENY, "过河拆桥", "♣", [3, 4]),
        (TrickType.HAND_STEAL, "顺手牵羊", "♠", [3, 4]),
        (TrickType.HAND_STEAL, "顺手牵羊", "♥", [4]),
        (TrickType.PEACH_GARDEN, "桃园结义", "♥", [1]),
        (TrickType.BARBARIAN, "南蛮入侵", "♠", [7]),
        (TrickType.BARBARIAN, "南蛮入侵", "♣", [7]),
        (TrickType.ARROW_VOLLEY, "万箭齐发", "♥", [13]),
        (TrickType.DUEL, "决斗", "♠", [1]),
        (TrickType.DUEL, "决斗", "♣", [1]),
        (TrickType.NULLIFICATION, "无懈可击", "♠", [1, 2]),
        (TrickType.NULLIFICATION, "无懈可击", "♥", [1]),
        (TrickType.LEARNING, "乐不思蜀", "♥", [6, 10]),
        (TrickType.LEARNING, "乐不思蜀", "♠", [6]),
        (TrickType.SUPPLY_BLOCK, "兵粮寸断", "♠", [13]),
        (TrickType.SUPPLY_BLOCK, "兵粮寸断", "♣", [6, 10]),
        (TrickType.LIGHTNING, "闪电", "♠", [2, 3]),
        (TrickType.LIGHTNING, "闪电", "♥", [2]),
    ]
    
    for subtype, name, suit, numbers in trick_cards:
        for num in numbers:
            is_delayed = subtype in [TrickType.LEARNING, TrickType.SUPPLY_BLOCK, TrickType.LIGHTNING]
            deck.append(TrickCard(
                name=name, suit=suit, number=num,
                card_type=CardType.TRICK, subtype=subtype,
                is_delayed=is_delayed
            ))
    
    # 装备牌
    equipment_cards = [
        # 武器
        (EquipmentType.WEAPON, "诸葛连弩", "♠", 1, 1, "可以无限出杀"),
        (EquipmentType.WEAPON, "青龙偃月刀", "♠", 5, 2, "攻击范围 2"),
        (EquipmentType.WEAPON, "方天画戟", "♠", 12, 4, "攻击范围 4"),
        (EquipmentType.WEAPON, "丈八蛇矛", "♠", 6, 3, "攻击范围 3"),
        (EquipmentType.WEAPON, "贯石斧", "♠", 11, 3, "攻击范围 3"),
        (EquipmentType.WEAPON, "雌雄双股剑", "♠", 2, 2, "攻击范围 2"),
        # 防具
        (EquipmentType.ARMOR, "八卦阵", "♠", 2, 1, "需要出杀时判定"),
        (EquipmentType.ARMOR, "仁王盾", "♠", 2, 1, "黑色杀无效"),
        # 马
        (EquipmentType.HORSE_MINUS, "-1 马", "♠", 3, 1, "攻击距离 -1"),
        (EquipmentType.HORSE_MINUS, "-1 马", "♥", 13, 1, "攻击距离 -1"),
        (EquipmentType.HORSE_PLUS, "+1 马", "♠", 4, 1, "被攻击距离 +1"),
        (EquipmentType.HORSE_PLUS, "+1 马", "♣", 5, 1, "被攻击距离 +1"),
    ]
    
    for subtype, name, suit, number, attack_range, effect in equipment_cards:
        deck.append(EquipmentCard(
            name=name, suit=suit, number=number,
            card_type=CardType.EQUIPMENT, subtype=subtype,
            attack_range=attack_range, effect=effect
        ))
    
    return deck


class ThreeKingdomsEngine:
    """三国杀游戏引擎"""
    
    def __init__(self, ui: UIBase, config: dict):
        """
        Args:
            ui: UI 接口
            config: 系统配置
        """
        self.ui = ui
        self.config = config
        self.players: dict[int, ThreeKingdomsPlayer] = {}
        self.deck: list[Card] = []
        self.discard_pile: list[Card] = []
        self.current_player_id: Optional[int] = None
        self.damage_source: Optional[int] = None
        self.phase: Phase = Phase.GAME_START
        self.turn_count: int = 0
        self.log_file: Optional[str] = None
        self.history: list[dict] = []

        # 配置
        self.identity_reveal_on_death = True  # 死亡时公开身份
        self.dying_request_peach = True       # 濒死求桃
        self.victory_condition = "simplified" # 简化胜负判定
        
        # 名字生成器
        self.name_generator = NameGenerator()
    
    def setup(self, player_count: int, roles_config: list[dict],
              generals: list[str], human_player_id: Optional[int] = None) -> None:
        """
        设置游戏
        
        Args:
            player_count: 玩家数量
            roles_config: 身份配置
            generals: 武将列表
            human_player_id: 人类玩家 ID
        """
        # 分配身份
        all_roles = []
        for rc in roles_config:
            all_roles.extend([Role(rc["role"])] * rc["count"])
        random.shuffle(all_roles)
        
        # 选将（随机 3 选 1）
        random.shuffle(generals)
        
        # 创建玩家
        for i in range(1, player_count + 1):
            role = all_roles[i-1] if i-1 < len(all_roles) else Role.REBEL
            
            # 选将
            if i * 3 <= len(generals):
                candidate_generals = generals[(i-1)*3:i*3]
            else:
                candidate_generals = generals[-3:]
            
            # 简化：直接选第一个（实际应该让玩家选择）
            selected_general = candidate_generals[0]
            
            # 体力值（根据武将，简化为主公 4 血，其他 3-4 血）
            max_hp = 4 if role == Role.LORD else (3 if i % 2 == 0 else 4)

            player = ThreeKingdomsPlayer(
                id=i,
                name=f"{i}号玩家",
                general=selected_general,
                role=role,
                hp=max_hp,
                max_hp=max_hp,
                position=i,  # 设置座位位置
                is_human=(i == human_player_id),
                is_bot=(i != human_player_id),
            )
            # === 修复 P2-6: 初始化武将技能 ===
            if selected_general in STANDARD_GENERALS:
                general_info = STANDARD_GENERALS[selected_general]
                player.skill_state["general"] = selected_general
                player.skill_state["kingdom"] = general_info.kingdom
                player.skill_state["skills"] = [s.value for s in general_info.skills]
                # 初始化技能状态
                for skill in general_info.skills:
                    player.skill_state[f"skill_{skill.value}_used"] = False
                    player.skill_state[f"skill_{skill.value}_active"] = True
            # 分配名人名字（使用默认人格"passive"）
            player.celebrity_name = self.name_generator.assign_name_to_player(i, "passive")
            
            # === 修复：初始化 AI agent ===
            if i != human_player_id:  # AI 玩家
                from games.threekingdoms.agent import ThreeKingdomsAgent
                from ai.personality import Personality
                
                # 使用默认人格
                try:
                    personality = Personality({
                        "name": "passive",
                        "description": "被动型人格",
                        "traits": ["理性"],
                        "speech_style": {"min_length": 10, "max_length": 50, "tone": "中性"}
                    })
                    # 使用配置的 LLM
                    llm_client = LLMClient(self.config) if self.config else None
                    player.agent = ThreeKingdomsAgent(
                        player_id=i,
                        general=selected_general,
                        role=role.value,
                        personality=personality,
                        llm_client=llm_client
                    )
                except Exception as e:
                    print(f"[WARN] 创建 AI agent 失败：{e}，使用规则逻辑")
                    player.agent = None
            
            self.players[i] = player

        # 创建牌堆
        self.deck = create_standard_deck()
        random.shuffle(self.deck)

        # 初始化日志
        self._init_log()

        # 记录游戏设置
        self._log_event("game_setup_3k", {
            "player_count": player_count,
            "roles": [r.value for r in all_roles],
            "generals": generals,
            "celebrity_names": {str(k): v.celebrity_name for k, v in self.players.items()},
        })
        
        # 发初始手牌（4 张）
        for player in self.players.values():
            self._draw_cards(player, 4)
    
    def _init_log(self) -> None:
        """初始化日志文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"logs/3k_game_{timestamp}.json"
        Path("logs").mkdir(exist_ok=True)
    
    def _save_log(self) -> None:
        """保存日志"""
        if self.log_file:
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump({
                    "players": {k: v.to_dict(reveal_all=True) for k, v in self.players.items()},
                    "history": self.history,
                }, f, ensure_ascii=False, indent=2)
    
    def _log_event(self, event_type: str, data: dict) -> None:
        """记录事件"""
        self.history.append({"type": event_type, "data": data, "timestamp": datetime.now().isoformat()})
        self._save_log()
    
    def start(self) -> None:
        """开始游戏"""
        self.ui.notify_game_event("game_start", {"players": len(self.players)})
        self._log_event("game_start", {"player_count": len(self.players)})

        # 设置 UI 的游戏状态（用于显示名人名字和身份）
        if hasattr(self.ui, "set_game_state"):
            self.ui.set_game_state(self.players, None)  # 三国杀暂不支持人类玩家

        # 显示各玩家信息（上帝视角）
        self._update_game_board()

        # 显示各玩家角色（仅自己可见）
        for player in self.players.values():
            if player.is_human:
                self.ui.display_system_message(f"你的角色是：{player.role.value}，武将：{player.general}")
        
        # 确定起始玩家（主公先手）
        lord_id = next((p.id for p in self.players.values() if p.role == Role.LORD), 1)
        self.current_player_id = lord_id
        
        # 游戏主循环
        while not self._check_game_over():
            self._run_turn()

        # 游戏结束
        self._end_game()

    def _run_turn(self) -> None:
        """运行一个回合"""
        player = self.players[self.current_player_id]

        if not player.is_alive:
            self._next_player()
            return

        self.turn_count += 1
        self.ui.notify_game_event("turn_start", {
            "player_id": player.id,
            "general": player.general,
        })
        self._log_event("turn_start", {
            "player_id": player.id,
            "general": player.general,
            "hp": player.hp,
        })

        # 重置状态
        player.slash_count = 0
        # === 修复 P2-6: 重置每回合技能状态 ===
        for key in list(player.skill_state.keys()):
            if key.endswith("_used"):
                player.skill_state[key] = False

        # 1. 判定阶段
        self._phase_judge(player)

        if not player.is_alive:
            self._next_player()
            return

        # 2. 摸牌阶段
        self._phase_draw(player)

        # 3. 出牌阶段
        self._phase_play(player)

        # === 修复 P2-6: 回合结束时触发技能（如貂蝉闭月） ===
        self._trigger_end_turn_skill(player)

        # 4. 弃牌阶段
        self._phase_discard(player)

        # 回合结束
        self._log_event("turn_end", {"player_id": player.id})

        # 检查游戏是否结束
        if self._check_game_over():
            # 显示获胜消息
            self.ui.display_system_message(self._get_winner_message())
            return

        # 下一个玩家
        self._next_player()
    
    def _phase_judge(self, player: ThreeKingdomsPlayer) -> None:
        """判定阶段"""
        self.phase = Phase.JUDGE
        self.ui.display_system_message(f"=== {player.name} 判定阶段 ===")
        
        # 处理延时锦囊
        judged_cards = []
        for card in player.judged:
            result = self._judge_card(player, card)
            if result:
                judged_cards.append(card)
        
        # 移除已结算的延时锦囊
        for card in judged_cards:
            player.judged.remove(card)
            self.discard_pile.append(card)
        
        self._log_event("phase_judge", {
            "player_id": player.id,
            "judged_cards": [c.name for c in judged_cards],
        })
    
    def _judge_card(self, player: ThreeKingdomsPlayer, card: TrickCard) -> bool:
        """
        判定单张延时锦囊
        
        Returns:
            True 表示需要移除，False 表示保留
        """
        if card.subtype == TrickType.LEARNING:
            # 乐不思蜀 - 判定红色则跳过出牌阶段
            suit = card.suit
            is_red = suit in ["♥", "♦"]
            self.ui.display_system_message(f"{player.name} 乐不思蜀判定：{card.suit}{card.number}，{'红色' if is_red else '黑色'}")
            if is_red:
                self.ui.display_system_message(f"{player.name} 跳过出牌阶段")
                self._log_event("judge_result", {
                    "player_id": player.id,
                    "card": card.name,
                    "result": "skip_play",
                })
                return True  # 跳过出牌阶段
            return False  # 正常出牌
        
        elif card.subtype == TrickType.SUPPLY_BLOCK:
            # 兵粮寸断 - 判定红色则跳过摸牌
            suit = card.suit
            is_red = suit in ["♥", "♦"]
            self.ui.display_system_message(f"{player.name} 兵粮寸断判定：{card.suit}{card.number}，{'红色' if is_red else '黑色'}")
            if is_red:
                self.ui.display_system_message(f"{player.name} 跳过摸牌阶段")
                self._log_event("judge_result", {
                    "player_id": player.id,
                    "card": card.name,
                    "result": "skip_draw",
                })
                # 标记跳过摸牌（需要在摸牌阶段处理）
                player.skill_state["skip_draw"] = True
            return False
        
        elif card.subtype == TrickType.LIGHTNING:
            # 闪电 - 判定黑桃 2-9 受到 3 点伤害
            suit = card.suit
            number = card.number
            is_black_2_9 = suit in ["♠", "♣"] and 2 <= number <= 9
            self.ui.display_system_message(f"{player.name} 闪电判定：{card.suit}{card.number}")
            if is_black_2_9:
                self.ui.display_system_message(f"{player.name} 被闪电击中，受到 3 点伤害！")
                self._deal_damage(source=None, target=player, damage=3)
                self._log_event("judge_result", {
                    "player_id": player.id,
                    "card": card.name,
                    "result": "damage_3",
                })
            else:
                # 闪电传递给下家
                next_player = self._get_next_alive_player(player.id)
                if next_player:
                    next_player.judged.append(card)
                    self.ui.display_system_message(f"闪电传递给{next_player.name}")
            return True  # 移除闪电
        
        return False
    
    def _phase_draw(self, player: ThreeKingdomsPlayer) -> None:
        """摸牌阶段"""
        self.phase = Phase.DRAW
        
        # 检查是否跳过摸牌
        if player.skill_state.get("skip_draw"):
            player.skill_state["skip_draw"] = False
            self.ui.display_system_message(f"{player.name} 跳过摸牌阶段")
            self._log_event("phase_draw", {"player_id": player.id, "skipped": True})
            return
        
        self.ui.display_system_message(f"=== {player.name} 摸牌阶段 ===")
        drawn_cards = self._draw_cards(player, 2)
        
        self.ui.display_system_message(f"{player.name} 摸了{len(drawn_cards)}张牌")
        self._log_event("phase_draw", {
            "player_id": player.id,
            "drawn_cards": [c.name for c in drawn_cards],
        })
        
        # 更新看板
        self._update_game_board()
    
    def _phase_play(self, player: ThreeKingdomsPlayer) -> None:
        """出牌阶段"""
        self.phase = Phase.PLAY
        self.ui.display_system_message(f"=== {player.name} 出牌阶段 ===")
        self._update_game_board()
        
        # 简化实现：AI 自动出牌，人类玩家手动出牌
        if player.is_human:
            self._human_play_phase(player)
        else:
            self._ai_play_phase(player)
    
    def _human_play_phase(self, player: ThreeKingdomsPlayer) -> None:
        """人类玩家出牌阶段"""
        while True:
            self._update_game_board()
            
            # 显示手牌
            hand_str = ", ".join([f"{c.name}({c.suit}{c.number})" for c in player.hand_cards])
            self.ui.display_system_message(f"你的手牌：{hand_str}")
            
            choice = self.ui.get_player_input("出牌 (输入牌名或 skip 结束): ")
            
            if choice.lower() == "skip":
                break
            
            # 找牌
            card_to_play = None
            for card in player.hand_cards:
                if card.name in choice:
                    card_to_play = card
                    break
            
            if not card_to_play:
                self.ui.display_system_message("没有找到这张牌")
                continue
            
            # 出牌
            self._play_card(player, card_to_play)
    
    def _ai_play_phase(self, player: ThreeKingdomsPlayer) -> None:
        """AI 玩家出牌阶段
        修复 P2-4: 增加身份判断和战术决策
        修复 P2-6: 支持武将技能
        - 张飞咆哮：出杀无次数限制
        - 黄盖苦肉：可以自减体力摸牌
        - 孙权制衡：可以换牌
        """
        # === 修复 P2-6: 黄盖苦肉（优先） ===
        if "ku" in player.skill_state.get("skills", []):
            # 简化：黄盖 AI 有概率发动苦肉
            import random
            if player.hp > 2 and random.random() < 0.5:
                self._trigger_huanggai_ku(player)
        
        # === 修复 P2-6: 孙权制衡（优先） ===
        if "zhi" in player.skill_state.get("skills", []):
            # 简化：孙权 AI 发动制衡弃掉废牌
            if len(player.hand_cards) > 1:
                # 弃掉一半手牌（简化策略）
                cards_to_discard = player.hand_cards[:len(player.hand_cards)//2]
                self._skill_sunquan_zhi(player, cards_to_discard)

        # AI 自动出牌，有杀就出，有装备就装，有锦囊就用
        played = True
        while played and player.is_alive:
            played = False

            # 1. 尝试使用锦囊牌（优先）
            trick_card = self._find_usable_trick(player)
            if trick_card:
                player.hand_cards.remove(trick_card)
                self._use_trick_card(player, trick_card)
                self.discard_pile.append(trick_card)
                played = True
                self._update_game_board()
                time.sleep(0.5)
                continue

            # 2. 尝试出杀（根据身份选择目标）
            # === 修复 P2-6: 张飞咆哮 - 出杀无次数限制 ===
            has_unlimited_slash = "pao" in player.skill_state.get("skills", [])
            can_play_slash = has_unlimited_slash or player.slash_count == 0
            
            if can_play_slash:
                slash = next((c for c in player.hand_cards if isinstance(c, BasicCard) and c.subtype == BasicType.SLASH), None)
                if slash:
                    # === 修复 P2-4: 根据身份选择攻击目标 ===
                    target = self._find_attack_target_by_identity(player)
                    if target and self._check_zhige(target):
                        player.hand_cards.remove(slash)
                        self.discard_pile.append(slash)
                        if not has_unlimited_slash:
                            player.slash_count += 1
                        self._log_event("card_played", {
                            "player_id": player.id,
                            "card": slash.to_dict(),
                            "target": target.id,
                        })
                        self._resolve_slash(player, target, slash)
                        played = True
                        self._update_game_board()
                        time.sleep(0.5)
                        continue

            # 3. 尝试装备
            equip = next((c for c in player.hand_cards if isinstance(c, EquipmentCard)), None)
            if equip:
                player.hand_cards.remove(equip)
                old = player.equipped.equip(equip)
                if old:
                    self.discard_pile.append(old)
                self._log_event("card_played", {
                    "player_id": player.id,
                    "card": equip.to_dict(),
                    "action": "equip",
                })
                self.ui.display_system_message(f"{player.name} 装备了{equip.name}")
                played = True
                self._update_game_board()
                time.sleep(0.5)
    
    def _phase_discard(self, player: ThreeKingdomsPlayer) -> None:
        """弃牌阶段"""
        self.phase = Phase.DISCARD
        
        if len(player.hand_cards) <= player.hp:
            return
        
        self.ui.display_system_message(f"=== {player.name} 弃牌阶段 ===")
        self.ui.display_system_message(f"手牌数{len(player.hand_cards)} > 体力值{player.hp}，需要弃牌")
        
        # 简化：随机弃牌
        discard_count = len(player.hand_cards) - player.hp
        discarded = []
        for _ in range(discard_count):
            if player.hand_cards:
                card = random.choice(player.hand_cards)
                player.hand_cards.remove(card)
                self.discard_pile.append(card)
                discarded.append(card.name)
        
        self.ui.display_system_message(f"{player.name} 弃置了：{', '.join(discarded)}")
        self._log_event("phase_discard", {
            "player_id": player.id,
            "discarded_cards": discarded,
        })
    
    def _draw_cards(self, player: ThreeKingdomsPlayer, count: int) -> list[Card]:
        """摸牌"""
        drawn = []
        for _ in range(count):
            if len(self.deck) == 0:
                # 牌堆为空，重置
                if len(self.discard_pile) > 0:
                    self._reset_deck()
                else:
                    break
            
            if len(self.deck) > 0:
                card = self.deck.pop()
                player.hand_cards.append(card)
                drawn.append(card)
        
        if drawn:
            self._log_event("cards_drawn", {
                "player_id": player.id,
                "cards": [c.name for c in drawn],
            })
        
        return drawn
    
    def _reset_deck(self) -> None:
        """重置牌堆（弃牌堆洗入）"""
        self.deck = self.discard_pile.copy()
        random.shuffle(self.deck)
        self.discard_pile = []
        self._log_event("deck_reset", {"card_count": len(self.deck)})
        self.ui.display_system_message("牌堆已重置（弃牌堆洗入）")
    
    def _play_card(self, player: ThreeKingdomsPlayer, card: Card) -> None:
        """出牌"""
        player.hand_cards.remove(card)
        self.discard_pile.append(card)

        if isinstance(card, BasicCard):
            if card.subtype == BasicType.SLASH:
                target = self._find_attack_target(player)
                if target:
                    player.slash_count += 1
                    self._log_event("card_played", {
                        "player_id": player.id,
                        "card": card.to_dict(),
                        "target": target.id,
                    })
                    self._resolve_slash(player, target, card)
            elif card.subtype == BasicType.PEACH:
                if player.hp < player.max_hp:
                    player.hp += 1
                    self.ui.display_system_message(f"{player.name} 使用桃，体力恢复到{player.hp}")
                    self._log_event("card_played", {
                        "player_id": player.id,
                        "card": card.to_dict(),
                        "action": "heal",
                    })
            elif card.subtype == BasicType.WINE:
                # === 修复 P2-5: 酒的效果 ===
                # 标记本回合出杀伤害 +1
                player.skill_state["wine_effect"] = True
                self.ui.display_system_message(f"{player.name} 喝了酒，本回合出杀伤害 +1")
                self._log_event("card_played", {
                    "player_id": player.id,
                    "card": card.to_dict(),
                    "action": "wine",
                })
        elif isinstance(card, EquipmentCard):
            old = player.equipped.equip(card)
            if old:
                self.discard_pile.append(old)
            self.ui.display_system_message(f"{player.name} 装备了{card.name}")
            self._log_event("card_played", {
                "player_id": player.id,
                "card": card.to_dict(),
                "action": "equip",
            })
        elif isinstance(card, TrickCard):
            # === 修复 P1-2: 锦囊牌效果实现 ===
            if not card.is_delayed:
                # 非延时锦囊立即使用
                self._use_trick_card(player, card)
            else:
                # 延时锦囊放入判定区
                player.judged.append(card)
                self.ui.display_system_message(f"{player.name} 使用了{card.name}，放在判定区")
                self._log_event("card_played", {
                    "player_id": player.id,
                    "card": card.to_dict(),
                    "action": "delayed_trick",
                })

        self._update_game_board()
    
    def _resolve_slash(self, source: ThreeKingdomsPlayer, target: ThreeKingdomsPlayer, slash: Card) -> None:
        """结算杀
        修复 P2-5: 支持酒的伤害加成效果
        修复 P2-6: 支持武将技能（空城、无双）
        """
        # === 修复 P2-6: 检查诸葛亮空城 ===
        if not self._check_zhige(target):
            self.ui.display_system_message(f"{target.name} 发动空城，不能成为杀的目标")
            return

        self.ui.display_system_message(f"{source.name} 对{target.name} 出杀")

        # 计算伤害（考虑酒的效果）
        damage = 1
        if source.skill_state.get("wine_effect"):
            damage = 2
            source.skill_state["wine_effect"] = False  # 清除酒效果
            self.ui.display_system_message(f"{source.name} 有酒效果，伤害 +1")

        # === 修复 P2-6: 检查吕布无双技能 ===
        need_two_dodges = False
        if "feng" in source.skill_state.get("skills", []):
            need_two_dodges = True
            self.ui.display_system_message(f"{source.name}({source.general}) 发动无双，需要两张闪")

        # 目标出闪
        dodges = []
        for c in target.hand_cards:
            if isinstance(c, BasicCard) and c.subtype == BasicType.DODGE:
                dodges.append(c)
                if len(dodges) >= (2 if need_two_dodges else 1):
                    break
        
        if len(dodges) >= (2 if need_two_dodges else 1):
            # 目标出闪（可能需要两张）
            for dodge in dodges:
                target.hand_cards.remove(dodge)
                self.discard_pile.append(dodge)
            if need_two_dodges:
                self.ui.display_system_message(f"{target.name} 出了两张闪，躲避了杀")
            else:
                self.ui.display_system_message(f"{target.name} 出闪，躲避了杀")
            self._log_event("card_responded", {
                "player_id": target.id,
                "response_card": "闪",
                "success": True,
            })
        else:
            # 掉血
            if need_two_dodges:
                self.ui.display_system_message(f"{target.name} 没有足够的闪，受到{damage}点伤害")
            else:
                self.ui.display_system_message(f"{target.name} 没有闪，受到{damage}点伤害")
            self._deal_damage(source=source, target=target, damage=damage)
    
    def _deal_damage(self, source: Optional[ThreeKingdomsPlayer], target: ThreeKingdomsPlayer, damage: int) -> None:
        """造成伤害"""
        target.hp -= damage
        self.damage_source = source.id if source else None
        
        self.ui.display_system_message(f"{target.name} 受到{damage}点伤害，当前体力{target.hp}")
        self._log_event("damage_dealt", {
            "source": source.id if source else None,
            "target": target.id,
            "damage": damage,
            "remaining_hp": target.hp,
        })
        
        if target.hp <= 0:
            # 濒死结算
            if self.dying_request_peach:
                self._dying_request(target)
            
            if target.is_alive:
                return
            
            # 死亡
            target.is_alive = False
            self.ui.display_system_message(f"{target.name} 死亡！")
            
            # 公开身份
            if self.identity_reveal_on_death:
                self.ui.display_system_message(f"{target.name} 的身份是：{target.role.value}")
            
            self._log_event("player_died", {
                "player_id": target.id,
                "role": target.role.value,
                "killer": source.id if source else None,
            })
            
            # 结算奖励
            if source and target.role == Role.REBEL:
                # 杀死反贼，摸 3 张牌
                self._draw_cards(source, 3)
                self.ui.display_system_message(f"{source.name} 杀死反贼，摸 3 张牌")
            elif source and target.role == Role.LOYALIST:
                # 杀死忠臣，弃光手牌
                for card in source.hand_cards.copy():
                    source.hand_cards.remove(card)
                    self.discard_pile.append(card)
                self.ui.display_system_message(f"{source.name} 杀死忠臣，弃光手牌")
        
        self._update_game_board()
    
    def _dying_request(self, player: ThreeKingdomsPlayer) -> None:
        """濒死求桃
        修复：传递身份关系信息给 AI，让 AI 根据身份决定是否救
        修复 P2-5: 濒死时可以先使用酒自救
        """
        self.phase = Phase.DYING
        self.ui.display_system_message(f"=== {player.name} 进入濒死状态 ===")
        self._log_event("dying_request", {
            "player_id": player.id,
            "hp": player.hp,
        })

        # === 修复 P2-5: 濒死时先尝试使用酒自救 ===
        wine = next((c for c in player.hand_cards if isinstance(c, BasicCard) and c.subtype == BasicType.WINE), None)
        if wine:
            player.hand_cards.remove(wine)
            self.discard_pile.append(wine)
            player.hp = 1
            self.ui.display_system_message(f"{player.name} 使用酒自救，体力恢复到 1")
            self._log_event("card_responded", {
                "player_id": player.id,
                "response_card": "酒",
                "saved": True,
            })
            return

        # 逆时针询问其他玩家
        current = player.id
        asked_count = 0
        total_players = len([p for p in self.players.values() if p.is_alive])

        while asked_count < total_players:
            current = self._get_next_alive_player(current)
            if not current:
                break

            asked_player = self.players[current]
            asked_count += 1

            # 检查是否有桃
            peach = next((c for c in asked_player.hand_cards if isinstance(c, BasicCard) and c.subtype == BasicType.PEACH), None)
            if peach:
                # === 修复：使用 AI 决策是否救 ===
                # 构建情境信息，包含身份关系
                context = {
                    "dying_player_id": player.id,
                    "dying_player_role": player.role.value,  # 濒死玩家的身份
                    "hand_cards": [c.to_dict() for c in asked_player.hand_cards],
                    "alive_players": [p.id for p in self.players.values() if p.is_alive],
                }
                
                # 调用 AI 决策
                should_save = asked_player.agent.decide_dying_peach(context) if asked_player.agent else False
                
                if should_save:
                    # 出桃
                    asked_player.hand_cards.remove(peach)
                    self.discard_pile.append(peach)
                    player.hp = 1
                    self.ui.display_system_message(f"{asked_player.name} 对{player.name} 使用桃")
                    self._log_event("card_responded", {
                        "player_id": asked_player.id,
                        "response_card": "桃",
                        "target": player.id,
                        "saved": True,
                    })
                    return
                else:
                    print(f"[DEBUG] {asked_player.name} 有桃但决定不救{player.name}")

        # 无人救
        self.ui.display_system_message(f"{player.name} 无人救援，死亡")
        player.is_alive = False
    
    def _find_attack_target(self, player: ThreeKingdomsPlayer) -> Optional[ThreeKingdomsPlayer]:
        """寻找攻击目标（简化版：随机选择）"""
        for target in self.players.values():
            if target.is_alive and target.id != player.id and player.can_attack(target):
                return target
        return None

    def _find_attack_target_by_identity(self, player: ThreeKingdomsPlayer) -> Optional[ThreeKingdomsPlayer]:
        """
        根据身份选择攻击目标
        修复 P2-4: 增加身份判断和战术决策
        
        身份逻辑：
        - 主公：攻击可疑的反贼
        - 忠臣：攻击反贼和内奸
        - 反贼：攻击主公和忠臣
        - 内奸：先消灭其他人，最后对付主公
        """
        # 获取所有可能的目标
        potential_targets = []
        
        for target in self.players.values():
            if not target.is_alive or target.id == player.id:
                continue
            if not player.can_attack(target):
                continue
            potential_targets.append(target)
        
        if not potential_targets:
            return None
        
        # === 根据身份选择目标 ===
        if player.role == Role.LORD:
            # 主公：优先攻击反贼（如果有暴露的）
            # 简化：随机选择
            print(f"[DEBUG] {player.name}(主公) 选择攻击目标")
            return random.choice(potential_targets)
        
        elif player.role == Role.LOYALIST:
            # 忠臣：优先攻击反贼和内奸
            # 简化：随机选择非主公目标
            non_lord_targets = [t for t in potential_targets if t.role != Role.LORD]
            if non_lord_targets:
                print(f"[DEBUG] {player.name}(忠臣) 攻击非主公目标")
                return random.choice(non_lord_targets)
            return random.choice(potential_targets)
        
        elif player.role == Role.REBEL:
            # 反贼：优先攻击主公
            lord = next((t for t in potential_targets if t.role == Role.LORD), None)
            if lord:
                print(f"[DEBUG] {player.name}(反贼) 攻击主公")
                return lord
            # 其次攻击忠臣
            loyalist = next((t for t in potential_targets if t.role == Role.LOYALIST), None)
            if loyalist:
                print(f"[DEBUG] {player.name}(反贼) 攻击忠臣")
                return loyalist
            return random.choice(potential_targets)
        
        elif player.role == Role.RENEGADE:
            # 内奸：先消灭其他人，最后对付主公
            # 简化：随机选择非主公目标
            non_lord_targets = [t for t in potential_targets if t.role != Role.LORD]
            if non_lord_targets:
                print(f"[DEBUG] {player.name}(内奸) 攻击非主公目标")
                return random.choice(non_lord_targets)
            # 只剩主公时攻击主公
            print(f"[DEBUG] {player.name}(内奸) 只能攻击主公")
            return random.choice(potential_targets)
        
        return random.choice(potential_targets)

    def _find_usable_trick(self, player: ThreeKingdomsPlayer) -> Optional[TrickCard]:
        """寻找可以使用的锦囊牌"""
        for card in player.hand_cards:
            if isinstance(card, TrickCard) and not card.is_delayed:
                # 检查是否有合法目标
                if self._has_valid_trick_target(player, card):
                    return card
        return None

    def _has_valid_trick_target(self, player: ThreeKingdomsPlayer, card: TrickCard) -> bool:
        """检查锦囊是否有合法目标"""
        if card.subtype == TrickType.PEACH_GARDEN:
            # 桃园结义：有人体力不满
            return any(p.is_alive and p.hp < p.max_hp for p in self.players.values())
        elif card.subtype == TrickType.BARBARIAN:
            # 南蛮入侵：有其他存活玩家
            return len([p for p in self.players.values() if p.is_alive and p.id != player.id]) > 0
        elif card.subtype == TrickType.ARROW_VOLLEY:
            # 万箭齐发：有其他存活玩家
            return len([p for p in self.players.values() if p.is_alive and p.id != player.id]) > 0
        elif card.subtype in [TrickType.RIVER_DENY, TrickType.HAND_STEAL, TrickType.DUEL]:
            # 单体锦囊：有其他存活玩家
            return len([p for p in self.players.values() if p.is_alive and p.id != player.id]) > 0
        return True

    def _use_trick_card(self, source: ThreeKingdomsPlayer, card: TrickCard) -> None:
        """
        使用锦囊牌
        修复 P1-2: 实现基本锦囊牌效果
        """
        self.ui.display_system_message(f"{source.name} 使用了{card.name}")
        self._log_event("trick_used", {
            "player_id": source.id,
            "card": card.name,
            "subtype": card.subtype.value,
        })

        if card.subtype == TrickType.RIVER_DENY:
            # 过河拆桥：拆除目标一张牌
            self._trick_river_deny(source, card)
        elif card.subtype == TrickType.HAND_STEAL:
            # 顺手牵羊：获得目标一张牌
            self._trick_hand_steal(source, card)
        elif card.subtype == TrickType.PEACH_GARDEN:
            # 桃园结义：所有角色回复 1 点体力
            self._trick_peach_garden(source, card)
        elif card.subtype == TrickType.BARBARIAN:
            # 南蛮入侵：所有其他角色出杀
            self._trick_barbarian(source, card)
        elif card.subtype == TrickType.ARROW_VOLLEY:
            # 万箭齐发：所有其他角色出闪
            self._trick_arrow_volley(source, card)
        elif card.subtype == TrickType.DUEL:
            # 决斗：与目标决斗
            self._trick_duel(source, card)
        elif card.subtype == TrickType.NULLIFICATION:
            # 无懈可击：抵消锦囊效果（简化：暂不实现）
            self.ui.display_system_message(f"{source.name} 使用了无懈可击（简化版暂不生效）")
        else:
            self.ui.display_system_message(f"{card.name} 效果未实现")

    def _trick_river_deny(self, source: ThreeKingdomsPlayer, card: TrickCard) -> None:
        """过河拆桥：拆除目标一张牌"""
        # 选择目标（简化：随机选择有牌的玩家）
        targets = [p for p in self.players.values() if p.is_alive and p.id != source.id and len(p.hand_cards) > 0]
        if not targets:
            self.ui.display_system_message("没有可拆除的目标")
            return
        
        target = random.choice(targets)
        discarded = random.choice(target.hand_cards)
        target.hand_cards.remove(discarded)
        self.discard_pile.append(discarded)
        self.ui.display_system_message(f"{source.name} 对{target.name} 使用过河拆桥，拆除了{discarded.name}")
        self._log_event("trick_result", {
            "card": "过河拆桥",
            "target": target.id,
            "discarded": discarded.name,
        })

    def _trick_hand_steal(self, source: ThreeKingdomsPlayer, card: TrickCard) -> None:
        """顺手牵羊：获得目标一张牌"""
        targets = [p for p in self.players.values() if p.is_alive and p.id != source.id and len(p.hand_cards) > 0]
        if not targets:
            self.ui.display_system_message("没有可偷取的目标")
            return
        
        target = random.choice(targets)
        stolen = random.choice(target.hand_cards)
        target.hand_cards.remove(stolen)
        source.hand_cards.append(stolen)
        self.ui.display_system_message(f"{source.name} 对{target.name} 使用顺手牵羊，获得了{stolen.name}")
        self._log_event("trick_result", {
            "card": "顺手牵羊",
            "target": target.id,
            "stolen": stolen.name,
        })

    def _trick_peach_garden(self, source: ThreeKingdomsPlayer, card: TrickCard) -> None:
        """桃园结义：所有角色回复 1 点体力"""
        healed_count = 0
        for player in self.players.values():
            if player.is_alive and player.hp < player.max_hp:
                player.hp += 1
                healed_count += 1
        self.ui.display_system_message(f"桃园结义生效，{healed_count}名角色回复了 1 点体力")
        self._log_event("trick_result", {
            "card": "桃园结义",
            "healed_count": healed_count,
        })

    def _trick_barbarian(self, source: ThreeKingdomsPlayer, card: TrickCard) -> None:
        """南蛮入侵：所有其他角色出杀"""
        self.ui.display_system_message("南蛮入侵：所有其他角色需要出杀")
        for player in self.players.values():
            if player.is_alive and player.id != source.id:
                slash = next((c for c in player.hand_cards if isinstance(c, BasicCard) and c.subtype == BasicType.SLASH), None)
                if slash:
                    player.hand_cards.remove(slash)
                    self.discard_pile.append(slash)
                    self.ui.display_system_message(f"{player.name} 出了杀")
                else:
                    self._deal_damage(source=source, target=player, damage=1)
                    self.ui.display_system_message(f"{player.name} 没有杀，受到 1 点伤害")
        self._log_event("trick_result", {"card": "南蛮入侵"})

    def _trick_arrow_volley(self, source: ThreeKingdomsPlayer, card: TrickCard) -> None:
        """万箭齐发：所有其他角色出闪"""
        self.ui.display_system_message("万箭齐发：所有其他角色需要出闪")
        for player in self.players.values():
            if player.is_alive and player.id != source.id:
                dodge = next((c for c in player.hand_cards if isinstance(c, BasicCard) and c.subtype == BasicType.DODGE), None)
                if dodge:
                    player.hand_cards.remove(dodge)
                    self.discard_pile.append(dodge)
                    self.ui.display_system_message(f"{player.name} 出了闪")
                else:
                    self._deal_damage(source=source, target=player, damage=1)
                    self.ui.display_system_message(f"{player.name} 没有闪，受到 1 点伤害")
        self._log_event("trick_result", {"card": "万箭齐发"})

    def _trick_duel(self, source: ThreeKingdomsPlayer, card: TrickCard) -> None:
        """决斗：与目标决斗"""
        targets = [p for p in self.players.values() if p.is_alive and p.id != source.id]
        if not targets:
            return
        
        target = random.choice(targets)
        self.ui.display_system_message(f"{source.name} 对{target.name} 使用决斗")

        # 简化决斗：双方轮流出杀，先不出杀者掉血
        source_slash = next((c for c in source.hand_cards if isinstance(c, BasicCard) and c.subtype == BasicType.SLASH), None)
        target_slash = next((c for c in target.hand_cards if isinstance(c, BasicCard) and c.subtype == BasicType.SLASH), None)

        if source_slash and target_slash:
            # 都有杀，各打五十大板（简化）
            source.hand_cards.remove(source_slash)
            target.hand_cards.remove(target_slash)
            self.discard_pile.append(source_slash)
            self.discard_pile.append(target_slash)
            self.ui.display_system_message("双方都出了杀，决斗平局")
        elif not source_slash and target_slash:
            # 源没有杀，源掉血
            target.hand_cards.remove(target_slash)
            self.discard_pile.append(target_slash)
            self._deal_damage(source=target, target=source, damage=1)
            self.ui.display_system_message(f"{source.name} 没有杀，受到 1 点伤害")
        else:
            # 目标没有杀，目标掉血（源出杀）
            if source_slash:
                source.hand_cards.remove(source_slash)
                self.discard_pile.append(source_slash)
            self._deal_damage(source=source, target=target, damage=1)
            self.ui.display_system_message(f"{target.name} 没有杀，受到 1 点伤害")

        self._log_event("trick_result", {
            "card": "决斗",
            "target": target.id,
        })
    
    def _get_next_alive_player(self, current_id: int) -> Optional[int]:
        """获取下一个存活玩家"""
        next_id = current_id % len(self.players) + 1
        checked = 0
        while checked < len(self.players):
            if self.players[next_id].is_alive:
                return next_id
            next_id = next_id % len(self.players) + 1
            checked += 1
        return None
    
    def _next_player(self) -> None:
        """切换到下一个玩家"""
        next_id = self._get_next_alive_player(self.current_player_id)
        if next_id:
            self.current_player_id = next_id
    
    def _check_game_over(self) -> bool:
        """
        检查游戏是否结束

        Returns:
            True 表示游戏结束，False 表示继续
        """
        lord = next((p for p in self.players.values() if p.role == Role.LORD), None)
        if not lord or not lord.is_alive:
            # 主公死亡，反贼胜
            return True

        rebels = [p for p in self.players.values() if p.role == Role.REBEL and p.is_alive]
        renegades = [p for p in self.players.values() if p.role == Role.RENEGADE and p.is_alive]

        if not rebels and not renegades:
            # 所有反贼和内奸死亡，主忠胜
            return True

        return False

    def _get_winner_message(self) -> str:
        """获取获胜方消息"""
        lord = next((p for p in self.players.values() if p.role == Role.LORD), None)
        if not lord or not lord.is_alive:
            return "主公死亡，反贼获胜！"

        rebels = [p for p in self.players.values() if p.role == Role.REBEL and p.is_alive]
        renegades = [p for p in self.players.values() if p.role == Role.RENEGADE and p.is_alive]

        if not rebels and not renegades:
            return "所有反贼和内奸死亡，主公阵营获胜！"

        return ""
    
    def _end_game(self) -> None:
        """结束游戏"""
        self.ui.notify_game_event("game_over", {})
        self._log_event("game_over", {})

        self.ui.display_system_message("=== 游戏结束 ===")

        # 显示获胜方
        winner_msg = self._get_winner_message()
        if winner_msg:
            self.ui.display_system_message(winner_msg)

        # 显示所有玩家身份
        self.ui.display_system_message("=== 玩家身份 ===")
        for player in self.players.values():
            role_str = player.role.value
            status = "存活" if player.is_alive else "死亡"
            self.ui.display_system_message(f"{player.name}: {player.general} - {role_str} ({status})")

        self.ui.display_system_message(f"日志已保存至：{self.log_file}")
    
    def _update_game_board(self) -> None:
        """更新全局看板"""
        # 简化实现：显示所有玩家状态
        board_text = f"\n{'='*60}\n"
        board_text += f"当前回合：{self.players[self.current_player_id].name if self.current_player_id else 'N/A'}\n"
        board_text += f"牌堆：{len(self.deck)}张 | 弃牌堆：{len(self.discard_pile)}张\n"
        board_text += f"{'='*60}\n"
        
        for player in self.players.values():
            if player.is_alive:
                hand_str = ", ".join([c.name for c in player.hand_cards])  # 上帝视角显示所有手牌
                board_text += f"\n[{player.id}号 - {player.general} - {player.role.value}]\n"
                board_text += f"  HP: {'●'*player.hp}{'○'*(player.max_hp-player.hp)} ({player.hp}/{player.max_hp})\n"
                board_text += f"  手牌：{len(player.hand_cards)}张 [{hand_str}]\n"
                board_text += f"  装备：{player.equipped.to_dict()}\n"
                if player.id == self.current_player_id:
                    board_text += f"  >>> 当前回合 <<<\n"
        
        board_text += f"\n{'='*60}\n"
        
        # 显示 AI 思考（简化）
        if self.current_player_id:
            current = self.players[self.current_player_id]
            if not current.is_human:
                board_text += f"\n[AI 思考 - {current.name}]\n"
                if current.slash_count == 0:
                    slash = next((c for c in current.hand_cards if isinstance(c, BasicCard) and c.subtype == BasicType.SLASH), None)
                    if slash:
                        target = self._find_attack_target(current)
                        if target:
                            board_text += f"  '有杀，准备攻击{target.name}'\n"
                board_text += f"\n{'='*60}\n"
        
        print(board_text)

    # === 修复 P2-6: 武将技能触发方法 ===
    def _trigger_end_turn_skill(self, player: ThreeKingdomsPlayer) -> None:
        """回合结束时触发技能"""
        skills = player.skill_state.get("skills", [])
        
        # 貂蝉 - 闭月：回合结束时摸一张牌
        if "bi" in skills:
            self._skill_diaochan_bi(player)
    
    def _skill_diaochan_bi(self, player: ThreeKingdomsPlayer) -> None:
        """貂蝉闭月技能"""
        self._draw_cards(player, 1)
        self.ui.display_system_message(f"{player.name}({player.general}) 触发闭月，摸一张牌")
        self._log_event("skill_triggered", {
            "player_id": player.id,
            "general": player.general,
            "skill": "闭月",
        })

    def _skill_sunquan_zhi(self, player: ThreeKingdomsPlayer, cards_to_discard: list) -> None:
        """
        孙权制衡技能
        弃置手牌，然后摸等量的牌
        """
        discard_count = len(cards_to_discard)
        if discard_count == 0:
            return
        
        # 弃牌
        for card in cards_to_discard:
            if card in player.hand_cards:
                player.hand_cards.remove(card)
                self.discard_pile.append(card)
        
        self.ui.display_system_message(f"{player.name}({player.general}) 发动制衡，弃置{discard_count}张牌")
        
        # 摸等量的牌
        self._draw_cards(player, discard_count)
        self.ui.display_system_message(f"{player.name} 摸了{discard_count}张牌")
        
        self._log_event("skill_triggered", {
            "player_id": player.id,
            "general": player.general,
            "skill": "制衡",
            "discarded": [c.name for c in cards_to_discard],
        })

    def _skill_huanggai_ku(self, player: ThreeKingdomsPlayer) -> None:
        """
        黄盖苦肉技能
        自减 1 点体力，然后摸 2 张牌
        """
        if player.hp <= 1:
            self.ui.display_system_message(f"{player.name}({player.general}) 体力不足，无法发动苦肉")
            return
        
        # 自减体力
        player.hp -= 1
        self.ui.display_system_message(f"{player.name}({player.general}) 发动苦肉，自减 1 点体力，当前体力{player.hp}")
        
        # 摸 2 张牌
        self._draw_cards(player, 2)
        self.ui.display_system_message(f"{player.name} 摸了 2 张牌")
        
        self._log_event("skill_triggered", {
            "player_id": player.id,
            "general": player.general,
            "skill": "苦肉",
            "hp_after": player.hp,
        })

    def _check_zhige(self, target: ThreeKingdomsPlayer) -> bool:
        """
        检查是否可以攻击目标（检查技能影响）
        Returns: True 表示可以攻击，False 表示不能攻击
        """
        # 检查诸葛亮空城
        if "kong" in target.skill_state.get("skills", []):
            if len(target.hand_cards) == 0:
                return False
        return True
