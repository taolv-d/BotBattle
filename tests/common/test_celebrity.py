"""测试名人名字功能"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.state import GameState, Player, Role
from ui.cli import CLI
from ai.names import NameGenerator


def test_celebrity_names():
    """测试名人名字显示"""
    print("=" * 70)
    print("测试名人名字功能")
    print("=" * 70)
    
    # 创建名字生成器
    name_gen = NameGenerator()
    
    # 测试不同人格的名字分配
    personalities = ["honest", "liar", "smooth", "cold", "chatterbox", "aggressive", "passive"]
    
    print("\n【人格与名人名字对应关系】")
    print("-" * 70)
    for person in personalities:
        name = name_gen.get_name_for_personality(person)
        print(f"  {person:12} -> {name}")
    
    # 创建游戏状态
    state = GameState()
    state.player_count = 7
    
    # 创建测试玩家（带名人名字）
    roles = [Role.WEREWOLF, Role.SEER, Role.WITCH, Role.VILLAGER, Role.HUNTER, Role.WEREWOLF, Role.VILLAGER]
    for i in range(1, 8):
        player = Player(
            id=i,
            name=f"{i}号玩家",
            role=roles[i-1],
            personality=personalities[i-1],
            is_alive=True,
        )
        # 分配名人名字
        player.celebrity_name = name_gen.assign_name_to_player(i, personalities[i-1])
        state.players[i] = player
    
    # 测试 1：观察模式（上帝视角 + 名人名字）
    print("\n【测试 1】观察模式（显示所有玩家身份 + 名人名字）")
    print("-" * 70)
    ui_god = CLI(god_view=True)
    ui_god.set_game_state(state, human_player_id=None)
    
    for i in range(1, 8):
        ui_god.display_message(f"{i}号玩家", "我是好人，大家相信我。")
    
    # 测试 2：玩家模式（人类玩家是 3 号）
    print("\n【测试 2】玩家模式（人类玩家是 3 号，只显示自己身份）")
    print("-" * 70)
    ui_player = CLI(god_view=True)
    ui_player.set_game_state(state, human_player_id=3)
    
    for i in range(1, 8):
        ui_player.display_message(f"{i}号玩家", "我是好人，大家相信我。")
    
    # 测试 3：系统消息展示所有玩家信息
    print("\n【测试 3】游戏开始时展示所有玩家信息")
    print("-" * 70)
    for player in state.players.values():
        role_name = player.role.value if player.role else "未知"
        print(f"  {player.name}({player.celebrity_name}) - 身份：{role_name} - 人格：{player.personality}")
    
    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)


if __name__ == "__main__":
    test_celebrity_names()
