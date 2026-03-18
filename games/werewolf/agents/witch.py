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
        
        Args:
            context: 夜晚行动上下文
            {
                "has_death": bool,                    # 狼人是否刀了人（不考虑守卫）
                "heal_used": bool,                    # 解药是否已用
                "poison_used": bool,                  # 毒药是否已用
                "is_first_night": bool,               # 是否首夜
                "alive_players": [int],               # 存活玩家
                "my_id": int,                         # 我的ID
                "can_dual_use": bool,                 # 是否可双药同夜使用
                "cannot_poison_first_night": bool     # 首夜是否不能用毒
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
        action = {"action": "none"}
        
        # 决定是否使用解药
        if has_death and not self.heal_used:
            # 策略：优先救自己，其次救确认的好人
            # 由于信息隔离，这里只能基于概率和策略决定
            should_save = await self._decide_to_save(context)
            if should_save:
                action["action"] = "heal"
                # 由于信息隔离，女巫不知道具体被刀的是谁
                # 但在实现中，我们会传递实际的被刀目标
                action["save_target"] = context.get("wolf_target")  # 实际被刀目标
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
        
        Args:
            context: 夜晚行动上下文
            
        Returns:
            是否使用解药
        """
        # 策略：如果狼人刀了人，且是首夜或刀的是自己或确认的好人，则救人
        is_first_night = context.get("is_first_night", False)
        my_id = context.get("my_id")
        wolf_target = context.get("wolf_target")
        
        # 信息隔离：女巫不知道具体被刀的是谁，只能基于策略决定
        # 简化策略：首夜大概率救人，其他时候看情况
        if is_first_night:
            return True
        elif wolf_target == my_id:
            # 如果是自己被刀，根据配置决定是否自救
            if context.get("rules", {}).get("witch_can_self_heal", True):
                return True
            else:
                return False
        else:
            # 其他情况，根据策略决定是否救人
            # 这里需要更多的上下文信息来做出判断
            return False  # 简化处理
    
    async def _decide_to_poison(self, context: Dict[str, Any]) -> Optional[int]:
        """
        决定是否使用毒药及毒谁
        
        Args:
            context: 夜晚行动上下文
            
        Returns:
            毒杀目标ID，None表示不使用毒药
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
        
        if not candidates:
            return None
        
        # 女巫投票策略：基于夜晚行动信息和白天观察
        prompt = f"""你是{self.name}（女巫），正在进行投票。
候选人：{candidates}
请根据你的夜晚行动信息（救人/毒人）和白天观察，选择你认为最可能是狼人的玩家进行投票。
记住不要因为投票过于精准而暴露你的女巫身份。"""
        
        response = await self.llm_service.generate_response(prompt)
        
        # 解析响应，尝试找到候选人ID
        for candidate in candidates:
            if str(candidate) in response:
                self.add_memory(f"投票给 {candidate} 号玩家")
                return candidate
        
        # 如果无法确定，返回None（弃票）
        return None