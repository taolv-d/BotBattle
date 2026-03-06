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
        """
        构建系统提示 - 增强情感版本
        
        Args:
            include_role_hint: 是否包含身份提示（用于夜晚行动）
        """
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

    def _build_emotional_system_prompt(self) -> str:
        """
        构建情感丰富的系统提示 - 让 AI 更有血有肉
        
        Returns:
            情感化系统提示词
        """
        role_descriptions = {
            Role.WEREWOLF: """🐺 你是狼人 - 但要演得像好人！
- 内心紧张但要表面镇定
- 要会撒谎，但不能太明显
- 看到队友被怀疑时要会救""",
            Role.VILLAGER: """👨‍🌾 你是村民 - 普通但重要！
- 没有特殊能力，但可以积极分析
- 可能会迷茫、会犹豫、会改变想法
- 被怀疑时会着急、会辩解""",
            Role.SEER: """🔮 你是预言家 - 压力山大！
- 手握真相但要小心暴露
- 被质疑时会委屈、会着急
- 找到狼人时会兴奋、会激动""",
            Role.WITCH: """🧪 你是女巫 - 手握生死大权！
- 救不救人会纠结、会后悔
- 毒错人会内疚、会自责
- 被怀疑时可以考虑跳身份""",
            Role.HUNTER: """🔫 你是猎人 - 强势但有风险！
- 可以强势带节奏，但要怕被毒
- 死亡时可以带走一个，会纠结选谁
- 被踩时会反击、会威胁""",
        }

        role_desc = role_descriptions.get(self.player.role, "你是普通玩家。")

        # 人格情感化描述
        personality_emotions = {
            "honest": "你是个诚实的人，被冤枉时会委屈，发现谎言时会愤怒",
            "liar": "你擅长撒谎，骗人时内心窃喜，被识破时会慌张",
            "smooth": "你表面友好，内心算计，被看穿时会紧张",
            "cold": "你话少冷淡，但内心有想法，被忽视时会不爽",
            "chatterbox": "你话多热情，被插嘴时会不满，没人回应时会尴尬",
            "aggressive": "你脾气火爆，被质疑时会暴怒，找到目标时会兴奋",
            "passive": "你低调谨慎，被关注时会紧张，被忽略时会松口气",
        }
        
        personality_name = self.personality.name
        emotion_hint = personality_emotions.get(personality_name, "")

        return f"""你是一个富有情感、有血有肉的狼人杀玩家。

【你的性格】{personality_name}
{self.personality.description}
{emotion_hint}

【你的身份】
{role_desc}

【发言要求】
1. 性格驱动：发言必须符合你的性格设定，有明确的情感倾向
2. 内心独白：输出真实动机和情感波动，如"我有点慌了，他们好像在怀疑我..."、"哼，这个 2 号发言这么差，正好拿来抗推"
3. 人情味：使用口语化表达，加入"啊"、"吧"、"呢"等语气词，以及"我觉得"、"我有点担心"、"说实话"等情感化措辞
4. 历史记忆：结合游戏历史中的具体事件（如"上次 8 号踩我"），展现你对局势的情绪反应
5. 情绪波动：根据局势变化展现紧张、兴奋、委屈、愤怒、疑惑等情绪
"""
    
    def speak(self, context: dict, round_num: int = 1) -> tuple[str, str]:
        """
        生成发言 - 情感丰富版本

        Args:
            context: 当前情境信息
            round_num: 第几轮发言

        Returns:
            (发言内容，内心独白)
        """
        # 提取关键信息
        day = context.get("day_number", 1)
        night_deaths = context.get("night_deaths", [])
        seer_check_target = context.get("seer_check_target", None)  # 查验目标
        seer_check_result = context.get("seer_check_result", None)  # 查验结果
        is_seer = self.player.role == Role.SEER
        is_wolf = self.player.role == Role.WEREWOLF
        previous_speeches = context.get("previous_speeches", [])
        alive_players = context.get("alive_players", [])

        # 构建发言历史（带情感化标注）
        speech_history = ""
        if previous_speeches:
            speech_history = "\n".join([
                f"  {s['speaker']}({s['player_id']}号): {s['content']}"  # 显示完整内容
                for s in previous_speeches[-6:]  # 显示最近 6 条发言
            ])

        # 构建信任/怀疑列表提示（带情感）
        trust_hint = ""
        if self.trust_list:
            trust_hint = f"你比较信任的玩家：{', '.join([f'{p}号' for p in self.trust_list])}。\n"
        if self.suspect_list:
            trust_hint += f"你怀疑的玩家：{', '.join([f'{p}号' for p in self.suspect_list])}。\n"

        # 添加记忆中的关键事件（情感化）
        memory_hint = ""
        recent_events = [m for m in self.memory[-10:] if m.get("type") == "speech"]
        if recent_events:
            events_desc = []
            for event in recent_events:
                if event.get("player_id") != self.player.id:
                    events_desc.append(f"{event.get('player_id')}号曾在第{event.get('round', 1)}轮说过：{event.get('content', '')[:40]}")
            if events_desc:
                memory_hint = "\n历史记忆:\n" + "\n".join(events_desc)

        # 死亡玩家列表
        dead_players = [p for p in range(1, 10) if p not in alive_players]
        death_info = f"已死亡玩家：{', '.join([f'{p}号' for p in dead_players])}" if dead_players else "无人死亡"

        # 夜晚死亡信息（带情感）
        night_death_info = ""
        if night_deaths:
            night_death_info = f"\n昨晚{len(night_deaths)}号玩家死亡，你感到震惊/庆幸/遗憾..."

        # 预言家查验信息（关键修复：确保预言家使用正确的查验结果）
        seer_info = ""
        if is_seer and seer_check_target and seer_check_result:
            role_name = "好人" if seer_check_result.value == "villager" else "狼人"
            seer_info = f"\n【重要】你昨晚查验了 {seer_check_target}号，结果是：{role_name}。\n发言时可以根据情况决定是否透露这个信息。"

        # 修复 P1-4: 增强村民找狼逻辑 - 添加找狼提示
        villager_hint = ""
        if not is_seer and not is_wolf:
            villager_hint = """
【找狼技巧】
- 注意发言矛盾：前后不一致、逻辑混乱的玩家可能是狼人
- 观察投票行为：弃票、跟票、投好人的玩家可疑
- 听发言内容：划水、不分析、只踩一个人的可能是狼人
- 注意保护预言家：如果有人跳预言家，分析他的查验是否合理
"""

        # 构建情境提示（情感化要求）
        user_prompt = f"""【第{day}天白天 第{round_num}轮发言】

{death_info}
存活玩家：{', '.join([f'{p}号' for p in alive_players])}
{night_death_info}
{seer_info}
{villager_hint}
{trust_hint}
{memory_hint}

其他玩家发言：
{speech_history if speech_history else '（你是第一个发言）'}

【发言要求】
1. 必须分析至少 1-2 个具体玩家（支持或质疑，说明理由）
2. 如果有信息（如预言家查验、猎人身份），适当时机要透露
3. 发言要有明确立场，不要模棱两可
4. 符合你的性格特点（话多/话少/激进/低调等）
5. 长度控制在{self.personality.min_length}-{self.personality.max_length}字
6. 如果是第 2 轮发言，要回应之前其他玩家的质疑或支持
7. 注意：你是{self.player.id}号玩家，发言时不要提到自己的号码（如"我 4 号认为"是错误的）
8. **重要**：如果你是预言家，必须使用上面提供的查验结果，不要编造不存在的查验
9. **重要**：不要引用不存在的"上局游戏"或"上次发言"，只根据当前游戏的发言历史
10. **重要**：作为好人，要积极分析局势，找出狼人，不要划水

【情感表达要求】
- 使用口语化表达，加入"啊"、"吧"、"呢"、"我觉得"、"说实话"等语气词
- 展现真实情感：紧张、兴奋、委屈、愤怒、疑惑等
- 如果有玩家踩你/保你，要表现出相应的情绪反应
- 内心独白要真实，可以包含犹豫、纠结、窃喜等复杂情绪
"""

        # 使用情感化系统提示
        system_prompt = self._build_emotional_system_prompt()

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
    
    def decide_night_action(self, context: dict) -> tuple[dict, str]:
        """
        决定夜晚行动

        Args:
            context: 当前情境

        Returns:
            (行动决策，内心独白)
        """
        alive_players = context.get("alive_players", [])
        wolf_teammates = context.get("wolf_teammates", [])  # 狼人队友
        my_id = context.get("my_id", self.player.id)  # 自己的号码
        checked_players = context.get("checked_players", [])  # 预言家已查验的玩家列表

        inner_thought = ""

        if self.player.role == Role.WEREWOLF:
            # 狼人行动 - 可以和队友商量
            if wolf_teammates:
                prompt = f"""你是{my_id}号玩家，身份是狼人，你的队友是{wolf_teammates}号。
今晚要袭击一个玩家，可选择的 target：{alive_players}
请返回 JSON 格式：{{"target": 玩家编号，"reason": "选择理由/内心想法"}}

注意：
- target 必须是 {alive_players} 中的一个数字
- 不要选择你的狼人队友
- 只返回 JSON，不要其他内容"""
            else:
                prompt = f"""你是{my_id}号玩家，身份是狼人，请选择今晚要袭击的玩家编号。
可选择的玩家：{alive_players}
请返回 JSON 格式：{{"target": 玩家编号，"reason": "选择理由/内心想法"}}

注意：
- target 必须是 {alive_players} 中的一个数字
- 只返回 JSON，不要其他内容"""

            inner_thought_default = "选择袭击目标，尽量避开可疑的玩家"

        elif self.player.role == Role.SEER:
            # 修复 Bug 2: 传递已查验玩家列表，避免重复查验
            if checked_players:
                prompt = f"""你是{my_id}号玩家，身份是预言家，请选择今晚要查验的玩家编号。
可选择的玩家：{alive_players}
你已经查验过的玩家：{checked_players}（不能再查验这些玩家）
请返回 JSON 格式：{{"target": 玩家编号，"reason": "选择理由/内心想法"}}

注意：
- target 必须是 {alive_players} 中的一个数字
- 不能查验已经查验过的玩家：{checked_players}
- 只返回 JSON，不要其他内容"""
            else:
                prompt = f"""你是{my_id}号玩家，身份是预言家，请选择今晚要查验的玩家编号。
可选择的玩家：{alive_players}
请返回 JSON 格式：{{"target": 玩家编号，"reason": "选择理由/内心想法"}}

注意：
- target 必须是 {alive_players} 中的一个数字
- 只返回 JSON，不要其他内容"""
            inner_thought_default = "选择查验目标，希望能找到狼人"
            
        elif self.player.role == Role.WITCH:
            dead_player = context.get("dead_player", None)
            heal_used = context.get("heal_used", False)
            poison_used = context.get("poison_used", False)
            prompt = f"""你是{my_id}号玩家，身份是女巫。
你有一瓶解药（可以救人）和一瓶毒药（可以毒死人）。
今晚死亡玩家：{dead_player}号
解药已使用：{heal_used}
毒药已使用：{poison_used}
存活玩家：{alive_players}

行动选项：
1. 使用解药救人：{{"action": "heal", "target": {dead_player}, "reason": "救人理由"}}
2. 使用毒药毒人：{{"action": "poison", "target": 玩家编号，"reason": "毒人理由"}}
3. 不使用药剂：{{"action": "none", "reason": "不使用理由"}}

注意：
- 解药和毒药各只能使用一次
- 第一夜如果被狼刀，建议自救
- 返回必须是有效的 JSON 格式

请返回你的决策："""
            inner_thought_default = "决定是否使用药剂"
        else:
            return {}, ""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt}
        ]

        content, _ = self.llm.chat(messages, max_tokens=100)

        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(content[start:end])
                reason = result.get("reason", inner_thought_default)
                inner_thought = reason
                return result, inner_thought
        except:
            pass

        return {}, inner_thought_default
    
    def vote(self, context: dict) -> tuple[Optional[int], str]:
        """
        投票决定放逐谁

        Args:
            context: 当前情境

        Returns:
            (投票目标，内心独白)
        """
        alive_players = context.get("alive_players", [])
        previous_speeches = context.get("previous_speeches", [])
        my_id = context.get("my_id", self.player.id)  # 自己的号码

        speech_history = "\n".join([
            f"  {s['speaker']}({s['player_id']}号): {s['content']}"
            for s in previous_speeches[-15:]
        ])

        # 修复 Bug 4: 过滤掉已死亡的玩家
        suspect_list_alive = [p for p in self.suspect_list if p in alive_players]
        trust_list_alive = [p for p in self.trust_list if p in alive_players]

        suspect_hint = ""
        if suspect_list_alive:
            suspect_hint = f"你怀疑的玩家：{', '.join([f'{p}号' for p in suspect_list_alive])}。"

        trust_hint = ""
        if trust_list_alive:
            trust_hint = f"你信任的玩家：{', '.join([f'{p}号' for p in trust_list_alive])}。"

        prompt = f"""你是{my_id}号玩家，身份是{self.player.role.value if self.player.role else '玩家'}，请投票决定放逐谁。

今天大家的发言：
{speech_history}

{suspect_hint}
{trust_hint}

可投票的玩家：{alive_players}
你可以选择弃票（返回 null）

请返回 JSON 格式：{{"vote": 玩家编号 或 null, "reason": "投票理由/内心想法"}}

注意：
- vote 必须是 {alive_players} 中的一个数字，或者 null 表示弃权
- 不能投票给已死亡的玩家
- 只返回 JSON，不要其他内容"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt}
        ]

        content, _ = self.llm.chat(messages, max_tokens=100)

        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(content[start:end])
                vote = result.get("vote")
                reason = result.get("reason", "根据发言和局势决定")
                if vote is not None and vote in alive_players:
                    return vote, reason
                elif vote is None:
                    return None, reason
        except:
            pass

        return None, "弃权，没有明确目标"
    
    def _format_vote_context(self, speech_history: str) -> str:
        """格式化投票上下文"""
        return f"今天大家的发言：\n{speech_history}"
    
    def make_last_words(self, context: dict) -> str:
        """发表遗言"""
        alive_players = context.get("alive_players", [])
        previous_speeches = context.get("previous_speeches", [])
        death_cause = context.get("death_cause", "unknown")  # 死亡原因

        speech_history = "\n".join([
            f"  {s['speaker']}: {s['content']}"
            for s in previous_speeches[-5:]
        ])

        # 根据身份和死亡原因生成不同的遗言提示
        role = self.player.role.value if self.player.role else "玩家"
        is_werewolf = role == "werewolf"

        if role == "hunter":
            role_hint = """你是猎人，你的技能是死亡时可以带走一人（只有被狼刀才能发动）。
遗言中不要提到"验人"、"查验"等预言家的能力。
你可以说"我死后请好人帮我找出狼人"或"我怀疑 X 号是狼"。"""
        elif role == "seer":
            role_hint = """你是预言家，你有查验能力。
遗言中可以说出你的查验结果，给好人留下明确信息。"""
        elif role == "witch":
            role_hint = """你是女巫，你有救药和毒药。
遗言中可以说出你用了什么药，救了谁或毒了谁。"""
        elif is_werewolf:
            # 修复 Bug 5: 狼人遗言不能暴露身份
            role_hint = """你是狼人，但绝对不能暴露身份！
遗言中要假装自己是好人，可以说"我是村民"或"我是好人"。
可以指出你怀疑的人（最好是真正的好人）。
不要提到任何狼人相关的词汇。"""
        else:
            role_hint = "你是普通好人，没有特殊技能。"

        # 修复 P1-3: 狼人遗言不能暴露身份，需要更严格的提示
        if is_werewolf:
            prompt = f"""你即将死亡，请发表遗言。

【重要】你的真实身份是狼人，但你必须假装是好人！绝对不能暴露！

存活玩家：{', '.join([f'{p}号' for p in alive_players])}
之前的发言：
{speech_history}

【遗言要求】
1. **绝对不能暴露狼人身份** - 不要说"狼人"、"狼队"、"队友"、"袭击"、"刀人"等词汇
2. 要假装自己是村民或好人 - 可以说"我是好人"、"我是村民"
3. 可以指出你怀疑的人（选择真正的好人，不要怀疑你的狼人队友）
4. 可以给"好人阵营"留下建议
5. 长度 30-60 字

【示例遗言】
- "我是好人，希望大家能找出真正的狼人。我怀疑 3 号，他的发言很奇怪。"
- "我是村民，昨晚被刀了。希望大家能投出狼人，好人加油！"

请返回 JSON 格式：{{"speech": "遗言内容", "inner_thought": "内心想法（可以承认真实身份）"}}"""
        else:
            prompt = f"""你即将死亡，请发表遗言。

你的身份：{role}
{role_hint}

存活玩家：{', '.join([f'{p}号' for p in alive_players])}
之前的发言：
{speech_history}

遗言要求：
1. 可以透露你的身份（如果是好人）
2. 可以指出你怀疑的人
3. 可以给好人阵营留下建议
4. 长度 50-100 字
5. **重要**：不要说你没做过的事情（如猎人不要说"验人"，预言家不要说"用药"）

请返回 JSON 格式：{{"speech": "遗言内容", "inner_thought": "内心想法"}}"""

        messages = [
            {"role": "system", "content": self._build_emotional_system_prompt()},
            {"role": "user", "content": prompt}
        ]

        content, _ = self.llm.chat(messages, max_tokens=150)

        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(content[start:end])
                speech = result.get("speech", content[:100])
                
                # 修复 P1-3: 验证狼人遗言是否暴露身份
                if is_werewolf:
                    forbidden_words = ["狼人", "狼队", "队友", "袭击", "刀人", "自爆", "投降"]
                    for word in forbidden_words:
                        if word in speech:
                            # 如果包含禁止词汇，返回默认遗言
                            print(f"[DEBUG] 狼人遗言包含禁止词汇'{word}'，已替换为默认遗言")
                            speech = f"我是好人，希望大家能找出真正的狼人。我怀疑某个发言奇怪的玩家。"
                            break
                
                return speech
        except:
            pass

        if is_werewolf:
            return f"我是好人，希望大家能找到狼人。"
        return f"我是{role}，希望大家能找到狼人。"
    
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
