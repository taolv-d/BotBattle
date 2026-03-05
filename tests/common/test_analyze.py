"""测试 analyze_speech 功能"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai.agent import AIAgent
from ai.personality import Personality
from ai.llm_client import LLMClient
from core.state import Player, Role


def test_analyze():
    """测试发言分析功能"""
    print("=" * 50)
    print("测试 AI 发言分析功能")
    print("=" * 50)
    
    # 创建测试玩家
    player1 = Player(id=1, name="1 号", role=Role.VILLAGER)
    player2 = Player(id=2, name="2 号", role=Role.VILLAGER)
    player3 = Player(id=3, name="3 号", role=Role.VILLAGER)
    
    # 创建人格和 AI
    personality = Personality({
        "name": "测试",
        "description": "测试人格",
        "traits": ["测试"],
        "speech_style": {"min_length": 20, "max_length": 100, "tone": "正常"}
    })
    
    # 创建虚拟 LLM 客户端（不需要实际调用 API）
    class DummyLLM:
        def chat(self, *args, **kwargs):
            return "", {}
        def generate_with_inner_thought(self, *args, **kwargs):
            return "", ""
    
    llm = DummyLLM()
    
    # 创建 AI 代理
    agent1 = AIAgent(player1, personality, llm)
    agent2 = AIAgent(player2, personality, llm)
    agent3 = AIAgent(player3, personality, llm)
    
    print("\n初始状态：")
    print(f"Agent1 怀疑：{agent1.suspect_list}, 信任：{agent1.trust_list}")
    print(f"Agent2 怀疑：{agent2.suspect_list}, 信任：{agent2.trust_list}")
    
    # 测试场景 1：2 号说怀疑 1 号是狼
    print("\n--- 场景 1: 2 号说'我怀疑 1 号是狼人' ---")
    speech1 = "我怀疑 1 号是狼人，他的发言太假了"
    agent1.analyze_speech(speech1, speaker_id=2)
    print(f"Agent1 怀疑：{agent1.suspect_list}, 信任：{agent1.trust_list}")
    print(f"  预期：怀疑=[2]")
    
    # 测试场景 2：3 号说信任 1 号
    print("\n--- 场景 2: 3 号说'1 号是好人，我信任他' ---")
    speech2 = "1 号是好人，我信任他，他的分析很有道理"
    agent1.analyze_speech(speech2, speaker_id=3)
    print(f"Agent1 怀疑：{agent1.suspect_list}, 信任：{agent1.trust_list}")
    print(f"  预期：怀疑=[2], 信任=[3]")
    
    # 测试场景 3：2 号说给 1 号发金水
    print("\n--- 场景 3: 2 号说'1 号是我的金水' ---")
    speech3 = "1 号是我的金水，他是好人"
    agent1.analyze_speech(speech3, speaker_id=2)
    print(f"Agent1 怀疑：{agent1.suspect_list}, 信任：{agent1.trust_list}")
    print(f"  预期：怀疑=[], 信任=[2, 3] (2 号从怀疑移到信任)")
    
    # 测试场景 4：3 号发言很长且有分析
    print("\n--- 场景 4: 3 号发言很长且有'分析'关键词 ---")
    speech4 = "我来详细分析一下现在的局势，从逻辑角度来看，1 号的发言确实有问题，但是 2 号的行为也不太好，我们需要更多信息才能判断"
    agent1.analyze_speech(speech4, speaker_id=3)
    print(f"Agent1 怀疑：{agent1.suspect_list}, 信任：{agent1.trust_list}")
    print(f"  预期：怀疑=[], 信任=[2, 3] (3 号已经在信任列表)")
    
    # 测试场景 5：2 号激进发言
    print("\n--- 场景 5: 2 号说'必须出 1 号'（短且激进） ---")
    speech5 = "必须出 1 号，没得商量"
    agent1.analyze_speech(speech5, speaker_id=2)
    print(f"Agent1 怀疑：{agent1.suspect_list}, 信任：{agent1.trust_list}")
    print(f"  预期：怀疑=[2], 信任=[3] (2 号从信任移到怀疑)")
    
    print("\n" + "=" * 50)
    print("测试完成！")
    print("=" * 50)


if __name__ == "__main__":
    test_analyze()
