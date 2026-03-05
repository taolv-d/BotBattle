"""测试上帝视角显示身份功能"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.state import GameState, Player, Role
from ui.cli import CLI


def test_god_view():
    """测试上帝视角显示"""
    print("=" * 60)
    print("测试上帝视角显示身份功能")
    print("=" * 60)
    
    # 创建游戏状态
    state = GameState()
    state.player_count = 6
    
    # 创建测试玩家
    roles = [Role.WEREWOLF, Role.SEER, Role.WITCH, Role.VILLAGER, Role.HUNTER, Role.WEREWOLF]
    for i in range(1, 7):
        player = Player(
            id=i,
            name=f"{i}号玩家",
            role=roles[i-1],
            is_alive=True,
        )
        state.players[i] = player
    
    # 测试 1：观察模式（上帝视角，显示所有身份）
    print("\n【测试 1】观察模式（显示所有玩家身份）")
    print("-" * 60)
    ui_god = CLI(god_view=True)
    ui_god.set_game_state(state, human_player_id=None)
    
    for i in range(1, 7):
        ui_god.display_message(f"{i}号玩家", "我是好人，大家相信我。")
    
    # 测试 2：玩家模式（只显示自己身份）
    print("\n【测试 2】玩家模式（人类玩家是 3 号，只显示自己身份）")
    print("-" * 60)
    ui_player = CLI(god_view=True)
    ui_player.set_game_state(state, human_player_id=3)
    
    for i in range(1, 7):
        ui_player.display_message(f"{i}号玩家", "我是好人，大家相信我。")
    
    # 测试 3：关闭上帝视角
    print("\n【测试 3】关闭上帝视角（不显示任何身份）")
    print("-" * 60)
    ui_no_god = CLI(god_view=False)
    ui_no_god.set_game_state(state, human_player_id=None)
    
    for i in range(1, 7):
        ui_no_god.display_message(f"{i}号玩家", "我是好人，大家相信我。")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_god_view()
