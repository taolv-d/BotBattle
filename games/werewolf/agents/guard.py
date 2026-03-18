from .base import WerewolfAgent
from ..config import Role
from typing import Dict, Any, Optional


class GuardAgent(WerewolfAgent):
    """
    守卫 Agent
    """
    
    def __init__(self, player_id: int, name: str, personality: str, llm_service: object):
        super().__init__(player_id, name, Role.GUARD, personality, llm_service)
        self.guarded_players = []  # 已守护的玩家（只包含上一夜）
    
    async def night_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        守卫夜晚行动：选择守护目标
        
        Args:
            context: 夜晚行动上下文
            {
                "alive_players": [int],      # 存活玩家列表
                "my_id": int,                # 我的ID
                "guarded_players": [int],    # 已守护玩家（上一夜）
                "last_night_guarded": int    # 上一夜守护的玩家
            }
        """
        alive_players = context.get("alive_players", [])
        self.guarded_players = context.get("guarded_players", [])
        last_night_guarded = context.get("last_night_guarded")
        
        # 过滤掉上一夜守护的玩家（防止连续守护同一人）
        possible_targets = [pid for pid in alive_players if pid != last_night_guarded]
        
        if not possible_targets:
            # 如果只有一个人存活（上一夜守护的人），则守护自己
            if len(alive_players) == 1 and alive_players[0] == last_night_guarded:
                possible_targets = alive_players
        
        if not possible_targets:
            return {"action": "skip", "target": None}
        
        # 守护策略：优先守护好人身份明确的玩家或高风险目标
        # 简化：随机选择一个可能的目标
        target = possible_targets[0]  # 可以根据策略调整选择方式
        
        # 记录守护意图
        self.add_memory(f"夜晚决定守护 {target} 号玩家")
        
        return {"action": "guard", "target": target}
    
    async def speak(self, context: Dict[str, Any]) -> str:
        """
        白天发言
        
        Args:
            context: 发言上下文
        """
        game_info = context.get("game_info", {})
        day_phase = context.get("day_phase", "discussion")  # discussion, accusation, defense, last_words
        
        if day_phase == "discussion":
            # 讨论阶段：观察局势，分析谁可能需要保护
            prompt = f"""你是{self.name}（守卫），正在白天讨论阶段。
当前存活玩家：{game_info.get('alive_players', [])}
请观察其他玩家的发言和行为，分析谁可能成为狼人的目标。
作为守卫，你需要留意那些可能需要保护的玩家。"""
            
        elif day_phase == "accusation":
            # 指认阶段：根据观察指认狼人
            prompt = f"""你是{self.name}（守卫），正在指认阶段。
当前存活玩家：{game_info.get('alive_players', [])}
请根据你的观察和分析，指认你认为最像狼人的玩家，并说明理由。
注意不要暴露你的守卫身份。"""
                
        elif day_phase == "defense":
            # 辩护阶段：如果被指认，则为自己辩护
            accused_by = context.get("accused_by", [])
            if self.player_id in [item.get('target') for item in accused_by]:
                prompt = f"""你是{self.name}（守卫），正在被其他玩家怀疑。
请为自己辩护，强调你的好人身份。
注意不要因为过度辩护而暴露你的守卫身份。"""
            else:
                prompt = f"""你是{self.name}（守卫），目前没有被怀疑。
请继续观察局势，支持好人阵营。"""
                
        elif day_phase == "last_words":
            # 遗言阶段：分享重要信息
            guarded_info = context.get("guarded_info", {})
            
            prompt = f"""你是{self.name}（守卫），即将死亡，发表遗言。
你最近守护的玩家信息：{guarded_info}
请分享你的观察和分析，提醒好人阵营注意某些玩家。
这是你最后一次帮助好人阵营的机会。"""
        else:
            prompt = f"""你是{self.name}（守卫），请根据当前局势发表合适的言论。"""
        
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
        
        # 守卫投票策略：基于观察和分析选择最像狼人的目标
        prompt = f"""你是{self.name}（守卫），正在进行投票。
候选人：{candidates}
请根据你的观察和分析，选择你认为最可能是狼人的玩家进行投票。
记住不要因为投票过于精准而暴露你的守卫身份。"""
        
        response = await self.llm_service.generate_response(prompt)
        
        # 解析响应，尝试找到候选人ID
        for candidate in candidates:
            if str(candidate) in response:
                self.add_memory(f"投票给 {candidate} 号玩家")
                return candidate
        
        # 如果无法确定，返回None（弃票）
        return None