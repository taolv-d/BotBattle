"""三国杀游戏入口"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config_loader import ConfigManager
from ui.cli import CLI
from games.threekingdoms.engine import ThreeKingdomsEngine


def main():
    """主函数"""
    print("=" * 50)
    print("BotBattle - 三国杀")
    print("=" * 50)
    
    # 加载配置
    print("\n正在加载配置...")
    config_mgr = ConfigManager()
    
    try:
        config_mgr.load_system()
        config_mgr.load_game_config("threekingdoms_default")
    except FileNotFoundError as e:
        print(f"[错误] 配置文件不存在：{e}")
        return
    
    # 初始化 LLM 客户端
    llm_config = config_mgr.get_llm_config()
    if not llm_config.get("api_key") or llm_config.get("api_key") == "YOUR_API_KEY":
        print("\n[警告] 未配置 LLM API Key！")
        print("请编辑 config/system.json 文件，填入有效的 API Key")
        return
    
    from ai.llm_client import LLMClient
    llm_client = LLMClient(llm_config)
    print(f"[OK] LLM 已配置：{llm_config.get('provider', 'unknown')}")
    
    # 初始化人格管理器
    from ai.personality import PersonalityManager
    personality_mgr = PersonalityManager()
    print(f"[OK] 已加载 {len(personality_mgr.personalities)} 种人格")
    
    # 创建 UI
    ui = CLI(show_inner_thoughts=False)
    
    # 选择游戏模式
    is_human_mode, human_player_id = ui.select_player_mode()
    
    if is_human_mode:
        ui.display_system_message(f"你将以 {human_player_id}号玩家 身份参与游戏")
    else:
        ui.display_system_message("进入观察模式，观看 AI 互斗")
    
    # 获取游戏配置
    game_config = config_mgr.get_game_config()
    player_count = game_config.get("player_count", 5)
    roles_config = game_config.get("roles", [])
    generals = game_config.get("generals", [])
    
    ui.display_system_message(f"游戏配置：{game_config.get('name', '自定义')}")
    ui.display_system_message(f"玩家数量：{player_count}人")
    ui.display_system_message(f"可选武将：{', '.join(generals[:8])}...")
    
    # 创建游戏引擎
    engine = ThreeKingdomsEngine(ui, config_mgr.system)
    
    # 设置游戏
    engine.setup(
        player_count=player_count,
        roles_config=roles_config,
        generals=generals,
        human_player_id=human_player_id,
    )
    
    # 开始游戏
    try:
        engine.start()
    except KeyboardInterrupt:
        print("\n\n游戏被中断")
        ui.display_system_message("游戏已退出")
    
    print("\n感谢游玩！")


if __name__ == "__main__":
    main()
