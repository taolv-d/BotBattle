from .base import WerewolfAgent
from ..config import Role
from typing import Dict, Any, Optional


class SeerAgent(WerewolfAgent):
    """
    预言家 Agent
    """
    
    def __init__(self, player_id: int, name: str, personality: str, llm_service: object):
        super().__init__(player_id, name, Role.SEER, personality, llm_service)
        self.checked_players = set()  # 已查验的玩家
    
    async def night_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        预言家夜晚行动：选择查验目标
        
        Args:
            context: 夜晚行动上下文
            {
                "alive_players": [int],  # 存活玩家列表
                "my_id": int,            # 我的ID
                "checked_players": [int] # 已查验玩家
            }
        """
        alive_players = context.get("alive_players", [])
        self.checked_players = set(context.get("checked_players", []))
        
        # 过滤掉已查验的玩家和自己
        possible_targets = [pid for pid in alive_players if pid != self.player_id and pid not in self.checked_players]
        
        if not possible_targets:
            # 没有可查验的目标
            return {"action": "skip", "target": None}
        
        # 策略：优先查验发言异常或行为可疑的玩家
        # 简化：随机选择一个未查验的玩家
        target = possible_targets[0]  # 可以根据策略调整选择方式
        
        # 记录查验意图
        self.add_memory(f"夜晚决定查验 {target} 号玩家")
        
        return {"action": "check", "target": target}
    
    async def speak(self, context: Dict[str, Any]) -> str:
        """
        白天发言
        
        Args:
            context: 发言上下文
        """
        game_info = context.get("game_info", {})
        day_phase = context.get("day_phase", "discussion")  # discussion, accusation, defense, last_words
        
        if day_phase == "discussion":
            # 讨论阶段：分享查验信息，引导好人阵营
            # 获取已查验玩家的身份信息（这部分需要从游戏状态获取）
            checked_info = context.get("checked_info", {})  # {player_id: role}
            
            if checked_info:
                prompt = f"""你是{self.name}（预言家），正在白天讨论阶段。
你已查验的玩家及其身份：{checked_info}
当前存活玩家：{game_info.get('alive_players', [])}
请分享你的查验结果，提醒好人阵营注意狼人，同时小心不要被狼人针对。"""
            else:
                prompt = f"""你是{self.name}（预言家），正在白天讨论阶段。
你尚未查验任何人，但可以根据其他玩家的发言和行为进行初步分析。
请发表评论，引导好人阵营识别狼人。"""
            
        elif day_phase == "accusation":
            # 指认阶段：基于查验结果指认狼人
            checked_info = context.get("checked_info", {})
            suspicious_wolves = [pid for pid, role in checked_info.items() if role == "werewolf"]
            
            if suspicious_wolves:
                prompt = f"""你是{self.name}（预言家），正在指认阶段。
你确认的狼人：{suspicious_wolves}
请正式指认这些玩家为狼人，并呼吁其他好人投票给他们。"""
            else:
                prompt = f"""你是{self.name}（预言家），正在指认阶段。
虽然你没有确认的狼人，但可以根据查验的好人或其他线索进行推测。
请指认你认为最可疑的玩家。"""
                
        elif day_phase == "defense":
            # 辩护阶段：如果被指认，则为自己辩护
            accused_by = context.get("accused_by", [])
            if self.player_id in [item.get('target') for item in accused_by]:
                # 预言家被怀疑时，需要特别辩护
                checked_info = context.get("checked_info", {})
                prompt = f"""你是{self.name}（预言家），正在被其他玩家怀疑。
你已查验的玩家及其身份：{checked_info}
请为自己辩护，解释你的查验逻辑，证明你的预言家身份。
提醒其他好人不要被狼人混淆视听。"""
            else:
                prompt = f"""你是{self.name}（预言家），目前没有被怀疑。
请继续支持好人阵营，提供你的分析和建议。"""
                
        elif day_phase == "last_words":
            # 遗言阶段：分享重要信息
            checked_info = context.get("checked_info", {})
            prompt = f"""你是{self.name}（预言家），即将死亡，发表遗言。
你已查验的玩家及其身份：{checked_info}
请分享最重要的信息，提醒其他好人注意关键的狼人身份。
这可能是你最后一次帮助好人阵营的机会。"""
        else:
            prompt = f"""你是{self.name}（预言家），请根据当前局势发表合适的言论。"""
        
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
                "my_id": int,
                "checked_info": dict  # {player_id: role}
            }
        """
        candidates = context.get("candidates", [])
        checked_info = context.get("checked_info", {})
        
        if not candidates:
            return None
        
        # 预言家投票策略：优先投票已确认的狼人，其次根据查验结果和推理
        confirmed_wolves = [pid for pid in candidates if checked_info.get(pid) == "werewolf"]
        
        if confirmed_wolves:
            # 优先投票已确认的狼人
            target = confirmed_wolves[0]
        else:
            # 如果没有确认的狼人，根据其他线索投票
            prompt = f"""你是{self.name}（预言家），正在进行投票。
候选人：{candidates}
你已查验的玩家及其身份：{checked_info}
请根据你的查验结果和其他线索，选择你认为最可能是狼人的玩家进行投票。"""
            
            response = await self.llm_service.generate_response(prompt)
            
            # 解析响应，尝试找到候选人ID
            for candidate in candidates:
                if str(candidate) in response:
                    target = candidate
                    break
            else:
                # 如果无法确定，返回None（弃票）
                return None
        
        self.add_memory(f"投票给 {target} 号玩家")
        return target