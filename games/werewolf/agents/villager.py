from .base import WerewolfAgent
from ..config import Role
from typing import Dict, Any, Optional


class VillagerAgent(WerewolfAgent):
    """
    村民 Agent
    """
    
    def __init__(self, player_id: int, name: str, personality: str, llm_service: object):
        super().__init__(player_id, name, Role.VILLAGER, personality, llm_service)
    
    async def night_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        村民夜晚行动：无行动
        
        Args:
            context: 夜晚行动上下文
        """
        # 村民在夜晚无法行动
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
            # 讨论阶段：分析局势，表达观点
            prompt = f"""你是{self.name}（村民），正在白天讨论阶段。
当前存活玩家：{game_info.get('alive_players', [])}
请根据已知信息发表评论，分析谁可能是狼人。
作为村民，你需要仔细观察其他玩家的发言和行为。"""
            
        elif day_phase == "accusation":
            # 指认阶段：根据观察指认疑似狼人
            prompt = f"""你是{self.name}（村民），正在指认阶段。
当前存活玩家：{game_info.get('alive_players', [])}
请根据之前的发言和行为，指认你认为最像狼人的玩家，并说明理由。"""
            
        elif day_phase == "defense":
            # 辩护阶段：如果被指认，则为自己辩护
            accused_by = context.get("accused_by", [])
            if self.player_id in [item.get('target') for item in accused_by]:
                prompt = f"""你是{self.name}（村民），正在被其他玩家怀疑。
请为自己辩护，说明为什么你不可能是狼人，强调你的村民身份。"""
            else:
                prompt = f"""你是{self.name}（村民），目前没有被怀疑。
请继续观察局势，支持你认为可信的玩家。"""
                
        elif day_phase == "last_words":
            # 遗言阶段：如果即将死亡，分享观察到的信息
            prompt = f"""你是{self.name}（村民），即将死亡，发表遗言。
请分享你在游戏中观察到的重要信息，提醒其他好人注意某些玩家的行为。"""
        else:
            prompt = f"""你是{self.name}（村民），请根据当前局势发表合适的言论。"""
        
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
        
        # 村民投票策略：基于观察和推理选择最像狼人的目标
        prompt = f"""你是{self.name}（村民），正在进行投票。
候选人：{candidates}
请根据他们的发言、行为和你的判断，选择你认为最可能是狼人的玩家进行投票。
如果你无法确定，可以弃票。"""
        
        response = await self.llm_service.generate_response(prompt)
        
        # 解析响应，尝试找到候选人ID
        for candidate in candidates:
            if str(candidate) in response:
                self.add_memory(f"投票给 {candidate} 号玩家")
                return candidate
        
        # 如果无法确定，返回None（弃票）
        return None