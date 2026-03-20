from typing import List, Dict, Any, Optional
from services.logger_service import LoggerService


class WerewolfGroupChat:
    """
    狼人杀群聊封装类（简化版，不依赖 AutoGen）

    注意：此类在当前实现中仅用于占位，实际游戏逻辑通过直接调用
    各个 Agent 的方法（如 speak()、vote()、night_action()）来完成，
    不使用群聊功能。
    """

    def __init__(self, agents: List[object], logger: LoggerService, config_list: List[Dict[str, Any]]):
        """
        初始化群聊

        Args:
            agents: 玩家 Agent 列表
            logger: 日志服务实例
            config_list: LLM 配置列表（未使用）
        """
        self.agents = agents
        self.logger = logger
        self.config_list = config_list
        self.messages: List[Dict[str, Any]] = []  # 聊天历史

        # 记录初始化
        self.logger.info(f"WerewolfGroupChat 已初始化，包含 {len(agents)} 个 Agent")

    async def start_discussion(self, topic: str, participants: Optional[List[object]] = None) -> Dict[str, Any]:
        """
        开始讨论（占位实现，未实际使用）

        Args:
            topic: 讨论主题
            participants: 参与讨论的 Agent 列表，默认为所有 Agent

        Returns:
            讨论结果
        """
        if participants is None:
            participants = self.agents

        self.logger.info(f"开始讨论：{topic}（占位实现，未实际使用）")

        # 添加话题到消息历史
        self.messages.append({
            "name": "Moderator",
            "content": f"现在开始讨论：{topic}",
            "role": "user"
        })

        return {
            "success": True,
            "messages": self.messages.copy(),
            "summary": f"讨论主题：{topic}（占位实现）"
        }

    async def broadcast_message(self, message: str, sender_id: Optional[int] = None):
        """
        广播消息给所有参与者

        Args:
            message: 消息内容
            sender_id: 发送者 ID
        """
        self.logger.info(f"广播消息：{message}")

        # 将消息添加到聊天历史
        msg_obj = {
            "name": f"System-{sender_id}" if sender_id else "System",
            "content": message,
            "role": "user"
        }
        self.messages.append(msg_obj)

    def get_participants(self) -> List[object]:
        """
        获取参与者列表

        Returns:
            参与者 Agent 列表
        """
        return self.agents

    def add_participant(self, agent: object):
        """
        添加参与者

        Args:
            agent: 要添加的 Agent
        """
        if agent not in self.agents:
            self.agents.append(agent)
            agent_name = getattr(agent, 'name', str(agent))
            self.logger.info(f"添加参与者：{agent_name}")

    def remove_participant(self, agent: object):
        """
        移除参与者

        Args:
            agent: 要移除的 Agent
        """
        if agent in self.agents:
            self.agents.remove(agent)
            agent_name = getattr(agent, 'name', str(agent))
            self.logger.info(f"移除参与者：{agent_name}")

    def reset_chat_history(self):
        """
        重置聊天历史
        """
        self.messages.clear()
        self.logger.info("重置聊天历史")
