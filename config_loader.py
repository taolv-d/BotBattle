"""配置加载器"""
import json
from pathlib import Path
from typing import Optional


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.system: dict = {}
        self.game: dict = {}
        self.personalities: dict = {}
    
    def load_system(self, path: Optional[str] = None) -> dict:
        """加载系统配置"""
        if path is None:
            path = str(self.config_dir / "system.json")
        
        with open(path, "r", encoding="utf-8") as f:
            self.system = json.load(f)
        return self.system
    
    def load_game_config(self, name: str = "werewolf_default") -> dict:
        """加载游戏配置"""
        path = str(self.config_dir / f"{name}.json")
        
        with open(path, "r", encoding="utf-8") as f:
            self.game = json.load(f)
        return self.game
    
    def load_personalities(self) -> dict:
        """加载人格配置"""
        path = str(self.config_dir / "personalities.json")
        
        with open(path, "r", encoding="utf-8") as f:
            self.personalities = json.load(f)
        return self.personalities
    
    def load_all(self) -> None:
        """加载所有配置"""
        self.load_system()
        self.load_game_config()
        self.load_personalities()
    
    def get_llm_config(self) -> dict:
        """获取 LLM 配置"""
        return self.system.get("llm", {})
    
    def get_game_config(self) -> dict:
        """获取游戏配置"""
        return self.game
    
    def get_personality_names(self) -> list[str]:
        """获取人格名称列表"""
        return self.game.get("personalities", [])
