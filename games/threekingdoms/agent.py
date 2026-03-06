"""三国杀 AI 代理"""
import json
from typing import Optional
from ai.llm_client import LLMClient
from ai.personality import Personality


class ThreeKingdomsAgent:
    """三国杀 AI 代理"""
    
    def __init__(self, player_id: int, general: str, role: str,
                 personality: Personality, llm_client: LLMClient):
        """
        Args:
            player_id: 玩家 ID
            general: 武将名
            role: 身份
            personality: 人格
            llm_client: LLM 客户端
        """
        self.player_id = player_id
        self.general = general
        self.role = role  # AI 只知道自己的身份
        self.personality = personality
        self.llm = llm_client
        self.memory: list[dict] = []  # 记忆
        self.trust_list: list[int] = []  # 信任列表
        self.suspect_list: list[int] = []  # 怀疑列表
        self.thought_history: list[dict] = []  # 思考历史
    
    def add_memory(self, event: dict) -> None:
        """添加记忆"""
        self.memory.append(event)
        if len(self.memory) > 200:
            self.memory = self.memory[-200:]
    
    def add_trust(self, player_id: int) -> None:
        """添加信任玩家"""
        if player_id != self.player_id and player_id not in self.trust_list:
            if player_id in self.suspect_list:
                self.suspect_list.remove(player_id)
            self.trust_list.append(player_id)
    
    def add_suspect(self, player_id: int) -> None:
        """添加怀疑玩家"""
        if player_id != self.player_id and player_id not in self.suspect_list:
            if player_id in self.trust_list:
                self.trust_list.remove(player_id)
            self.suspect_list.append(player_id)
    
    def _build_system_prompt(self) -> str:
        """构建系统提示"""
        role_descriptions = {
            "主公": "你是主公，需要消灭所有反贼和内奸。忠臣会保护你。",
            "忠臣": "你是忠臣，需要保护主公，消灭所有反贼和内奸。",
            "反贼": "你是反贼，需要消灭主公。可以配合其他反贼。",
            "内奸": "你是内奸，需要先消灭其他人，最后单挑赢主公。",
        }
        
        role_desc = role_descriptions.get(self.role, "")
        
        return f"""{self.personality.to_prompt()}

【游戏背景】
你正在参与一场三国杀游戏。
你的武将是：{self.general}
你的身份是：{self.role}
{role_desc}

【重要规则】
1. 不要暴露你的身份（除非死亡）
2. 根据局势做出合理决策
3. 发言要符合你的性格特点
"""
    
    def decide_play(self, context: dict) -> dict:
        """
        决定出牌
        
        Args:
            context: 当前情境
        
        Returns:
            出牌决策
        """
        hand_cards = context.get("hand_cards", [])
        hp = context.get("hp", 4)
        max_hp = context.get("max_hp", 4)
        alive_players = context.get("alive_players", [])
        current_player = context.get("current_player")
        
        # 构建提示
        prompt = f"""你是{self.general}（{self.role}），当前出牌阶段。

手牌：{', '.join([c['name'] for c in hand_cards])}
体力：{hp}/{max_hp}
存活玩家：{alive_players}
信任：{self.trust_list}
怀疑：{self.suspect_list}

请决定出什么牌，返回 JSON 格式：
{{"action": "play/discard/pass", "card": "牌名", "target": 目标 ID 或 null}}

决策要点：
1. 有杀可以攻击敌人
2. 有装备可以装备
3. 血量低可以使用桃
4. 不要暴露身份
"""
        
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt}
        ]
        
        content, _ = self.llm.chat(messages, max_tokens=100)
        
        # 记录思考过程
        thought = {
            "player_id": self.player_id,
            "phase": "play",
            "situation": {
                "hand_cards": len(hand_cards),
                "hp": hp,
            },
            "reasoning": content[:200] if len(content) > 200 else content,
            "final_decision": content[:50],
        }
        self.thought_history.append(thought)
        
        # 解析响应
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except:
            pass
        
        return {"action": "pass"}
    
    def decide_respond(self, context: dict) -> dict:
        """
        决定响应（如出闪、桃别人）
        
        Args:
            context: 当前情境
        
        Returns:
            响应决策
        """
        card_type = context.get("card_type")  # 杀、桃等
        source = context.get("source")  # 来源玩家
        target = context.get("target")  # 目标玩家（可能是自己）
        hand_cards = context.get("hand_cards", [])
        
        prompt = f"""你是{self.general}（{self.role}），需要响应。

事件：{source}对{target}使用了{card_type}
手牌：{', '.join([c['name'] for c in hand_cards])}
信任：{self.trust_list}
怀疑：{self.suspect_list}

请决定是否响应，返回 JSON 格式：
{{"respond": true/false, "card": "牌名" 或 null}}
"""
        
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt}
        ]
        
        content, _ = self.llm.chat(messages, max_tokens=50)
        
        # 记录思考
        thought = {
            "player_id": self.player_id,
            "phase": "respond",
            "situation": {
                "card_type": card_type,
                "source": source,
                "target": target,
            },
            "reasoning": content[:100],
            "final_decision": content[:30],
        }
        self.thought_history.append(thought)
        
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except:
            pass
        
        return {"respond": False}
    
    def decide_dying_peach(self, context: dict) -> bool:
        """
        决定是否桃濒死玩家
        修复：根据身份关系决定 AI 是否使用桃
        - 反贼不应该救主公
        - 忠臣应该救主公
        - 内奸根据局势决定
        - 队友应该互相救

        Args:
            context: 当前情境

        Returns:
            是否使用桃
        """
        dying_player_id = context.get("dying_player_id")
        dying_player_role = context.get("dying_player_role")  # 濒死玩家的身份（AI 视角可能不知道）
        hand_cards = context.get("hand_cards", [])
        alive_players = context.get("alive_players", [])
        
        # 检查是否有桃
        has_peach = any(c.get("name") == "桃" for c in hand_cards)
        if not has_peach:
            return False

        # === 修复核心逻辑：根据身份关系决定是否救 ===
        # 1. 反贼不应该救主公
        if self.role == "反贼" and dying_player_role == "主公":
            print(f"[DEBUG] {self.player_id}号反贼拒绝救主公")
            return False
        
        # 2. 忠臣应该救主公
        if self.role == "忠臣" and dying_player_role == "主公":
            print(f"[DEBUG] {self.player_id}号忠臣决定救主公")
            return True
        
        # 3. 主公应该救忠臣（如果判断是队友）
        if self.role == "主公" and dying_player_role == "忠臣":
            print(f"[DEBUG] {self.player_id}号主公决定救忠臣")
            return True
        
        # 4. 反贼应该救其他反贼（队友）
        if self.role == "反贼" and dying_player_role == "反贼":
            print(f"[DEBUG] {self.player_id}号反贼决定救队友")
            return True
        
        # 5. 忠臣应该救其他忠臣（如果有）
        if self.role == "忠臣" and dying_player_role == "忠臣":
            print(f"[DEBUG] {self.player_id}号忠臣决定救队友")
            return True
        
        # 6. 内奸根据局势决定（优先保自己，局势不明时可救）
        if self.role == "内奸":
            # 如果濒死的是主公，且场上还有其他人，可以考虑救（维持平衡）
            if dying_player_role == "主公":
                print(f"[DEBUG] {self.player_id}号内奸决定救主公（维持平衡）")
                return True
            # 其他情况根据信任列表决定
            if dying_player_id in self.trust_list:
                print(f"[DEBUG] {self.player_id}号内奸决定救信任的玩家")
                return True
            print(f"[DEBUG] {self.player_id}号内奸决定不救")
            return False
        
        # 7. 其他情况：根据信任列表决定
        if dying_player_id in self.trust_list:
            print(f"[DEBUG] {self.player_id}号决定救信任的玩家")
            return True
        
        # 默认不救（保存桃子）
        print(f"[DEBUG] {self.player_id}号决定不救（默认）")
        return False
    
    def get_thought_history(self, limit: int = 10) -> list[dict]:
        """获取思考历史"""
        return self.thought_history[-limit:]
