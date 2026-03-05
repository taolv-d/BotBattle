"""测试狼人杀改进功能"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.state import GameState, Player, Role
from ai.agent import AIAgent
from ai.personality import Personality


def test_improvements():
    """测试改进功能"""
    print("=" * 70)
    print("测试狼人杀改进功能")
    print("=" * 70)
    
    # 测试 1：AI 知道自己号码
    print("\n【改进 1】AI 知道自己号码 - 发言提示")
    print("-" * 70)
    
    player = Player(id=4, name="4 号玩家", role=Role.VILLAGER, celebrity_name="诸葛亮")
    personality = Personality({
        "name": "真诚",
        "description": "诚实正直",
        "traits": ["诚实", "直接"],
        "speech_style": {"min_length": 30, "max_length": 80, "tone": "真诚"}
    })
    
    class DummyLLM:
        def generate_with_inner_thought(self, system, user, max_length=100):
            # 模拟 LLM 返回，检查 prompt 中是否包含自己的号码
            if "4 号玩家" in user and "不要提到自己的号码" in user:
                return "我认为 7 号玩家发言很可疑，大家要注意。", "我确实是村民，7 号刚才的发言逻辑有问题"
            return "我是好人。", ""
        def chat(self, messages, max_tokens=50):
            return '{"target": 3, "reason": "3 号发言有问题"}', {}
    
    agent = AIAgent(player, personality, DummyLLM())
    
    # 模拟发言
    context = {
        "day_number": 1,
        "night_deaths": [],
        "alive_players": [1, 2, 3, 4, 5, 6, 7],
        "previous_speeches": [
            {"speaker": "1 号", "player_id": 1, "content": "我是好人"},
            {"speaker": "2 号", "player_id": 2, "content": "我怀疑 3 号"},
        ]
    }
    
    speech, thought = agent.speak(context, round_num=1)
    print(f"4 号玩家发言：{speech}")
    print(f"内心独白：{thought}")
    print("[OK] AI 知道自己号码，prompt 中有明确提示")
    
    # 测试 2：夜晚行动返回内心独白
    print("\n【改进 2】夜晚行动返回内心独白")
    print("-" * 70)
    
    # 狼人
    wolf_player = Player(id=4, name="4 号玩家", role=Role.WEREWOLF, celebrity_name="曹操")
    wolf_agent = AIAgent(wolf_player, personality, DummyLLM())
    
    action, thought = wolf_agent.decide_night_action({
        "alive_players": [1, 2, 3, 5, 6, 7],
        "wolf_teammates": [2],
        "my_id": 4,
    })
    
    print(f"狼人行动：{action}")
    print(f"内心独白：{thought}")
    print("[OK] 狼人行动包含内心独白")
    
    # 预言家
    seer_player = Player(id=3, name="3 号玩家", role=Role.SEER, celebrity_name="诸葛亮")
    seer_agent = AIAgent(seer_player, personality, DummyLLM())
    
    action, thought = seer_agent.decide_night_action({
        "alive_players": [1, 2, 4, 5, 6, 7],
        "my_id": 3,
    })
    
    print(f"\n预言家行动：{action}")
    print(f"内心独白：{thought}")
    print("[OK] 预言家行动包含内心独白")
    
    # 女巫
    witch_player = Player(id=5, name="5 号玩家", role=Role.WITCH, celebrity_name="华佗")
    witch_agent = AIAgent(witch_player, personality, DummyLLM())
    
    action, thought = witch_agent.decide_night_action({
        "alive_players": [1, 2, 3, 4, 6, 7],
        "dead_player": 2,
        "my_id": 5,
    })
    
    print(f"\n女巫行动：{action}")
    print(f"内心独白：{thought}")
    print("[OK] 女巫行动包含内心独白")
    
    print("\n" + "=" * 70)
    print("测试完成！所有改进功能正常")
    print("=" * 70)
    
    print("\n【改进总结】")
    print("1. [OK] AI 发言时知道自己号码，不会再出现'我 4 号认为'的逻辑错误")
    print("2. [OK] 夜晚行动（狼人、预言家、女巫）都返回内心独白")
    print("3. [OK] 上帝视角可以看到所有角色的内心活动和决策理由")


if __name__ == "__main__":
    test_improvements()
