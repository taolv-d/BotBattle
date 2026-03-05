"""UI 基类接口 - 方便后续扩展 Web UI"""
from abc import ABC, abstractmethod
from typing import Optional


class UIBase(ABC):
    """UI 基类"""
    
    @abstractmethod
    def display_message(self, speaker: str, message: str) -> None:
        """显示发言消息"""
        pass
    
    @abstractmethod
    def display_inner_thought(self, speaker: str, thought: str) -> None:
        """显示内心独白（可选，观察者模式可能不显示）"""
        pass
    
    @abstractmethod
    def get_player_input(self, prompt: str) -> str:
        """获取玩家输入"""
        pass
    
    @abstractmethod
    def notify_game_event(self, event_type: str, data: dict) -> None:
        """通知游戏事件"""
        pass
    
    @abstractmethod
    def display_system_message(self, message: str) -> None:
        """显示系统消息"""
        pass
