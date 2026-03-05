"""人格系统"""
import json
from typing import Optional
from pathlib import Path


class Personality:
    """人格定义"""
    
    def __init__(self, data: dict):
        self.name = data.get("name", "未知")
        self.description = data.get("description", "")
        self.traits = data.get("traits", [])
        self.speech_style = data.get("speech_style", {})
        self.min_length = self.speech_style.get("min_length", 20)
        self.max_length = self.speech_style.get("max_length", 100)
        self.tone = self.speech_style.get("tone", "正常")
    
    def to_prompt(self) -> str:
        """生成人格提示词"""
        traits_str = "、".join(self.traits)
        return f"""你现在的性格是「{self.name}」：{self.description}
性格特点：{traits_str}
说话风格：{self.tone}，发言长度通常在{self.min_length}-{self.max_length}字之间"""
    
    def __repr__(self):
        return f"Personality({self.name})"


class PersonalityManager:
    """人格管理器"""
    
    def __init__(self, config_path: str = "config/personalities.json"):
        self.personalities: dict[str, Personality] = {}
        self.load_from_file(config_path)
    
    def load_from_file(self, path: str) -> None:
        """从文件加载人格配置"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for key, value in data.items():
                    self.personalities[key] = Personality(value)
        except FileNotFoundError:
            print(f"[警告] 人格配置文件不存在：{path}")
        except json.JSONDecodeError:
            print(f"[错误] 人格配置文件格式错误：{path}")
    
    def get(self, name: str) -> Optional[Personality]:
        """获取人格"""
        return self.personalities.get(name)
    
    def get_all(self) -> list[str]:
        """获取所有人格名称"""
        return list(self.personalities.keys())
    
    def get_random(self) -> Personality:
        """随机获取一个人格"""
        import random
        return random.choice(list(self.personalities.values()))
