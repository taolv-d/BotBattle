from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from ..config import Role
from services.llm_service import LLMService


class MemoryType(Enum):
    """记忆类型枚举"""
    SPEECH = "speech"              # 发言
    VOTE = "vote"                  # 投票
    NIGHT_ACTION = "night_action"  # 夜晚行动
    OBSERVATION = "observation"    # 观察
    DEATH = "death"                # 死亡事件
    ELECTION = "election"          # 警长竞选
    LAST_WORDS = "last_words"      # 遗言
    SYSTEM = "system"              # 系统消息


@dataclass
class MemoryEntry:
    """
    结构化记忆条目

    包含记忆类型、内容、时间戳和相关玩家 ID
    """
    memory_type: MemoryType
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    related_player_id: Optional[int] = None  # 相关玩家 ID（如投票目标、被查验玩家等）
    day_number: Optional[int] = None         # 游戏天数
    night_number: Optional[int] = None       # 游戏夜晚数
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "type": self.memory_type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "related_player_id": self.related_player_id,
            "day_number": self.day_number,
            "night_number": self.night_number,
            "metadata": self.metadata
        }

    def __str__(self) -> str:
        """字符串表示"""
        time_str = self.timestamp.strftime("%H:%M:%S")
        day_info = f"第{self.day_number}天" if self.day_number else ""
        night_info = f"第{self.night_number}夜" if self.night_number else ""
        phase_info = f"{day_info}{night_info}" if day_info or night_info else ""

        return f"[{time_str}][{self.memory_type.value}]{phase_info}: {self.content}"


class WerewolfAgent(ABC):
    """
    狼人杀 Agent 基类

    定义所有角色 Agent 的通用接口
    """

    def __init__(self, player_id: int, name: str, role: Role, personality: str, llm_service: LLMService):
        """
        初始化 Agent

        Args:
            player_id: 玩家 ID
            name: 玩家名称
            role: 玩家角色
            personality: 人格特质
            llm_service: LLM 服务实例
        """
        self.player_id = player_id
        self.name = name
        self.role = role
        self.personality = personality
        self.llm_service = llm_service

        # Agent 状态
        self.knowledge = {}  # 存储已知信息
        self.memory: List[MemoryEntry] = []  # 结构化记忆存储
        self._raw_memory: List[str] = []     # 原始记忆存储（向后兼容）

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
            投票目标 ID，None 表示弃票
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

    def add_memory(self, content: str, memory_type: MemoryType = MemoryType.OBSERVATION,
                   related_player_id: Optional[int] = None, day_number: Optional[int] = None,
                   night_number: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None):
        """
        添加结构化记忆

        Args:
            content: 记忆内容
            memory_type: 记忆类型（默认为观察）
            related_player_id: 相关玩家 ID
            day_number: 游戏天数
            night_number: 游戏夜晚数
            metadata: 额外元数据
        """
        entry = MemoryEntry(
            memory_type=memory_type,
            content=content,
            related_player_id=related_player_id,
            day_number=day_number,
            night_number=night_number,
            metadata=metadata or {}
        )
        self.memory.append(entry)

        # 同时保存原始记忆（向后兼容）
        self._raw_memory.append(content)

        # 限制记忆长度，避免无限增长
        max_memory = 100
        if len(self.memory) > max_memory:
            self.memory = self.memory[-max_memory:]
        if len(self._raw_memory) > max_memory:
            self._raw_memory = self._raw_memory[-max_memory:]

    def add_speech_memory(self, content: str, day_number: Optional[int] = None):
        """添加发言记忆"""
        self.add_memory(content, MemoryType.SPEECH, day_number=day_number)

    def add_vote_memory(self, target_id: int, day_number: Optional[int] = None):
        """添加投票记忆"""
        self.add_memory(f"投票给 {target_id} 号玩家", MemoryType.VOTE,
                       related_player_id=target_id, day_number=day_number)

    def add_night_action_memory(self, content: str, night_number: Optional[int] = None,
                                target_id: Optional[int] = None):
        """添加夜晚行动记忆"""
        self.add_memory(content, MemoryType.NIGHT_ACTION,
                       related_player_id=target_id, night_number=night_number)

    def add_observation_memory(self, content: str, day_number: Optional[int] = None,
                               night_number: Optional[int] = None):
        """添加观察记忆"""
        self.add_memory(content, MemoryType.OBSERVATION,
                       day_number=day_number, night_number=night_number)

    def add_death_memory(self, player_id: int, cause: str, day_number: Optional[int] = None,
                         night_number: Optional[int] = None):
        """添加死亡事件记忆"""
        self.add_memory(f"{player_id} 号玩家死亡，原因：{cause}", MemoryType.DEATH,
                       related_player_id=player_id, day_number=day_number,
                       night_number=night_number)

    def get_memories_by_type(self, memory_type: MemoryType) -> List[MemoryEntry]:
        """
        获取特定类型的记忆

        Args:
            memory_type: 记忆类型

        Returns:
            该类型的记忆列表
        """
        return [m for m in self.memory if m.memory_type == memory_type]

    def get_memories_by_day(self, day_number: int) -> List[MemoryEntry]:
        """
        获取特定天数的记忆

        Args:
            day_number: 游戏天数

        Returns:
            该天数的记忆列表
        """
        return [m for m in self.memory if m.day_number == day_number]

    def get_memories_by_night(self, night_number: int) -> List[MemoryEntry]:
        """
        获取特定夜晚的记忆

        Args:
            night_number: 游戏夜晚数

        Returns:
            该夜晚的记忆列表
        """
        return [m for m in self.memory if m.night_number == night_number]

    def get_memory_summary(self, limit: int = 20) -> str:
        """
        获取记忆摘要

        Args:
            limit: 最大记忆条数

        Returns:
            记忆摘要字符串
        """
        recent_memories = self.memory[-limit:] if len(self.memory) > limit else self.memory
        return "\n".join(str(m) for m in recent_memories)

    def get_speech_history(self, limit: int = 10) -> List[str]:
        """
        获取发言历史

        Args:
            limit: 最大条数

        Returns:
            发言内容列表
        """
        speeches = self.get_memories_by_type(MemoryType.SPEECH)
        return [m.content for m in speeches[-limit:]]

    def get_vote_history(self) -> Dict[int, int]:
        """
        获取投票历史

        Returns:
            投票历史字典 {天数：投票目标 ID}
        """
        votes = self.get_memories_by_type(MemoryType.VOTE)
        return {m.day_number: m.related_player_id for m in votes if m.day_number and m.related_player_id}

    async def decide_to_run_president(self) -> bool:
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
        prompt = f"""你是{self.name}（{self.role.value}），正在参与警长竞选。

【游戏状态】
- 当前是第 1 天白天，警长竞选阶段
- 还没有进行任何夜晚行动（没有查验、没有死亡、没有用药）
- 所有玩家都还存活

请发表一段竞选演讲，展示你的能力和领导意愿。
**注意**：不要提及任何夜晚行动的结果（如查验、死亡等），因为还没有进行过夜晚行动。"""
        return await self.llm_service.generate_response(prompt)

    async def vote_for_president(self, candidates: List[int]) -> Optional[int]:
        """
        为警长投票

        Args:
            candidates: 候选人列表

        Returns:
            投票目标 ID，None 表示弃票
        """
        if not candidates:
            return None

        prompt = f"""你是{self.name}（{self.role.value}），现在进行警长竞选投票。

【游戏状态】
- 当前是第 1 天白天，警长竞选阶段
- 还没有进行任何夜晚行动（没有查验、没有死亡、没有用药）
- 所有玩家都还存活

候选人 ID 列表：{candidates}
请根据候选人的竞选发言进行分析，决定你要投给哪位候选人（返回一个候选人 ID）或弃票（返回 null）。
**注意**：不要提及任何夜晚行动的结果（如查验、死亡等），因为还没有进行过夜晚行动。只能根据竞选发言内容和个人判断进行投票。
你目前知道的信息：{self.knowledge}"""

        response = await self.llm_service.generate_response(prompt)

        # 解析响应，尝试找到候选人 ID
        for candidate in candidates:
            if str(candidate) in response:
                return candidate

        # 如果无法确定，随机选择
        import random
        return random.choice(candidates) if candidates else None

    async def pk_speech(self) -> str:
        """
        平票 PK 发言

        Returns:
            PK 发言内容
        """
        prompt = f"你是{self.name}（{self.role.value}），现在进行警长竞选平票 PK，请发表一段争取选票的发言。"
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
            开枪目标 ID，None 表示不开枪
        """
        alive_players = context.get("alive_players", [])
        if not alive_players:
            return None

        prompt = f"""你是{self.name}（猎人），即将死亡。
场上存活玩家 ID：{alive_players}
请决定是否开枪及开枪目标（返回玩家 ID）或不开枪（返回 null）。
你目前知道的信息：{self.knowledge}"""

        response = await self.llm_service.generate_response(prompt)

        # 解析响应，尝试找到目标 ID
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
