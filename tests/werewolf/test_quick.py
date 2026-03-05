"""快速测试脚本 - 只运行一轮"""
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


def test_quick():
    """快速测试"""
    print("=" * 50)
    print("BotBattle - AI 狼人杀 - 快速测试")
    print("=" * 50)
    
    config_mgr = ConfigManager()
    config_mgr.load_all()
    
    llm_config = config_mgr.get_llm_config()
    llm_client = LLMClient(llm_config)
    print(f"[OK] LLM 已配置")
    
    personality_mgr = PersonalityManager()
    print(f"[OK] 已加载 {len(personality_mgr.personalities)} 种人格")
    
    ui = CLI(show_inner_thoughts=False)
    game_config = config_mgr.get_game_config()
    
    engine = GameEngine(ui, config_mgr.system)
    engine.setup(
        player_count=game_config.get("player_count", 9),
        roles_config=game_config.get("roles", []),
        personalities=config_mgr.get_personality_names(),
        human_player_id=None,
    )
    
    for player in engine.state.players.values():
        if player.is_bot:
            personality = personality_mgr.get(player.personality)
            if not personality:
                personality = personality_mgr.get_random()
            agent = AIAgent(player, personality, llm_client)
            engine.agents[player.id] = agent
    
    print("\n[系统] 游戏开始！\n")
    engine.start()
    print("\n测试完成！")


if __name__ == "__main__":
    test_quick()
