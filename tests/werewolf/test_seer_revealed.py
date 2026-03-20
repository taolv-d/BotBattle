"""
测试预言家跳明身份后的记忆问题

验证点：
1. 预言家在警长竞选时跳明身份后，revealed 标志应该设置为 True
2. 预言家在白天发言时，应该记住自己已经跳明身份
3. 预言家不应该再说"今晚查验"这类话
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from games.werewolf.agents.seer import SeerAgent
from games.werewolf.config import Role


class MockLLMService:
    """模拟 LLM 服务用于测试"""
    
    def __init__(self):
        self.model_config = {"model": "test"}
        self.call_history = []
    
    async def generate_response(self, prompt: str) -> str:
        """模拟生成响应"""
        self.call_history.append(prompt)
        
        # 根据 prompt 内容返回合适的响应
        if "警长竞选" in prompt:
            return "我是预言家，我会带领大家找出狼人。"
        elif "今晚查验" in prompt:
            # 如果 prompt 中包含"今晚查验"，说明预言家忘记了已跳明身份
            return "或许今晚我可以先查验他。"
        elif "跳明身份" in prompt:
            return "我已经跳明了预言家身份，我会分享我的查验结果。"
        else:
            return "我是好人，我会投票给狼人。"


async def test_seer_president_speech():
    """测试预言家警长竞选发言"""
    print("=" * 60)
    print("测试 1：预言家警长竞选发言")
    print("=" * 60)
    
    llm_service = MockLLMService()
    seer = SeerAgent(player_id=7, name="Player_7", personality="Test", llm_service=llm_service)
    
    # 初始状态：未跳明身份
    assert seer.revealed == False, "初始状态 revealed 应该为 False"
    print("✓ 初始状态：revealed = False")
    
    # 警长竞选发言
    speech = await seer.president_speech()
    
    # 验证：发言后 revealed 应该为 True
    assert seer.revealed == True, "警长竞选发言后 revealed 应该为 True"
    print("✓ 警长竞选发言后：revealed = True")
    
    # 验证：prompt 中应该包含跳明身份的指示
    assert len(llm_service.call_history) > 0, "LLM 应该被调用"
    prompt = llm_service.call_history[0]
    assert "跳明身份" in prompt, "prompt 应该包含跳明身份的指示"
    print("✓ prompt 包含跳明身份的指示")
    
    print(f"✓ 竞选发言内容：{speech}")
    print("测试 1 通过！\n")
    return True


async def test_seer_day_speech_revealed():
    """测试预言家白天发言（已跳明身份）"""
    print("=" * 60)
    print("测试 2：预言家白天发言（已跳明身份）")
    print("=" * 60)
    
    llm_service = MockLLMService()
    seer = SeerAgent(player_id=7, name="Player_7", personality="Test", llm_service=llm_service)
    
    # 模拟已经跳明身份
    seer.revealed = True
    
    # 模拟已查验玩家
    seer.checked_players = {3, 5}
    
    # 构建上下文（模拟 orchestrator 传递的 checked_info）
    context = {
        "game_info": {
            "day_number": 1,
            "alive_players": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "president_id": 7
        },
        "day_phase": "discussion",
        "checked_info": {3: "villager", 5: "werewolf"}  # 模拟已查验信息
    }
    
    # 白天发言
    speech = await seer.speak(context)
    
    # 验证：prompt 中应该包含跳明身份的提示
    assert len(llm_service.call_history) > 0, "LLM 应该被调用"
    prompt = llm_service.call_history[-1]
    
    # 验证：prompt 中应该包含"已经跳明身份"的提示
    assert "已经跳明身份" in prompt or "跳明" in prompt, "prompt 应该提醒预言家已经跳明身份"
    print("✓ prompt 包含'已经跳明身份'的提示")
    
    # 验证：prompt 中应该包含"不应该再说今晚查验"的提示
    assert "不应该" in prompt or "不要" in prompt, "prompt 应该提示不要说'今晚查验'"
    print("✓ prompt 包含不要说'今晚查验'的提示")
    
    # 验证：prompt 中应该包含已查验信息
    assert "3" in prompt and "villager" in prompt, "prompt 应该包含查验的村民信息"
    assert "5" in prompt and "werewolf" in prompt, "prompt 应该包含查验的狼人信息"
    print("✓ prompt 包含已查验玩家的信息")
    
    print(f"✓ 白天发言内容：{speech}")
    print("测试 2 通过！\n")
    return True


async def test_seer_day_speech_not_revealed():
    """测试预言家白天发言（未跳明身份）"""
    print("=" * 60)
    print("测试 3：预言家白天发言（未跳明身份）")
    print("=" * 60)
    
    llm_service = MockLLMService()
    seer = SeerAgent(player_id=7, name="Player_7", personality="Test", llm_service=llm_service)
    
    # 模拟未跳明身份
    seer.revealed = False
    
    # 构建上下文（没有 checked_info，因为还没进行夜晚行动）
    context = {
        "game_info": {
            "day_number": 1,
            "alive_players": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "president_id": None
        },
        "day_phase": "discussion",
        "checked_info": {}
    }
    
    # 白天发言
    speech = await seer.speak(context)
    
    # 验证：prompt 中不应该包含"已经跳明身份"的提示
    prompt = llm_service.call_history[-1]
    assert "已经跳明身份" not in prompt, "未跳明时 prompt 不应该包含'已经跳明身份'"
    print("✓ prompt 不包含'已经跳明身份'的提示（正确）")
    
    print(f"✓ 白天发言内容：{speech}")
    print("测试 3 通过！\n")
    return True


async def test_seer_vote_with_checked_info():
    """测试预言家投票（使用查验信息）"""
    print("=" * 60)
    print("测试 4：预言家投票（使用查验信息）")
    print("=" * 60)
    
    llm_service = MockLLMService()
    seer = SeerAgent(player_id=7, name="Player_7", personality="Test", llm_service=llm_service)
    
    # 模拟已跳明身份
    seer.revealed = True
    
    # 构建投票上下文
    context = {
        "alive_players": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "candidates": [2, 5, 8],
        "previous_votes": {},
        "my_id": 7,
        "checked_info": {5: "werewolf", 3: "villager"}  # 5 号是狼人
    }
    
    # 投票
    vote = await seer.vote(context)
    
    # 验证：应该投票给已确认的狼人
    # 当有确认的狼人时，预言家会直接投票，不需要调用 LLM
    assert vote == 5, f"应该投票给已确认的狼人 5 号，实际投票给 {vote}"
    print("✓ 投票给已确认的狼人 5 号")
    
    # 验证：记忆中包含投票记录
    # 注意：add_memory 添加到 self.memories 列表
    # 这里我们验证投票逻辑正确执行
    
    print(f"✓ 投票结果：{vote}")
    print("测试 4 通过！\n")
    return True


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("预言家跳明身份记忆测试")
    print("=" * 60 + "\n")
    
    results = []
    
    try:
        results.append(("警长竞选发言", await test_seer_president_speech()))
    except Exception as e:
        print(f"测试 1 失败：{e}\n")
        results.append(("警长竞选发言", False))
    
    try:
        results.append(("白天发言（已跳明）", await test_seer_day_speech_revealed()))
    except Exception as e:
        print(f"测试 2 失败：{e}\n")
        results.append(("白天发言（已跳明）", False))
    
    try:
        results.append(("白天发言（未跳明）", await test_seer_day_speech_not_revealed()))
    except Exception as e:
        print(f"测试 3 失败：{e}\n")
        results.append(("白天发言（未跳明）", False))
    
    try:
        results.append(("投票（使用查验信息）", await test_seer_vote_with_checked_info()))
    except Exception as e:
        print(f"测试 4 失败：{e}\n")
        results.append(("投票（使用查验信息）", False))
    
    # 汇总结果
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")
    
    print(f"\n总计：{passed}/{total} 测试通过")
    
    if passed == total:
        print("\n✓ 所有测试通过！预言家跳明身份记忆问题已修复。")
        return 0
    else:
        print("\n✗ 部分测试失败，请检查修复。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
