from .base import WerewolfAgent
from ..config import Role
from typing import Dict, Any, Optional
import random


class WolfAgent(WerewolfAgent):
    """
    狼人 Agent
    """
    
    def __init__(self, player_id: int, name: str, personality: str, llm_service: object):
        super().__init__(player_id, name, Role.WEREWOLF, personality, llm_service)
        self.wolf_teammates = []  # 狼人队友列表
    
    async def night_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        狼人夜晚行动：选择击杀目标
        
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
            # 没有可击杀的目标
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