"""三国杀全局看板 UI"""
from typing import Optional, Any, TYPE_CHECKING
from ui.base import UIBase

if TYPE_CHECKING:
    from games.threekingdoms.state import ThreeKingdomsPlayer


class ThreeKingdomsCLI(UIBase):
    """三国杀命令行界面 - 带全局看板"""

    def __init__(self, show_inner_thoughts: bool = False, god_view: bool = True):
        """
        Args:
            show_inner_thoughts: 是否显示内心独白
            god_view: 是否开启上帝视角
        """
        self.show_inner_thoughts = show_inner_thoughts
        self.god_view = god_view
        self.thought_history: list[dict] = []  # AI 思考历史
        self.game_state = None
        self.human_player_id: Optional[int] = None

    def set_game_state(self, players: dict, human_player_id: Optional[int] = None) -> None:
        """设置游戏状态"""
        self.game_state = players
        self.human_player_id = human_player_id

    def _format_speaker_name(self, speaker: str) -> str:
        """格式化发言者名字（添加名人名字和身份）"""
        if not self.game_state:
            return speaker
        
        try:
            player_id = int(speaker.split("号")[0])
            player = self.game_state.get(player_id)
            
            if not player:
                return speaker
            
            # 构建名字
            celebrity_name = getattr(player, 'celebrity_name', '')
            if celebrity_name:
                name_with_celebrity = f"{player.name}({celebrity_name})"
            else:
                name_with_celebrity = player.name
            
            # 上帝视角显示身份
            if self.god_view:
                if self.human_player_id is not None and player_id != self.human_player_id:
                    return name_with_celebrity
                
                role = getattr(player, 'role', None)
                if role:
                    role_name = role.value if hasattr(role, 'value') else str(role)
                    return f"{name_with_celebrity}-{role_name}"
            
            return name_with_celebrity
            
        except (ValueError, IndexError, AttributeError):
            pass
        
        return speaker

    def display_message(self, speaker: str, message: str) -> None:
        display_name = self._format_speaker_name(speaker)
        print(f"\n[{display_name}] {message}")
    
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
            "turn_start": "[回合开始]",
            "game_over": "[游戏结束]",
        }
        msg = event_messages.get(event_type, event_type)
        print(f"\n=== {msg} ===")
        if data:
            for k, v in data.items():
                print(f"   {k}: {v}")
    
    def display_system_message(self, message: str) -> None:
        print(f"\n[系统] {message}")
    
    def update_game_board(self, players: list[dict], deck_count: int, 
                         discard_count: int, current_player_id: int) -> None:
        """
        更新全局看板
        
        Args:
            players: 玩家状态列表
            deck_count: 牌堆数量
            discard_count: 弃牌堆数量
            current_player_id: 当前回合玩家 ID
        """
        board = "\n" + "=" * 70 + "\n"
        board += f"当前回合：{current_player_id}号  |  牌堆：{deck_count}张  |  弃牌堆：{discard_count}张\n"
        board += "=" * 70 + "\n"
        
        # 玩家信息（线性布局）
        for p in players:
            if not p.get("is_alive", True):
                continue
            
            hp_display = "●" * p.get("hp", 0) + "○" * (p.get("max_hp", 4) - p.get("hp", 4))
            hand_cards = p.get("hand_cards", [])
            hand_str = ", ".join([c.get("name", "?") for c in hand_cards]) if hand_cards else "无"
            
            highlight = ">>> 当前回合 <<<" if p.get("id") == current_player_id else ""
            
            board += f"\n[{p.get('id')}号 - {p.get('general')} - {p.get('role', '?')}]\n"
            board += f"  HP: {hp_display} ({p.get('hp')}/{p.get('max_hp')})\n"
            board += f"  手牌：{len(hand_cards)}张 [{hand_str}]\n"
            
            equipped = p.get("equipped", {})
            if equipped.get("weapon"):
                board += f"  武器：{equipped['weapon']}\n"
            if equipped.get("armor"):
                board += f"  防具：{equipped['armor']}\n"
            if equipped.get("horse_minus") or equipped.get("horse_plus"):
                board += f"  马：{equipped.get('horse_minus', '')} {equipped.get('horse_plus', '')}\n"
            
            if highlight:
                board += f"  {highlight}\n"
        
        board += "\n" + "=" * 70 + "\n"
        
        # AI 思考过程（可折叠）
        if self.thought_history:
            board += "\n【AI 思考过程】▼ (最近 3 条)\n"
            for thought in self.thought_history[-3:]:
                board += f"  [{thought.get('player')}] {thought.get('time')}\n"
                board += f"    {thought.get('decision')}\n"
            board += "\n  ▶ 输入 'thought' 查看详细历史\n"
        
        board += "\n" + "=" * 70 + "\n"
        
        print(board)
    
    def show_ai_thought(self, player_id: int, player_name: str, phase: str,
                       reasoning: str, decision: str, confidence: float) -> None:
        """
        显示 AI 思考过程
        
        Args:
            player_id: 玩家 ID
            player_name: 玩家名称
            phase: 阶段
            reasoning: 推理过程
            decision: 最终决定
            confidence: 置信度
        """
        from datetime import datetime
        thought = {
            "player_id": player_id,
            "player": f"{player_id}号 - {player_name}",
            "time": datetime.now().strftime("%H:%M:%S"),
            "phase": phase,
            "reasoning": reasoning,
            "decision": decision,
            "confidence": confidence,
        }
        
        self.thought_history.append(thought)
        
        # 限制历史记录数量
        if len(self.thought_history) > 50:
            self.thought_history = self.thought_history[-50:]
        
        # 显示最新思考（可折叠）
        print(f"\n[AI 思考 - {player_name}]")
        print(f"  阶段：{phase}")
        print(f"  决策：{decision} (置信度：{confidence*100:.0f}%)")
        # reasoning 默认不显示，需要时展开
    
    def show_thought_history(self) -> None:
        """显示完整 AI 思考历史"""
        if not self.thought_history:
            print("\n暂无思考历史")
            return
        
        print("\n" + "=" * 70)
        print("【AI 思考历史】")
        print("=" * 70)
        
        for i, thought in enumerate(self.thought_history[-10:], 1):  # 显示最近 10 条
            print(f"\n{i}. [{thought.get('player')}] {thought.get('time')} - {thought.get('phase')}")
            print(f"   决策：{thought.get('decision')}")
            print(f"   推理：{thought.get('reasoning')}")
            print(f"   置信度：{thought.get('confidence', 0)*100:.0f}%")
        
        print("\n" + "=" * 70)
    
    def select_player_mode(self) -> tuple[bool, Optional[int]]:
        """选择游戏模式"""
        print("\n" + "=" * 40)
        print("请选择游戏模式：")
        print("1. 观察模式（只看 AI 互斗）")
        print("2. 玩家模式（亲自下场）")
        print("=" * 40)
        
        choice = self.get_player_input("输入选项 (1/2): ")
        
        if choice == "2":
            player_count = 5  # 三国杀默认 5 人
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
