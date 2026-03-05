"""命令行界面实现"""
from typing import Optional, TYPE_CHECKING
from .base import UIBase

# 避免循环导入，仅在类型检查时导入
if TYPE_CHECKING:
    from core.state import GameState


class CLI(UIBase):
    """命令行界面 - 支持上帝视角显示身份"""

    def __init__(self, show_inner_thoughts: bool = False, god_view: bool = True):
        """
        Args:
            show_inner_thoughts: 是否显示内心独白（默认不显示，避免界面杂乱）
            god_view: 是否开启上帝视角（显示所有玩家身份）
        """
        self.show_inner_thoughts = show_inner_thoughts
        self.god_view = god_view
        self.game_state: Optional["GameState"] = None
        self.human_player_id: Optional[int] = None

    def set_game_state(self, game_state: "GameState", human_player_id: Optional[int] = None) -> None:
        """
        设置游戏状态（用于获取玩家身份信息）

        Args:
            game_state: 游戏状态对象
            human_player_id: 人类玩家 ID（None 表示观察模式）
        """
        self.game_state = game_state
        self.human_player_id = human_player_id

    def _format_speaker_name(self, speaker: str) -> str:
        """
        格式化发言者名字（添加身份和名人名字）

        Args:
            speaker: 原始发言者名字，如 "7 号玩家"

        Returns:
            格式化后的名字，如 "7 号玩家 (诸葛亮)- 预言家"
        """
        if not self.game_state:
            return speaker

        # 从 "7 号玩家" 中提取玩家 ID
        try:
            player_id = int(speaker.split("号")[0])
            player = self.game_state.players.get(player_id)
            
            if not player:
                return speaker
            
            # 构建名字部分
            if player.celebrity_name:
                name_with_celebrity = f"{player.name}({player.celebrity_name})"
            else:
                name_with_celebrity = player.name
            
            # 添加身份（上帝视角）
            if self.god_view:
                # 人类玩家只能看到自己的身份
                if self.human_player_id is not None and player_id != self.human_player_id:
                    return name_with_celebrity
                
                if player.role:
                    role_map = {
                        "werewolf": "狼人",
                        "villager": "村民",
                        "seer": "预言家",
                        "witch": "女巫",
                        "hunter": "猎人",
                    }
                    role_name = role_map.get(player.role.value, player.role.value)
                    return f"{name_with_celebrity}-{role_name}"
            
            return name_with_celebrity
            
        except (ValueError, IndexError):
            pass

        return speaker

    def display_message(self, speaker: str, message: str) -> None:
        display_name = self._format_speaker_name(speaker)
        print(f"\n[{display_name}] {message}")

    def display_inner_thought(self, speaker: str, thought: str) -> None:
        """
        显示内心独白（上帝视角可见）
        
        Args:
            speaker: 发言者
            thought: 内心独白内容
        """
        # 上帝视角或明确要显示内心独白时才显示
        if self.god_view or self.show_inner_thoughts:
            if thought:  # 只有非空内容才显示
                print(f"  [{speaker} 的内心] {thought}")

    def get_player_input(self, prompt: str) -> str:
        try:
            return input(f"\n{prompt}").strip()
        except (EOFError, KeyboardInterrupt):
            return ""

    def notify_game_event(self, event_type: str, data: dict) -> None:
        event_messages = {
            "game_start": "[游戏开始]",
            "night_start": "[夜晚降临]",
            "day_start": "[天亮了]",
            "vote_result": "[投票结果]",
            "player_eliminated": "[玩家被放逐]",
            "player_died": "[玩家死亡]",
            "game_over": "[游戏结束]",
            "role_reveal": "[角色揭晓]",
        }
        msg = event_messages.get(event_type, event_type)
        print(f"\n=== {msg} ===")
        if data:
            for k, v in data.items():
                print(f"   {k}: {v}")

    def display_system_message(self, message: str) -> None:
        print(f"\n[系统] {message}")

    def select_player_mode(self) -> tuple[bool, Optional[int]]:
        """
        选择游戏模式
        Returns:
            (是否玩家模式，玩家编号)
        """
        print("\n" + "="*40)
        print("请选择游戏模式：")
        print("1. 观察模式（只看 AI 互斗）")
        print("2. 玩家模式（亲自下场）")
        print("="*40)

        choice = self.get_player_input("输入选项 (1/2): ")

        if choice == "2":
            player_count = 9  # 默认 9 人，后续可从配置读取
            while True:
                pid = self.get_player_input(f"选择你要扮演的玩家编号 (1-{player_count}): ")
                try:
                    player_id = int(pid)
                    if 1 <= player_id <= player_count:
                        return True, player_id
                except ValueError:
                    pass
                print("无效输入，请重新选择")
        return False, None
