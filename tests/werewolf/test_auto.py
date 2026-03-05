"""自动化测试脚本 - 观察模式"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config_loader import ConfigManager
from ui.cli import CLI
from core.game_engine import GameEngine
from ai.agent import AIAgent
from ai.personality import PersonalityManager
from ai.llm_client import LLMClient


def test_auto():
    """自动测试 - 观察模式"""
    print("=" * 50)
    print("BotBattle - AI 狼人杀 - 自动测试")
    print("=" * 50)
    
    # 加载配置
    print("\n正在加载配置...")
    config_mgr = ConfigManager()
    config_mgr.load_all()
    
    # 初始化 LLM 客户端
    llm_config = config_mgr.get_llm_config()
    llm_client = LLMClient(llm_config)
    print(f"[OK] LLM 已配置：{llm_config.get('provider', 'unknown')}")
    
    # 初始化人格管理器
    personality_mgr = PersonalityManager()
    print(f"[OK] 已加载 {len(personality_mgr.personalities)} 种人格")
    
    # 创建 UI
    ui = CLI(show_inner_thoughts=False)
    
    # 获取游戏配置
    game_config = config_mgr.get_game_config()
    player_count = game_config.get("player_count", 9)
    roles_config = game_config.get("roles", [])
    personality_names = config_mgr.get_personality_names()
    
    print(f"\n[系统] 游戏配置：{game_config.get('name', '自定义')}")
    print(f"[系统] 玩家数量：{player_count}人")
    
    # 创建游戏引擎
    engine = GameEngine(ui, config_mgr.system)
    
    # 设置游戏（观察模式）
    engine.setup(
        player_count=player_count,
        roles_config=roles_config,
        personalities=personality_names,
        human_player_id=None,  # 观察模式
    )
    
    # 初始化 AI 代理
    for player in engine.state.players.values():
        if player.is_bot:
            personality = personality_mgr.get(player.personality)
            if not personality:
                personality = personality_mgr.get_random()
            agent = AIAgent(player, personality, llm_client)
            engine.agents[player.id] = agent
    
    print("\n[系统] 游戏开始！\n")
    
    # 开始游戏
    try:
        engine.start()
    except KeyboardInterrupt:
        print("\n\n测试被中断")
    
    print("\n测试完成！")


if __name__ == "__main__":
    test_auto()
