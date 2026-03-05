"""命令行界面实现"""
from typing import Optional
from .base import UIBase


class CLI(UIBase):
    """命令行界面"""

    def __init__(self, show_inner_thoughts: bool = False):
        """
        Args:
            show_inner_thoughts: 是否显示内心独白（默认不显示，避免界面杂乱）
        """
        self.show_inner_thoughts = show_inner_thoughts

    def display_message(self, speaker: str, message: str) -> None:
        print(f"\n[{speaker}] {message}")

    def display_inner_thought(self, speaker: str, thought: str) -> None:
        """内心独白写入日志，终端默认不显示"""
        if self.show_inner_thoughts:
            print(f"  -> ({speaker} 的内心独白：{thought})")

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
