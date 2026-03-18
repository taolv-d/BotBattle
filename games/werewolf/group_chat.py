from typing import List, Dict, Any, Optional
import asyncio
from autogen import GroupChat, GroupChatManager
from services.logger_service import LoggerService


class WerewolfGroupChat:
    """
    狼人杀群聊封装类
    
    基于 AutoGen 的群聊系统，用于管理玩家之间的对话
    """
    
    def __init__(self, agents: List[object], logger: LoggerService, config_list: List[Dict[str, Any]]):
        """
        初始化群聊
        
        Args:
            agents: 玩家 Agent 列表
            logger: 日志服务实例
            config_list: LLM 配置列表
        """
        self.agents = agents
        self.logger = logger
        self.config_list = config_list
        
        # 创建 AutoGen 群聊
        self.group_chat = GroupChat(
            agents=agents,
            messages=[],
            max_round=50  # 最大对话轮数
        )
        
        # 创建群聊管理器
        self.manager = GroupChatManager(
            groupchat=self.group_chat,
            llm_config={
                "config_list": self.config_list,
            },
            is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0
        )
    
    async def start_discussion(self, topic: str, participants: Optional[List[object]] = None) -> Dict[str, Any]:
        """
        开始讨论
        
        Args:
            topic: 讨论主题
            participants: 参与讨论的 Agent 列表，默认为所有 Agent
            
        Returns:
            讨论结果
        """
        if participants is None:
            participants = self.agents
        
        # 记录讨论开始
        self.logger.info(f"开始讨论: {topic}")
        
        # 初始化群聊消息
        self.group_chat.messages = []
        
        # 添加初始话题
        initial_message = {
            "name": "Moderator",
            "content": f"现在开始讨论: {topic}",
            "role": "user"
        }
        self.group_chat.messages.append(initial_message)
        
        # 异步运行群聊
        try:
            # 使用 asyncio 运行群聊
            result = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.manager.initiate_chat(
                    self.manager,
                    message=f"现在开始讨论: {topic}",
                    summary_method="last_msg"
                )
            )
            
            # 记录讨论结果
            self.logger.info(f"讨论结束: {topic}")
            
            return {
                "success": True,
                "messages": self.group_chat.messages,
                "summary": result.summary if hasattr(result, 'summary') else "No summary available"
            }
        except Exception as e:
            self.logger.error(f"讨论出错: {e}")
            return {
                "success": False,
                "error": str(e),
                "messages": self.group_chat.messages
            }
    
    async def broadcast_message(self, message: str, sender_id: Optional[int] = None):
        """
        广播消息给所有参与者
        
        Args:
            message: 消息内容
            sender_id: 发送者ID
        """
        self.logger.info(f"广播消息: {message}")
        
        # 将消息添加到群聊历史
        msg_obj = {
            "name": f"System-{sender_id}" if sender_id else "System",
            "content": message,
            "role": "user"
        }
        self.group_chat.messages.append(msg_obj)
    
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
            self.logger.info(f"添加参与者: {agent.name}")
    
    def remove_participant(self, agent: object):
        """
        移除参与者
        
        Args:
            agent: 要移除的 Agent
        """
        if agent in self.agents:
            self.agents.remove(agent)
            self.logger.info(f"移除参与者: {agent.name}")
    
    def reset_chat_history(self):
        """
        重置聊天历史
        """
        self.group_chat.messages = []
        self.logger.info("重置聊天历史")