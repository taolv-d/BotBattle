"""
测试游戏复盘服务

用于验证复盘功能的正确性
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.game_review_service import GameReviewService, ReviewConfig, ReviewMode
from services.llm_service import LLMService


# 模拟日志数据
MOCK_LOG_ENTRIES = [
    {
        "timestamp": "2026-03-20T15:33:44.104",
        "event_type": "game_start",
        "data": {"game_id": "werewolf_1234", "player_count": 9}
    },
    {
        "timestamp": "2026-03-20T15:34:00.000",
        "event_type": "speech",
        "data": {
            "player_id": 1,
            "content": "我是好人，目前还没有什么信息，先听听后面人的发言。",
            "day": 1
        }
    },
    {
        "timestamp": "2026-03-20T15:34:30.000",
        "event_type": "speech",
        "data": {
            "player_id": 2,
            "content": "我是预言家，昨晚验了 3 号，是好人。今天先出 1 号，他发言有问题。",
            "day": 1
        }
    },
    {
        "timestamp": "2026-03-20T15:35:00.000",
        "event_type": "speech",
        "data": {
            "player_id": 3,
            "content": "2 号跳预言家，但我才是真的！昨晚验了 5 号是狼人。大家相信我！",
            "day": 1
        }
    },
    {
        "timestamp": "2026-03-20T15:36:00.000",
        "event_type": "vote",
        "data": {"voter_id": 1, "target_id": 2}
    },
    {
        "timestamp": "2026-03-20T15:36:00.000",
        "event_type": "vote",
        "data": {"voter_id": 3, "target_id": 2}
    },
    {
        "timestamp": "2026-03-20T15:37:00.000",
        "event_type": "death",
        "data": {"player_id": 2, "death_cause": "vote_out"}
    },
    {
        "timestamp": "2026-03-20T15:37:30.000",
        "event_type": "last_words",
        "data": {
            "player_id": 2,
            "content": "我真的是预言家，你们会后悔的。3 号肯定是狼人，悍跳我的身份。"
        }
    }
]


async def test_review_generation():
    """测试复盘报告生成"""
    print("=" * 50)
    print("测试复盘报告生成功能")
    print("=" * 50)

    # 创建复盘服务
    config = ReviewConfig(
        enabled=True,
        mode=ReviewMode.DETAILED,
        detect_loopholes=False,
        max_log_entries=100
    )

    # 使用 mock LLM（避免实际调用 API）
    llm_config = {
        "provider": "mock",
        "params": {}
    }
    llm_service = LLMService(llm_config)

    service = GameReviewService(config=config)
    service.set_llm_service(llm_service)

    # 生成报告
    game_result = {
        "winner": "good",
        "reason": "all_wolves_dead",
        "day_number": 5,
        "game_id": "werewolf_1234"
    }

    print("\n正在生成复盘报告...")
    report = await service.generate_review(
        game_id="werewolf_1234",
        game_type="werewolf",
        log_entries=MOCK_LOG_ENTRIES,
        game_result=game_result
    )

    if report:
        print("\n✓ 复盘报告生成成功")
        print(f"\n报告摘要:\n{report.summary[:300]}...")
        print(f"\n报告已保存到：reviews/review_{report.game_id}.md")
    else:
        print("\n✗ 复盘报告生成失败")

    return report


async def test_loophole_detection():
    """测试漏洞检测功能"""
    print("\n" + "=" * 50)
    print("测试逻辑漏洞检测功能")
    print("=" * 50)

    # 创建复盘服务（启用漏洞检测）
    config = ReviewConfig(
        enabled=True,
        mode=ReviewMode.ANALYSIS,
        detect_loopholes=True,
        max_log_entries=100
    )

    llm_config = {
        "provider": "mock",
        "params": {}
    }
    llm_service = LLMService(llm_config)

    service = GameReviewService(config=config)
    service.set_llm_service(llm_service)

    # 检测漏洞
    print("\n正在检测逻辑漏洞...")
    loopholes = await service.detect_loopholes(
        game_type="werewolf",
        log_entries=MOCK_LOG_ENTRIES,
        game_result={"game_id": "werewolf_1234", "winner": "good"}
    )

    if loopholes:
        print(f"\n✓ 检测到 {len(loopholes)} 个逻辑漏洞:")
        for i, loophole in enumerate(loopholes, 1):
            print(f"\n  漏洞 {i}:")
            print(f"    类型：{loophole.get('type', '未知')}")
            print(f"    玩家：{loophole.get('player', '未知')}")
            print(f"    分析：{loophole.get('analysis', '')[:100]}")
    else:
        print("\n✓ 未检测到明显逻辑漏洞")

    return loopholes


async def main():
    """主函数"""
    print("\nBotBattle - 游戏复盘服务测试\n")

    # 测试报告生成
    report = await test_review_generation()

    # 测试漏洞检测
    loopholes = await test_loophole_detection()

    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)

    if report:
        print(f"\n复盘报告文件：reviews/review_{report.game_id}.md")
        print(f"JSON 文件：reviews/review_{report.game_id}.json")


if __name__ == "__main__":
    asyncio.run(main())
