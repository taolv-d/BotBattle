from .base import WerewolfAgent
from ..config import Role, DeathCause
from typing import Dict, Any, Optional


class WitchAgent(WerewolfAgent):
    """
    女巫 Agent
    """

    def __init__(self, player_id: int, name: str, personality: str, llm_service: object):
        super().__init__(player_id, name, Role.WITCH, personality, llm_service)
        self.heal_used = False      # 解药已使用
        self.poison_used = False    # 毒药已使用

    async def night_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        女巫夜晚行动：选择使用解药或毒药

        深度信息隔离原则：
        1. 女巫只知道"狼人是否刀了人"（has_death）
        2. 不知道具体被刀的是谁（wolf_target 不传递）
        3. 不知道守卫守护情况
        4. save_target 由 Orchestrator 设置，不由女巫 Agent 设置

        Args:
            context: 夜晚行动上下文
            {
                "has_death": bool,                    # 狼人是否刀了人（不考虑守卫）
                "heal_used": bool,                    # 解药是否已用
                "poison_used": bool,                  # 毒药是否已用
                "is_first_night": bool,               # 是否首夜
                "alive_players": [int],               # 存活玩家
                "my_id": int,                         # 我的 ID
                "can_dual_use": bool,                 # 是否可双药同夜使用
                "cannot_poison_first_night": bool,    # 首夜是否不能用毒
                "rules": dict                         # 游戏规则配置
            }
        """
        has_death = context.get("has_death", False)
        self.heal_used = context.get("heal_used", False)
        self.poison_used = context.get("poison_used", False)
        is_first_night = context.get("is_first_night", False)
        alive_players = context.get("alive_players", [])
        can_dual_use = context.get("can_dual_use", False)
        cannot_poison_first_night = context.get("cannot_poison_first_night", False)

        # 深度信息隔离：女巫只知道狼人是否刀了人，不知道具体是谁
        # 也不清楚守卫是否守护了人
        # 注意：wolf_target 不传递给女巫 Agent，由 Orchestrator 处理
        action = {"action": "none"}

        # 决定是否使用解药
        if has_death and not self.heal_used:
            # 策略：基于信息隔离，女巫不知道具体被刀的是谁
            # 只能根据策略决定是否救人
            should_save = await self._decide_to_save(context)
            if should_save:
                action["action"] = "heal"
                # 信息隔离：女巫不知道具体被刀的是谁
                # save_target 由 Orchestrator 设置，女巫只表示"我要救人"
                # 不设置 action["save_target"]
                self.heal_used = True

        # 决定是否使用毒药
        if not self.poison_used:
            if cannot_poison_first_night and is_first_night:
                # 首夜不能用毒
                pass
            else:
                poison_target = await self._decide_to_poison(context)
                if poison_target:
                    if action["action"] == "none":
                        action["action"] = "poison"
                        action["poison_target"] = poison_target
                        self.poison_used = True
                    elif action["action"] == "heal" and can_dual_use:
                        # 可以双药同夜使用
                        action["action"] = "dual"
                        action["poison_target"] = poison_target
                        self.poison_used = True

        return action

    async def _decide_to_save(self, context: Dict[str, Any]) -> bool:
        """
        决定是否使用解药

        信息隔离：女巫不知道具体被刀的是谁，只能基于策略决定

        Args:
            context: 夜晚行动上下文

        Returns:
            是否使用解药
        """
        # 策略：如果狼人刀了人，根据策略决定是否救人
        is_first_night = context.get("is_first_night", False)
        rules = context.get("rules", {})

        # 信息隔离：女巫不知道具体被刀的是谁
        # 简化策略：首夜大概率救人，其他时候看情况
        if is_first_night:
            # 首夜通常救人，因为首夜死亡有遗言，可以传递信息
            return True
        else:
            # 非首夜，根据策略决定
            # 这里可以添加更复杂的策略，比如根据白天发言判断
            # 简化处理：非首夜不轻易救人
            return False

    async def _decide_to_poison(self, context: Dict[str, Any]) -> Optional[int]:
        """
        决定是否使用毒药及毒谁

        Args:
            context: 夜晚行动上下文

        Returns:
            毒杀目标 ID，None 表示不使用毒药
        """
        alive_players = context.get("alive_players", [])
        my_id = context.get("my_id")

        # 策略：优先毒可能的狼人，特别是行为异常的
        # 由于信息隔离，女巫无法确切知道谁是狼人
        # 简化策略：随机选择一个非自己的存活玩家（实际应用中应更智能）
        possible_targets = [pid for pid in alive_players if pid != my_id]

        if possible_targets:
            # 这里应该根据已知信息和推理来选择目标
            # 简化：返回第一个可能的目标
            return possible_targets[0]

        return None

    async def speak(self, context: Dict[str, Any]) -> str:
        """
        白天发言

        Args:
            context: 发言上下文
        """
        game_info = context.get("game_info", {})
        day_phase = context.get("day_phase", "discussion")  # discussion, accusation, defense, last_words

        if day_phase == "discussion":
            # 讨论阶段：谨慎发言，不暴露身份
            # 女巫通常会比较低调，观察局势
            prompt = f"""你是{self.name}（女巫），正在白天讨论阶段。
当前存活玩家：{game_info.get('alive_players', [])}
请注意，作为女巫你应该谨慎发言，不要过早暴露身份。
可以通过提问和观察来收集信息，但要避免引起狼人注意。"""

        elif day_phase == "accusation":
            # 指认阶段：基于夜晚信息进行分析
            # 女巫知道谁被刀了（如果有救人的话）和谁被毒了
            saved_player = context.get("saved_player")
            poisoned_player = context.get("poisoned_player")

            if saved_player is not None:
                prompt = f"""你是{self.name}（女巫），正在指认阶段。
昨晚你救了 {saved_player} 号玩家，这意味着狼人刀了他。
请根据这个信息和其他线索，分析局势并指认狼人。
注意不要暴露你的女巫身份。"""
            elif poisoned_player is not None:
                prompt = f"""你是{self.name}（女巫），正在指认阶段。
昨晚你毒死了 {poisoned_player} 号玩家。
请根据这个信息和其他线索，分析局势并指认其他狼人。
注意不要暴露你的女巫身份。"""
            else:
                prompt = f"""你是{self.name}（女巫），正在指认阶段。
请根据你的观察和推理，指认你认为的狼人。
注意不要暴露你的女巫身份。"""

        elif day_phase == "defense":
            # 辩护阶段：如果被指认，则为自己辩护
            accused_by = context.get("accused_by", [])
            if self.player_id in [item.get('target') for item in accused_by]:
                prompt = f"""你是{self.name}（女巫），正在被其他玩家怀疑。
请为自己辩护，强调你的好人身份。
注意不要因为过度辩护而暴露你的女巫身份（比如知道太多夜晚信息）。"""
            else:
                prompt = f"""你是{self.name}（女巫），目前没有被怀疑。
请继续观察局势，支持好人阵营。"""

        elif day_phase == "last_words":
            # 遗言阶段：分享重要信息
            saved_player = context.get("saved_player")
            poisoned_player = context.get("poisoned_player")

            prompt = f"""你是{self.name}（女巫），即将死亡，发表遗言。
昨晚你{'救了 ' + str(saved_player) if saved_player is not None else '没有救人'}，
{'毒死了 ' + str(poisoned_player) if poisoned_player is not None else '没有毒人'}。
请分享这些重要信息，帮助好人阵营识别狼人。
这是你最后一次帮助好人阵营的机会。"""
        else:
            prompt = f"""你是{self.name}（女巫），请根据当前局势发表合适的言论。"""

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

        # 女巫投票策略：基于夜晚行动信息和白天观察
        prompt = f"""你是{self.name}（女巫），正在进行投票。

候选人：{candidates}

请根据你的夜晚行动信息（救人/毒人）和白天观察，选择你认为最可能是狼人的玩家进行投票。
记住不要因为投票过于精准而暴露你的女巫身份。

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
