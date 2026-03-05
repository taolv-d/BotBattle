"""BotBattle - AI 大乱斗游戏引擎"""
import sys
import os
from pathlib import Path

# 修复 Windows 编码问题
if sys.platform == 'win32':
    os.system('chcp 65001 >nul')

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config_loader import ConfigManager
from ui.cli import CLI
from core.game_engine import GameEngine
from ai.agent import AIAgent
from ai.personality import PersonalityManager
from ai.llm_client import LLMClient


def main():
    """主函数"""
    print("=" * 50)
    print("BotBattle - AI 狼人杀")
    print("=" * 50)
    
    # 加载配置
    print("\n正在加载配置...")
    config_mgr = ConfigManager()
    
    try:
        config_mgr.load_all()
    except FileNotFoundError as e:
        print(f"[错误] 配置文件不存在：{e}")
        print("请检查 config/ 目录下的配置文件是否完整")
        return
    
    # 初始化 LLM 客户端
    llm_config = config_mgr.get_llm_config()
    if not llm_config.get("api_key") or llm_config.get("api_key") == "YOUR_API_KEY":
        print("\n[警告] 未配置 LLM API Key！")
        print("请编辑 config/system.json 文件，填入有效的 API Key")
        print("\n支持的 API 提供商：")
        print("  - DeepSeek: https://platform.deepseek.com/")
        print("  - 通义千问：https://dashscope.aliyun.com/")
        print("  - 其他 OpenAI 兼容接口")
        return
    
    llm_client = LLMClient(llm_config)
    print(f"[OK] LLM 已配置：{llm_config.get('provider', 'unknown')}")

    # 初始化人格管理器
    personality_mgr = PersonalityManager()
    print(f"[OK] 已加载 {len(personality_mgr.personalities)} 种人格")
    
    # 创建 UI
    ui = CLI(show_inner_thoughts=False)  # 默认不显示内心独白
    
    # 选择游戏模式
    is_human_mode, human_player_id = ui.select_player_mode()
    
    if is_human_mode:
        ui.display_system_message(f"你将以 {human_player_id}号玩家 身份参与游戏")
    else:
        ui.display_system_message("进入观察模式，观看 AI 互斗")
    
    # 获取游戏配置
    game_config = config_mgr.get_game_config()
    player_count = game_config.get("player_count", 9)
    roles_config = game_config.get("roles", [])
    personality_names = config_mgr.get_personality_names()
    
    ui.display_system_message(f"游戏配置：{game_config.get('name', '自定义')}")
    ui.display_system_message(f"玩家数量：{player_count}人")
    
    # 创建游戏引擎
    engine = GameEngine(ui, config_mgr.system)
    
    # 设置游戏
    engine.setup(
        player_count=player_count,
        roles_config=roles_config,
        personalities=personality_names,
        human_player_id=human_player_id,
    )
    
    # 初始化 AI 代理
    for player in engine.state.players.values():
        if player.is_bot:
            personality = personality_mgr.get(player.personality)
            if not personality:
                personality = personality_mgr.get_random()
            agent = AIAgent(player, personality, llm_client)
            engine.agents[player.id] = agent
    
    # 允许人类玩家中途加入/退出
    if is_human_mode:
        ui.display_system_message("游戏中输入 'quit' 可退出并替换为 AI")
    
    # 开始游戏
    try:
        engine.start()
    except KeyboardInterrupt:
        print("\n\n游戏被中断")
        ui.display_system_message("游戏已退出")
    
    print("\n感谢游玩！")


if __name__ == "__main__":
    main()
