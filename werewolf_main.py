"""
狼人杀游戏入口文件

演示如何使用重构后的狼人杀多 Agents 架构
"""

import asyncio
from games.werewolf.config import GameConfig
from games.werewolf.orchestrator import WerewolfOrchestrator
from games.werewolf.state import Player
from services.logger_service import LoggerService
from services.tts_interface import MockTTS


def create_sample_game():
    """
    创建示例游戏配置
    9人标准局：3狼3神3民
    """
    roles = [
        {"role": "werewolf", "count": 3},
        {"role": "villager", "count": 2},
        {"role": "seer", "count": 1},
        {"role": "witch", "count": 1},
        {"role": "hunter", "count": 1},
        {"role": "guard", "count": 1}
    ]
    
    personalities = [
        "逻辑严谨型", "情感丰富型", "冷静分析型", "激进冒险型", "谨慎保守型",
        "善于欺骗型", "直觉敏锐型", "善于观察型", "善于表达型"
    ]
    
    config = GameConfig(
        player_count=9,
        roles=roles,
        personalities=personalities,
        rules={
            "witch_can_self_heal": True,
            "hunter_can_shoot_if_poisoned": False,
            "witch_same_night_dual_use": False,
            "witch_cannot_poison_first_night": False,
            "hunter_can_shoot_if_same_save_conflict": False,
            "president_can_inherit": True
        }
    )
    
    # 验证配置
    is_valid, errors, warnings = config.validate()
    if not is_valid:
        print(f"配置验证失败: {errors}")
        return None
    
    if warnings:
        print(f"配置警告: {warnings}")
    
    return config


def main():
    """
    主函数：运行狼人杀游戏演示
    """
    print("=== 狼人杀多 Agents 架构演示 ===")
    
    # 创建游戏配置
    config = create_sample_game()
    if not config:
        print("游戏配置创建失败")
        return
    
    # 创建日志服务
    logger = LoggerService()
    
    # 创建TTS服务（使用模拟实现）
    tts = MockTTS()
    
    # LLM配置（使用模拟实现）
    llm_config = {
        "provider": "mock",
        "model": "mock-model",
        "params": {}
    }
    
    # 创建游戏编排器
    try:
        orchestrator = WerewolfOrchestrator(
            config=config,
            llm_config=llm_config,
            logger=logger,
            tts=tts
        )
        
        print("游戏初始化完成，开始运行...")
        
        # 运行游戏
        asyncio.run(orchestrator.run_game())
        
        print("游戏结束")
        
    except Exception as e:
        print(f"游戏运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()