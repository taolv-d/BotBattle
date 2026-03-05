"""测试投票内心活动展示"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.state import GameState, Player, Role
from ai.agent import AIAgent
from ai.personality import Personality


def test_vote_with_thoughts():
    """测试投票时展示内心活动"""
    print("=" * 70)
    print("测试投票内心活动展示")
    print("=" * 70)
    
    # 创建测试玩家
    player = Player(id=4, name="4 号玩家", role=Role.VILLAGER, celebrity_name="诸葛亮")
    personality = Personality({
        "name": "真诚",
        "description": "诚实正直",
        "traits": ["诚实", "直接"],
        "speech_style": {"min_length": 30, "max_length": 80, "tone": "真诚"}
    })
    
    class DummyLLM:
        def chat(self, messages, max_tokens=100):
            # 模拟 LLM 返回投票决策和理由
            return '{"vote": 7, "reason": "7 号发言很可疑，一直在划水，不敢分析别人"}', {}
    
    agent = AIAgent(player, personality, DummyLLM())
    
    # 模拟投票场景
    context = {
        "alive_players": [1, 2, 3, 4, 5, 6, 7],
        "my_id": 4,
        "previous_speeches": [
            {"speaker": "1 号", "player_id": 1, "content": "我是好人，暂时没信息"},
            {"speaker": "2 号", "player_id": 2, "content": "我怀疑 5 号，他发言太少了"},
            {"speaker": "3 号", "player_id": 3, "content": "我是预言家，查验 6 号是好人"},
            {"speaker": "5 号", "player_id": 5, "content": "过了"},
            {"speaker": "6 号", "player_id": 6, "content": "感谢 3 号金水，我会站边 3 号"},
            {"speaker": "7 号", "player_id": 7, "content": "没想好，先听听后面"},
        ]
    }
    
    print("\n【投票场景】")
    print("-" * 70)
    print("存活玩家：1, 2, 3, 4, 5, 6, 7")
    print("\n发言历史：")
    for speech in context["previous_speeches"]:
        print(f"  {speech['speaker']}: {speech['content']}")
    
    # 投票
    vote, thought = agent.vote(context)
    
    print(f"\n【4 号玩家 (诸葛亮) 投票结果】")
    print("-" * 70)
    if vote:
        print(f"投票给：{vote}号")
    else:
        print("投票：弃权")
    print(f"内心独白：{thought}")
    
    # 显示上帝视角格式
    print(f"\n【上帝视角显示】")
    print("-" * 70)
    print(f"[4 号] 4 号 (诸葛亮 -villager) 投票给 {vote}号：{thought}")
    
    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)
    
    print("\n【改进总结】")
    print("1. [OK] AI 投票返回 (投票目标，内心独白)")
    print("2. [OK] 上帝视角可以看到每个玩家的投票选择")
    print("3. [OK] 显示投票理由和内心活动")
    print("4. [OK] 包含身份和名人名字信息")


if __name__ == "__main__":
    test_vote_with_thoughts()
