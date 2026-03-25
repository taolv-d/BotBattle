from .base import WerewolfAgent
from ..config import Role
from typing import Dict, Any, Optional
import random
import json


class WolfAgent(WerewolfAgent):
    """
    狼人 Agent
    """

    def __init__(self, player_id: int, name: str, personality: str, llm_service: object):
        super().__init__(player_id, name, Role.WEREWOLF, personality, llm_service)
        self.wolf_teammates = []  # 狼人队友列表

    async def night_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        狼人夜晚行动：选择击杀目标或空刀

        Args:
            context: 夜晚行动上下文
            {
                "alive_players": [int],  # 存活玩家列表
                "my_id": int,            # 我的ID
                "wolf_teammates": [int]  # 狼人队友
            }
        """
        alive_players = context.get("alive_players", [])
        wolf_teammates = context.get("wolf_teammates", [])

        # 更新狼人队友信息
        self.wolf_teammates = [pid for pid in wolf_teammates if pid != self.player_id]

        # 过滤掉狼人自己和狼人队友
        possible_targets = [pid for pid in alive_players if pid != self.player_id and pid not in self.wolf_teammates]

        if not possible_targets:
            # 没有可击杀的目标，空刀
            self.add_memory("夜晚没有可击杀目标，空刀")
            return {"action": "skip", "target": None}

        # 战术空刀：约10%概率选择不刀人
        # 空刀战术可以迷惑女巫，让女巫误以为有人被刀而浪费解药
        # 或者在狼人优势时减少暴露风险
        if random.random() < 0.1:
            self.add_memory("夜晚决定战术空刀，迷惑女巫")
            return {"action": "skip", "target": None}

        # 根据策略选择目标
        # 简单策略：优先击杀神职，其次是村民
        gods = []
        villagers = []

        # 这里需要访问游戏状态来判断角色，暂时简化处理
        # 在实际实现中，我们会从上下文中获得更多信息
        target = random.choice(possible_targets)

        # 记录击杀意图
        self.add_memory(f"夜晚决定击杀 {target} 号玩家")

        return {"action": "attack", "target": target}

    async def decide_self_explode(self, context: Dict[str, Any]) -> bool:
        """
        决定是否在白天自爆
        """
        alive_players = context.get("alive_players", [])
        alive_wolves = context.get("alive_wolves", [])
        day_number = context.get("day_number", 0)
        president_id = context.get("president_id")
        speech_order = context.get("speech_order", [])

        fallback = False
        if alive_players:
            wolf_ratio = len(alive_wolves) / len(alive_players)
            fallback = wolf_ratio <= 0.34 and day_number >= 2

        prompt = f"""你是{self.name}（狼人），正在评估是否要在白天自爆。

当前天数：第 {day_number} 天
当前存活玩家：{alive_players}
当前存活狼人：{alive_wolves}
当前警长：{president_id}
当前发言顺序：{speech_order}
你的狼人队友：{self.wolf_teammates}

请判断现在是否值得自爆。一般来说，只有在以下情况才考虑自爆：
1. 狼人处于明显劣势，需要立刻中断白天投票
2. 你即将被高概率放逐
3. 自爆能明显保护队友或争取夜晚轮次

如果没有足够收益，就不要自爆。

请严格返回 JSON：
{{
  "explode": true 或 false,
  "reason": "简短原因"
}}
只返回 JSON，不要其他解释。"""

        try:
            response = await self.llm_service.generate_response(prompt)
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(response[start:end])
                decision = bool(result.get("explode", False))
                reason = result.get("reason", "")
                self.add_memory(f"评估自爆：{decision}，原因：{reason}")
                return decision
        except Exception:
            pass

        self.add_memory(f"评估自爆：{fallback}（使用回退策略）")
        return fallback

    async def speak(self, context: Dict[str, Any]) -> str:
        """
        白天发言

        Args:
            context: 发言上下文
        """
        # 狼人的发言策略：混淆视听，引导投票错误目标
        game_info = context.get("game_info", {})
        day_phase = context.get("day_phase", "discussion")  # discussion, accusation, defense, last_words

        if day_phase == "discussion":
            # 讨论阶段：观察局势，适时发言混淆
            prompt = f"""你是{self.name}（狼人），正在白天讨论阶段。
你的狼人队友是：{self.wolf_teammates}
当前存活玩家：{game_info.get('alive_players', [])}
请发表评论，试图混淆视听，不要暴露身份。
你可以质疑其他玩家，但要显得自然。"""

        elif day_phase == "accusation":
            # 指认阶段：指控某个好人，转移视线
            prompt = f"""你是{self.name}（狼人），正在指认阶段。
你的狼人队友是：{self.wolf_teammates}
当前存活玩家：{game_info.get('alive_players', [])}
请选择一个好人玩家进行指控，并给出理由，试图让其他人投票给他。"""

        elif day_phase == "defense":
            # 辩护阶段：如果是被指认对象，进行辩护
            accused_by = context.get("accused_by", [])
            if self.player_id in [item.get('target') for item in accused_by]:
                prompt = f"""你是{self.name}（狼人），正在被其他玩家怀疑。
请为自己辩护，解释为什么不可能是狼人，可以编造一些合理的理由。"""
            else:
                prompt = f"""你是{self.name}（狼人），目前没有被直接怀疑。
请继续伪装，可以附和其他玩家的观点以显得正常。"""

        elif day_phase == "last_words":
            # 遗言阶段：如果即将死亡，可以尝试误导
            prompt = f"""你是{self.name}（狼人），即将死亡，发表遗言。
你可以尝试误导其他玩家，或者透露一些假信息来影响后续局势。"""
        else:
            prompt = f"""你是{self.name}（狼人），请根据当前局势发表合适的言论。"""

        response = await self.think(prompt)
        self.add_memory(f"发言: {response}")
        return response

    async def vote(self, context: Dict[str, Any]) -> Optional[int]:
        """
        投票

        Args:
            context: 投票上下文
            {
                "alive_players": [int],
                "candidates": [int],
                "previous_votes": dict,
                "my_id": int
            }
        """
        candidates = context.get("candidates", [])
        alive_players = context.get("alive_players", [])

        if not candidates:
            return None

        # 狼人投票策略：不投给自己人，尽量投给对自己威胁大的好人
        # 简化策略：随机选择非狼人候选者
        safe_candidates = [pid for pid in candidates if pid not in self.wolf_teammates and pid != self.player_id]

        if not safe_candidates:
            # 如果安全候选人为空，从存活玩家中选择非队友
            safe_candidates = [pid for pid in alive_players if pid not in self.wolf_teammates and pid != self.player_id]

        if safe_candidates:
            # 使用 LLM 决定投票目标
            prompt = f"""你是{self.name}（狼人），正在进行投票。

候选人：{candidates}
你的狼人队友：{self.wolf_teammates}

请根据他们的发言、行为和你的判断，选择你认为对狼人威胁最大的好人玩家进行投票。
**注意**：不能投票给狼人队友。

**请严格按照以下 JSON 格式返回（只返回 JSON，不要其他内容）**：
{{
    "vote": 玩家编号 或 null,  // 你要投票的玩家编号，如果弃票则返回 null
    "reason": "投票理由"
}}

**注意**：
- vote 必须是 {candidates} 中的一个数字，或者 null 表示弃票
- 不要返回字符串 "None"，如果要弃票请返回 null
- 只返回 JSON 对象，不要添加任何解释"""

            response = await self.llm_service.generate_response(prompt)

            # 解析 JSON 响应
            try:
                start = response.find("{")
                end = response.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = response[start:end]
                    result = json.loads(json_str)
                    vote = result.get("vote")
                    if vote is not None and vote in safe_candidates:
                        self.add_memory(f"投票给 {vote} 号玩家")
                        return vote
                    elif vote is None:
                        self.add_memory("投票弃票")
                        return None
            except Exception:
                pass

            # JSON 解析失败，尝试从响应中找到候选人 ID（向后兼容）
            for candidate in safe_candidates:
                if str(candidate) in response:
                    self.add_memory(f"投票给 {candidate} 号玩家")
                    return candidate

            # 如果无法确定，随机选择
            target = random.choice(safe_candidates)
            self.add_memory(f"投票给 {target} 号玩家")
            return target
        else:
            return None

    async def decide_to_run_president(self) -> bool:
        """
        决定是否参与警长竞选

        狼人通常不会主动参选，除非特殊策略需要
        """
        # 简单策略：一般不参选，但有时为了扰乱局势可能会参选
        import random
        return random.random() < 0.2  # 20% 概率参选
