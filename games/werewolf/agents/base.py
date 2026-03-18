from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from ..config import Role
from services.llm_service import LLMService


class WerewolfAgent(ABC):
    """
    狼人杀 Agent 基类
    
    定义所有角色 Agent 的通用接口
    """
    
    def __init__(self, player_id: int, name: str, role: Role, personality: str, llm_service: LLMService):
        """
        初始化 Agent
        
        Args:
            player_id: 玩家ID
            name: 玩家名称
            role: 玩家角色
            personality: 人格特质
            llm_service: LLM服务实例
        """
        self.player_id = player_id
        self.name = name
        self.role = role
        self.personality = personality
        self.llm_service = llm_service
        
        # Agent 状态
        self.knowledge = {}  # 存储已知信息
        self.memory = []     # 存储记忆
    
    @abstractmethod
    async def night_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        夜晚行动
        
        Args:
            context: 夜晚行动上下文
            
        Returns:
            行动结果字典
        """
        pass
    
    @abstractmethod
    async def speak(self, context: Dict[str, Any]) -> str:
        """
        白天发言
        
        Args:
            context: 发言上下文
            
        Returns:
            发言内容
        """
        pass
    
    @abstractmethod
    async def vote(self, context: Dict[str, Any]) -> Optional[int]:
        """
        投票
        
        Args:
            context: 投票上下文
            
        Returns:
            投票目标ID，None表示弃票
        """
        pass
    
    async def think(self, thought_prompt: str) -> str:
        """
        思考过程
        
        Args:
            thought_prompt: 思考提示
            
        Returns:
            思考结果
        """
        prompt = f"你是{self.name}（{self.role.value}），你的性格是{self.personality}。\n\n{thought_prompt}"
        return await self.llm_service.generate_response(prompt)
    
    def update_knowledge(self, key: str, value: Any):
        """
        更新知识库
        
        Args:
            key: 知识键
            value: 知识值
        """
        self.knowledge[key] = value
    
    def get_knowledge(self, key: str, default: Any = None) -> Any:
        """
        获取知识
        
        Args:
            key: 知识键
            default: 默认值
            
        Returns:
            知识值
        """
        return self.knowledge.get(key, default)
    
    def add_memory(self, memory: str):
        """
        添加记忆
        
        Args:
            memory: 记忆内容
        """
        self.memory.append(memory)
        # 限制记忆长度，避免无限增长
        if len(self.memory) > 50:
            self.memory = self.memory[-50:]
    
    def decide_to_run_president(self) -> bool:
        """
        决定是否参与警长竞选
        
        Returns:
            是否参选
        """
        # 默认实现：神职更倾向于参选
        return self.role in [Role.SEER, Role.WITCH, Role.HUNTER, Role.GUARD]
    
    async def president_speech(self) -> str:
        """
        警长竞选发言
        
        Returns:
            竞选发言内容
        """
        prompt = f"你是{self.name}（{self.role.value}），正在参与警长竞选。请发表一段竞选演讲，展示你的能力和领导意愿。"
        return await self.llm_service.generate_response(prompt)
    
    async def vote_for_president(self, candidates: List[int]) -> Optional[int]:
        """
        为警长投票
        
        Args:
            candidates: 候选人列表
            
        Returns:
            投票目标ID，None表示弃票
        """
        if not candidates:
            return None
        
        prompt = f"""你是{self.name}（{self.role.value}），现在进行警长竞选投票。
候选人ID列表：{candidates}
请分析并决定你要投给哪位候选人（返回一个候选人ID）或弃票（返回null）。
你目前知道的信息：{self.knowledge}"""
        
        response = await self.llm_service.generate_response(prompt)
        
        # 解析响应，尝试找到候选人ID
        for candidate in candidates:
            if str(candidate) in response:
                return candidate
        
        # 如果无法确定，随机选择
        import random
        return random.choice(candidates) if candidates else None
    
    async def pk_speech(self) -> str:
        """
        平票PK发言
        
        Returns:
            PK发言内容
        """
        prompt = f"你是{self.name}（{self.role.value}），现在进行警长竞选平票PK，请发表一段争取选票的发言。"
        return await self.llm_service.generate_response(prompt)
    
    async def make_last_words(self) -> str:
        """
        发表遗言
        
        Returns:
            遗言内容
        """
        prompt = f"你是{self.name}（{self.role.value}），即将死亡，请发表遗言。你可以透露一些信息或表达最后的想法。"
        return await self.llm_service.generate_response(prompt)
    
    async def hunter_skill(self, context: Dict[str, Any]) -> Optional[int]:
        """
        猎人技能发动
        
        Args:
            context: 技能上下文
            
        Returns:
            开枪目标ID，None表示不开枪
        """
        alive_players = context.get("alive_players", [])
        if not alive_players:
            return None
        
        prompt = f"""你是{self.name}（猎人），即将死亡。
场上存活玩家ID：{alive_players}
请决定是否开枪及开枪目标（返回玩家ID）或不开枪（返回null）。
你目前知道的信息：{self.knowledge}"""
        
        response = await self.llm_service.generate_response(prompt)
        
        # 解析响应，尝试找到目标ID
        for player_id in alive_players:
            if str(player_id) in response:
                return player_id
        
        # 如果无法确定，随机选择
        import random
        return random.choice(alive_players) if alive_players else None
    
    async def choose_direction(self) -> str:
        """
        选择发言方向（仅警长使用）
        
        Returns:
            "left" 或 "right"
        """
        prompt = f"你是{self.name}（警长），请选择发言顺序方向：左置位（从警长开始向左发言）或右置位（从警长开始向右发言）。请回答'left'或'right'。"
        response = await self.llm_service.generate_response(prompt)
        
        if "left" in response.lower():
            return "left"
        else:
            return "right"