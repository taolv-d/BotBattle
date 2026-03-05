"""快速验证脚本 - 不依赖 API"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 50)
print("BotBattle 代码验证")
print("=" * 50)

# 1. 验证导入
print("\n[1] 验证模块导入...")
try:
    from core.game_engine import GameEngine
    from core.state import GameState, Player, Role, Phase
    from ai.agent import AIAgent
    from ai.personality import Personality, PersonalityManager
    from ai.llm_client import LLMClient
    from ui.cli import CLI
    from config_loader import ConfigManager
    print("    [OK] 所有模块导入成功")
except Exception as e:
    print(f"    [FAIL] 导入失败：{e}")
    sys.exit(1)

# 2. 验证配置加载
print("\n[2] 验证配置加载...")
try:
    config_mgr = ConfigManager()
    config_mgr.load_personalities()
    config_mgr.load_game_config()
    print(f"    [OK] 人格配置：{len(config_mgr.personalities)} 种")
    print(f"    [OK] 游戏配置：{config_mgr.game.get('name', 'unknown')}")
except Exception as e:
    print(f"    [FAIL] 配置加载失败：{e}")
    sys.exit(1)

# 3. 验证 GameState
print("\n[3] 验证 GameState...")
try:
    state = GameState()
    assert state.player_count == 9
    assert state.day_number == 0
    assert state.phase == Phase.NIGHT
    print("    [OK] GameState 初始化正确")
except Exception as e:
    print(f"    [FAIL] GameState 错误：{e}")
    sys.exit(1)

# 4. 验证 Personality
print("\n[4] 验证 Personality...")
try:
    pm = PersonalityManager()
    honest = pm.get("honest")
    assert honest is not None
    assert honest.min_length == 30
    assert honest.max_length == 80
    print("    [OK] Personality 加载正确")
except Exception as e:
    print(f"    [FAIL] Personality 错误：{e}")
    sys.exit(1)

# 5. 验证 UI
print("\n[5] 验证 UI...")
try:
    ui = CLI()
    assert hasattr(ui, 'display_message')
    assert hasattr(ui, 'get_player_input')
    print("    [OK] UI 接口实现正确")
except Exception as e:
    print(f"    [FAIL] UI 错误：{e}")
    sys.exit(1)

# 6. 验证日志目录
print("\n[6] 验证日志目录...")
try:
    logs_dir = Path("logs")
    assert logs_dir.exists()
    log_files = list(logs_dir.glob("*.json"))
    print(f"    [OK] 日志目录存在，已有 {len(log_files)} 个日志文件")
except Exception as e:
    print(f"    [FAIL] 日志目录错误：{e}")
    sys.exit(1)

# 7. 验证 SDD 文档
print("\n[7] 验证 SDD 文档...")
try:
    sdd_file = Path("SDD.md")
    assert sdd_file.exists()
    content = sdd_file.read_text(encoding='utf-8')
    assert "Specification-Driven Development" in content or "规范驱动开发" in content
    assert "GameEngine" in content
    assert "AIAgent" in content
    print("    [OK] SDD 文档存在且内容完整")
except Exception as e:
    print(f"    [FAIL] SDD 文档错误：{e}")
    sys.exit(1)

print("\n" + "=" * 50)
print("[PASS] 所有验证通过！代码可以提交。")
print("=" * 50)
