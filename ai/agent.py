"""AI 代理 - 增强版"""
import json
from typing import Optional
from .llm_client import LLMClient
from .personality import Personality
from core.state import Player, Role, Phase


class AIAgent:
    """AI 玩家代理 - 增强版"""
    
    def __init__(self, player: Player, personality: Personality, llm_client: LLMClient):
        self.player = player
        self.personality = personality
        self.llm = llm_client
        self.memory: list[dict] = []  # 记忆：发言、事件等
        self.hidden_task: Optional[str] = None  # 隐藏任务
        self.trust_list: list[int] = []  # 信任的玩家列表
        self.suspect_list: list[int] = []  # 怀疑的玩家列表
        self._generate_hidden_task()
    
    def _generate_hidden_task(self) -> None:
        """生成隐藏任务（增加游戏趣味性）"""
        import random
        tasks = [
            "全程咬定某个随机玩家是狼人",
            "假装自己是预言家",
            "尽量保持低调，不引人注意",
            "积极带节奏，引导大家投票",
            "总是质疑第一个发言的人",
            "尽量保护某个随机玩家",
        ]
        self.hidden_task = random.choice(tasks)
    
    def add_memory(self, event: dict) -> None:
        """添加记忆"""
        self.memory.append(event)
        # 限制记忆数量，保留最近的 100 条
        if len(self.memory) > 100:
            self.memory = self.memory[-100:]
    
    def add_trust(self, player_id: int) -> None:
        """添加信任玩家"""
        if player_id != self.player.id:
            # 从怀疑列表移除
            if player_id in self.suspect_list:
                self.suspect_list.remove(player_id)
            # 添加到信任列表（如果不在）
            if player_id not in self.trust_list:
                self.trust_list.append(player_id)

    def add_suspect(self, player_id: int) -> None:
        """添加怀疑玩家"""
        if player_id != self.player.id:
            # 从信任列表移除
            if player_id in self.trust_list:
                self.trust_list.remove(player_id)
            # 添加到怀疑列表（如果不在）
            if player_id not in self.suspect_list:
                self.suspect_list.append(player_id)
    
    def analyze_speech(self, speech: str, speaker_id: int) -> None:
        """
        分析其他玩家的发言，更新信任/怀疑列表
        
        Args:
            speech: 发言内容
            speaker_id: 发言玩家 ID
        """
        if speaker_id == self.player.id:
            return  # 不分析自己的发言
        
        # 简单规则分析（后续可以用 LLM 做更复杂的分析）
        # 匹配多种格式： "1 号", "1 号玩家", "玩家 1", "一号"
        my_id_patterns = [
            f"{self.player.id}号",
            f"{self.player.id} 号",
            f"{self.player.id}号玩家",
            f"玩家{self.player.id}",
        ]
        mentioned_me = any(pattern in speech for pattern in my_id_patterns)
        
        # 如果发言中提到怀疑我，增加怀疑
        if mentioned_me and ("怀疑" in speech or "狼" in speech or "踩" in speech or "查杀" in speech):
            self.add_suspect(speaker_id)
        
        # 如果发言中表示信任我，增加信任
        if mentioned_me and ("信任" in speech or "好人" in speech or "金水" in speech or "保" in speech or "站边" in speech):
            self.add_trust(speaker_id)
        
        # 如果发言很激进且无理由踩人，可能是狼
        if "必须" in speech and "出" in speech and len(speech) < 30:
            self.add_suspect(speaker_id)
        
        # 如果发言分析详细且逻辑清晰，暂时信任
        if len(speech) > 80 and ("分析" in speech or "逻辑" in speech):
            self.add_trust(speaker_id)
    
    def _build_system_prompt(self, include_role_hint: bool = False) -> str:
        """构建系统提示"""
        role_descriptions = {
            Role.WEREWOLF: """🐺 你是狼人！你的目标：
1. 隐藏身份，假装好人
2. 夜晚可以袭击村民
3. 白天要混淆视听，误导好人投票
4. 如果有其他狼人，你们是队友，但要装作不认识""",
            Role.VILLAGER: """👨‍🌾 你是村民！你的目标：
1. 没有特殊能力，但要积极参与推理
2. 找出狼人，保护好人
3. 仔细分析每个人的发言，找出矛盾点""",
            Role.SEER: """🔮 你是预言家！你的目标：
1. 每晚可以查验一个人的身份
2. 适当时机跳身份报查验，帮助好人
3. 注意保护自己，避免被狼人刀""",
            Role.WITCH: """🧪 你是女巫！你的目标：
1. 有一瓶解药（可救人）和一瓶毒药（可毒死人）
2. 首夜建议自救
3. 适当时机可以跳身份""",
            Role.HUNTER: """🔫 你是猎人！你的目标：
1. 死亡时可以带走一个人
2. 可以适当强势，威慑狼人
3. 死后发动技能前可以留遗言""",
        }
        
        role_desc = role_descriptions.get(self.player.role, "你是普通玩家。")
        
        personality_prompt = self.personality.to_prompt()
        
        # 添加隐藏任务提示（不直接说，而是暗示）
        hidden_task_hint = f"\n💡 你内心有个想法：{self.hidden_task}" if self.hidden_task else ""
        
        return f"""{personality_prompt}
{hidden_task_hint}

【游戏背景】
你正在参与一场狼人杀游戏，共有 9 名玩家。
你的角色是：{self.player.role.value if self.player.role else '未知'}
{role_desc}

【重要规则】
1. 发言要符合你的性格和角色
2. 如果你是狼人，绝对不能暴露身份
3. 根据已知信息做出合理推理
4. 可以质疑其他玩家，也可以为自己辩解
5. 发言要有实质性内容，不要说空话
"""
    
    def speak(self, context: dict, round_num: int = 1) -> tuple[str, str]:
        """
        生成发言
        
        Args:
            context: 当前情境信息
            round_num: 第几轮发言
        
        Returns:
            (发言内容，内心独白)
        """
        # 提取关键信息
        day = context.get("day_number", 1)
        night_deaths = context.get("night_deaths", [])
        seer_result = context.get("seer_result", None)
        is_seer = self.player.role == Role.SEER
        is_wolf = self.player.role == Role.WEREWOLF
        previous_speeches = context.get("previous_speeches", [])
        alive_players = context.get("alive_players", [])
        
        # 构建发言历史
        speech_history = ""
        if previous_speeches:
            speech_history = "\n".join([
                f"  {s['speaker']}({s['player_id']}号): {s['content']}"
                for s in previous_speeches[-8:]  # 显示最近 8 条发言
            ])
        
        # 构建信任/怀疑列表提示
        trust_hint = ""
        if self.trust_list:
            trust_hint = f"你比较信任的玩家：{', '.join([f'{p}号' for p in self.trust_list])}。"
        if self.suspect_list:
            trust_hint += f"你怀疑的玩家：{', '.join([f'{p}号' for p in self.suspect_list])}。"
        
        # 构建情境提示
        user_prompt = f"""【第{day}天白天 第{round_num}轮发言】

昨晚情况：{', '.join([f'{p}号死亡' for p in night_deaths]) if night_deaths else '无人死亡'}
你是{self.player.role.value if self.player.role else '玩家'}{'（预言家）' if is_seer else ''}
存活玩家：{', '.join([f'{p}号' for p in alive_players])}

{trust_hint}

其他玩家发言：
{speech_history if speech_history else '（你是第一个发言）'}

【发言要求】
1. 必须分析至少一个具体玩家（支持或质疑）
2. 如果有信息（如预言家查验），要适当透露
3. 发言要有立场，不要模棱两可
4. 符合你的性格特点
5. 长度控制在{self.personality.min_length}-{self.personality.max_length}字
"""
        
        system_prompt = self._build_system_prompt()
        
        speech, inner_thought = self.llm.generate_with_inner_thought(
            system_prompt, 
            user_prompt,
            max_length=self.personality.max_length
        )
        
        # 添加自己的发言到记忆
        self.add_memory({
            "type": "speech",
            "player_id": self.player.id,
            "content": speech,
            "inner_thought": inner_thought,
            "day": day,
            "round": round_num,
        })
        
        return speech, inner_thought
    
    def decide_night_action(self, context: dict) -> dict:
        """决定夜晚行动"""
        alive_players = context.get("alive_players", [])
        wolf_teammates = context.get("wolf_teammates", [])  # 狼人队友
        
        if self.player.role == Role.WEREWOLF:
            # 狼人行动 - 可以和队友商量
            if wolf_teammates:
                prompt = f"""你是狼人，你的队友是{wolf_teammates}号。
今晚要袭击一个玩家，可选择的 target：{alive_players}
请返回 JSON 格式：{{"target": 玩家编号}}"""
            else:
                prompt = f"""你是狼人，请选择今晚要袭击的玩家编号。
可选择的玩家：{alive_players}
请返回 JSON 格式：{{"target": 玩家编号}}"""
        elif self.player.role == Role.SEER:
            prompt = f"""你是预言家，请选择今晚要查验的玩家编号。
可选择的玩家：{alive_players}
请返回 JSON 格式：{{"target": 玩家编号}}"""
        elif self.player.role == Role.WITCH:
            dead_player = context.get("dead_player", None)
            prompt = f"""你是女巫，今晚有人死亡：{dead_player}号
你可以使用解药救人，或使用毒药毒人。
可选择的玩家：{alive_players}
请返回 JSON 格式：{{"action": "heal/poison/none", "target": 玩家编号}}"""
        else:
            return {}
        
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt}
        ]
        
        content, _ = self.llm.chat(messages, max_tokens=50)
        
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except:
            pass
        
        return {}
    
    def vote(self, context: dict) -> Optional[int]:
        """投票决定放逐谁"""
        alive_players = context.get("alive_players", [])
        previous_speeches = context.get("previous_speeches", [])
        
        speech_history = "\n".join([
            f"  {s['speaker']}({s['player_id']}号): {s['content']}"
            for s in previous_speeches[-15:]
        ])
        
        suspect_hint = ""
        if self.suspect_list:
            suspect_hint = f"你怀疑的玩家：{', '.join([f'{p}号' for p in self.suspect_list])}。"
        
        prompt = f"""你是{self.player.role.value if self.player.role else '玩家'}，请投票决定放逐谁。

{self._format_vote_context(speech_history)}

{suspect_hint}

可投票的玩家：{alive_players}
你可以选择弃票（返回 null）

请返回 JSON 格式：{{"vote": 玩家编号}} 或 {{"vote": null}}"""
        
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt}
        ]
        
        content, _ = self.llm.chat(messages, max_tokens=50)
        
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(content[start:end])
                vote = result.get("vote")
                if vote is not None and vote in alive_players:
                    return vote
        except:
            pass
        
        return None  # 弃权
    
    def _format_vote_context(self, speech_history: str) -> str:
        """格式化投票上下文"""
        return f"今天大家的发言：\n{speech_history}"
    
    def make_last_words(self, context: dict) -> str:
        """发表遗言"""
        alive_players = context.get("alive_players", [])
        previous_speeches = context.get("previous_speeches", [])
        
        speech_history = "\n".join([
            f"  {s['speaker']}: {s['content']}"
            for s in previous_speeches[-5:]
        ])
        
        prompt = f"""你即将死亡，请发表遗言。

存活玩家：{', '.join([f'{p}号' for p in alive_players])}
之前的发言：
{speech_history}

遗言要求：
1. 可以透露你的身份（如果是好人）
2. 可以指出你怀疑的人
3. 可以给好人阵营留下建议
4. 长度 50-100 字

请返回 JSON 格式：{{"speech": "遗言内容", "inner_thought": "内心想法"}}"""
        
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt}
        ]
        
        content, _ = self.llm.chat(messages, max_tokens=150)
        
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(content[start:end])
                return result.get("speech", content[:100])
        except:
            pass
        
        return f"我是{self.player.role.value if self.player.role else '好人'}，希望大家能找到狼人。"
    
    def hunter_skill(self, context: dict) -> Optional[int]:
        """猎人技能 - 带走一人"""
        alive_players = context.get("alive_players", [])
        
        prompt = f"""你是猎人，你死亡了，可以带走一个玩家。

可选择的玩家：{alive_players}

请返回 JSON 格式：{{"target": 玩家编号}} 或 {{"target": null}}（不发动技能）"""
        
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt}
        ]
        
        content, _ = self.llm.chat(messages, max_tokens=50)
        
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(content[start:end])
                target = result.get("target")
                if target is not None and target in alive_players:
                    return target
        except:
            pass
        
        return None
