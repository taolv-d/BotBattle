from .base import WerewolfAgent
from ..config import Role
from typing import Dict, Any, Optional


class HunterAgent(WerewolfAgent):
    """
    猎人 Agent
    """

    def __init__(self, player_id: int, name: str, personality: str, llm_service: object):
        super().__init__(player_id, name, Role.HUNTER, personality, llm_service)

    async def night_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        猎人夜晚行动：无特殊行动

        Args:
            context: 夜晚行动上下文
        """
        # 猎人在夜晚无法行动
        return {"action": "none"}

    async def speak(self, context: Dict[str, Any]) -> str:
        """
        白天发言

        Args:
            context: 发言上下文
        """
        game_info = context.get("game_info", {})
        day_phase = context.get("day_phase", "discussion")  # discussion, accusation, defense, last_words

        if day_phase == "discussion":
            # 讨论阶段：积极参与讨论，分析局势
            prompt = f"""你是{self.name}（猎人），正在白天讨论阶段。
当前存活玩家：{game_info.get('alive_players', [])}
请积极参与讨论，分析谁可能是狼人。
作为猎人，你有一定的威慑力，可以利用这一点影响局势。"""

        elif day_phase == "accusation":
            # 指认阶段：根据分析指认狼人
            prompt = f"""你是{self.name}（猎人），正在指认阶段。
当前存活玩家：{game_info.get('alive_players', [])}
请根据你的分析和观察，指认你认为最像狼人的玩家，并说明理由。
作为猎人，你的指认真具有一定的分量。"""

        elif day_phase == "defense":
            # 辩护阶段：如果被指认，则为自己辩护
            accused_by = context.get("accused_by", [])
            if self.player_id in [item.get('target') for item in accused_by]:
                prompt = f"""你是{self.name}（猎人），正在被其他玩家怀疑。
请为自己辩护，强调你的猎人身份和好人立场。
可以适当展示你的威慑力，但不要过于激进。"""
            else:
                prompt = f"""你是{self.name}（猎人），目前没有被怀疑。
请继续支持好人阵营，利用你的身份影响局势。"""

        elif day_phase == "last_words":
            # 遗言阶段：如果即将死亡，分享信息并警告
            prompt = f"""你是{self.name}（猎人），即将死亡，发表遗言。
请分享你的重要发现，警告好人阵营注意某些玩家。
同时，你可以暗示你的猎人身份带来的威慑力。"""
        else:
            prompt = f"""你是{self.name}（猎人），请根据当前局势发表合适的言论。"""

        response = await self.think(prompt)
        self.add_memory(f"发言：{response}")
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
        import json

        candidates = context.get("candidates", [])

        if not candidates:
            return None

        # 猎人投票策略：基于分析选择最像狼人的目标
        prompt = f"""你是{self.name}（猎人），正在进行投票。

候选人：{candidates}

请根据你的分析和观察，选择你认为最可能是狼人的玩家进行投票。
作为猎人，你的投票可能会影响局势。

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
                if vote is not None and vote in candidates:
                    self.add_memory(f"投票给 {vote} 号玩家")
                    return vote
                elif vote is None:
                    self.add_memory("投票弃票")
                    return None
        except Exception:
            pass

        # JSON 解析失败，尝试从响应中找到候选人 ID（向后兼容）
        for candidate in candidates:
            if str(candidate) in response:
                self.add_memory(f"投票给 {candidate} 号玩家")
                return candidate

        # 如果无法确定，返回 None（弃票）
        return None

    async def hunter_skill(self, context: Dict[str, Any]) -> Optional[int]:
        """
        猎人技能发动

        Args:
            context: 技能上下文
            {
                "alive_players": [int],
                "death_cause": str,
                "my_id": int
            }
        """
        alive_players = context.get("alive_players", [])
        death_cause = context.get("death_cause", "")

        if not alive_players:
            return None

        # 根据死亡原因判断是否可以开枪
        # 根据配置，有些情况下不能开枪
        can_shoot = True  # 简化处理，在实际实现中需要根据配置判断

        if not can_shoot:
            return None

        # 猎人开枪策略：选择对狼人阵营威胁最小或对好人阵营威胁最大的玩家
        prompt = f"""你是{self.name}（猎人），即将死亡，可以开枪带走一名玩家。
死亡原因：{death_cause}
场上存活玩家：{alive_players}
请决定开枪目标，选择你认为最合适的目标。"""

        response = await self.llm_service.generate_response(prompt)

        # 解析响应，尝试找到目标 ID
        for player_id in alive_players:
            if str(player_id) in response:
                self.add_memory(f"猎人开枪击中 {player_id} 号玩家")
                return player_id

        # 如果无法确定，随机选择
        import random
        return random.choice(alive_players) if alive_players else None
