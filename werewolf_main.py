"""
狼人杀游戏入口文件

使用重构后的多 Agents 架构
"""
import sys
import os
import asyncio
from pathlib import Path

# 修复 Windows 编码问题
if sys.platform == 'win32':
    os.system('chcp 65001 >nul')

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config_loader import ConfigManager
from games.werewolf.config import GameConfig
from games.werewolf.orchestrator import WerewolfOrchestrator
from services.logger_service import LoggerService
from services.tts_interface import MockTTS


def create_game_config(config_mgr: ConfigManager) -> GameConfig:
    """
    从配置管理器创建游戏配置
    """
    game_config = config_mgr.get_game_config()
    
    roles = game_config.get("roles", [
        {"role": "werewolf", "count": 3},
        {"role": "villager", "count": 3},
        {"role": "seer", "count": 1},
        {"role": "witch", "count": 1},
        {"role": "hunter", "count": 1}
    ])
    
    personalities = config_mgr.get_personality_names()
    if not personalities:
        personalities = [
            "逻辑严谨型", "情感丰富型", "冷静分析型", "激进冒险型", "谨慎保守型",
            "善于欺骗型", "直觉敏锐型", "善于观察型", "善于表达型"
        ]
    
    game_rules = game_config.get("game_rules", {})
    
    config = GameConfig(
        player_count=game_config.get("player_count", 9),
        roles=roles,
        personalities=personalities,
        rules={
            "witch_can_self_heal": True,
            "hunter_can_shoot_if_poisoned": game_rules.get("hunter_can_skill", True),
            "witch_same_night_dual_use": False,
            "witch_cannot_poison_first_night": False,
            "hunter_can_shoot_if_same_save_conflict": False,
            "president_can_inherit": game_rules.get("has_president_election", True)
        }
    )
    
    return config


def main():
    """
    主函数：运行狼人杀游戏
    """
    print("=" * 50)
    print("BotBattle - AI 狼人杀 (多 Agents 架构)")
    print("=" * 50)
    
    # 加载配置
    print("\n正在加载配置...")
    config_mgr = ConfigManager()
    
    try:
        config_mgr.load_all()
    except FileNotFoundError as e:
        print(f"[错误] 配置文件不存在：{e}")
        print("请运行 'python init.py' 初始化配置")
        return
    
    # 获取 LLM 配置
    llm_config = config_mgr.get_llm_config()
    if not llm_config.get("api_key") or llm_config.get("api_key") == "YOUR_API_KEY":
        print("\n[警告] 未配置 LLM API Key！")
        print("请编辑 config/system.json 文件，填入有效的 API Key")
        print("\n支持的 API 提供商：")
        print("  - DeepSeek: https://platform.deepseek.com/")
        print("  - 通义千问：https://dashscope.aliyun.com/")
        print("  - 其他 OpenAI 兼容接口")
        return
    
    print(f"[OK] LLM 已配置：{llm_config.get('provider', 'unknown')}")
    
    # 创建游戏配置
    game_config = create_game_config(config_mgr)
    
    # 验证配置
    is_valid, errors, warnings = game_config.validate()
    if not is_valid:
        print(f"[错误] 配置验证失败: {errors}")
        return
    
    if warnings:
        print(f"[警告] {warnings}")
    
    print(f"[OK] 游戏配置：{config_mgr.game.get('name', '自定义')}")
    print(f"[OK] 玩家数量：{game_config.player_count}人")

    # 创建日志服务（使用时间戳生成独立日志文件）
    logger = LoggerService()

    # 创建 TTS 服务（使用模拟实现）
    tts = MockTTS()
    
    # 选择游戏模式
    print("\n请选择游戏模式：")
    print("  1. 观察模式（AI 互斗）")
    print("  2. 玩家模式（参与游戏）")
    
    try:
        choice = input("\n请输入选项 (1/2): ").strip()
    except EOFError:
        choice = "1"
    
    human_player_id = None
    if choice == "2":
        try:
            human_player_id = int(input(f"请选择你的玩家编号 (1-{game_config.player_count}): ").strip())
            if human_player_id < 1 or human_player_id > game_config.player_count:
                print(f"[警告] 无效的玩家编号，使用观察模式")
                human_player_id = None
            else:
                print(f"\n你将以 {human_player_id}号玩家 身份参与游戏")
        except (ValueError, EOFError):
            print("[警告] 无效输入，使用观察模式")
            human_player_id = None
    else:
        print("\n进入观察模式，观看 AI 互斗")
    
    # 显示玩家身份（上帝视角）
    print("\n【玩家身份】")
    print("-" * 40)
    
    # 创建游戏编排器
    try:
        orchestrator = WerewolfOrchestrator(
            config=game_config,
            llm_config=llm_config,
            logger=logger,
            tts=tts
        )
        
        # 显示玩家身份
        for player_id, player in orchestrator.state.players.items():
            role_name = {
                "werewolf": "狼人",
                "villager": "村民",
                "seer": "预言家",
                "witch": "女巫",
                "hunter": "猎人",
                "guard": "守卫"
            }.get(player.role.value, player.role.value)
            print(f"  {player_id}号：{role_name} - {player.personality}")
        
        print("\n" + "=" * 50)
        print("游戏开始")
        print("=" * 50)
        
        # 运行游戏
        asyncio.run(orchestrator.run_game())
        
        # 显示游戏结果
        print("\n" + "=" * 50)
        print("游戏结束")
        print("=" * 50)
        
        winner_name = {
            "good": "好人阵营",
            "werewolf": "狼人阵营"
        }.get(orchestrator.state.winner, orchestrator.state.winner)
        
        print(f"获胜方：{winner_name}")
        print(f"原因：{orchestrator.state.reason}")
        
    except Exception as e:
        print(f"\n[错误] 游戏运行出错: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n感谢游玩！")


if __name__ == "__main__":
    main()