from abc import ABC, abstractmethod
from typing import Optional


class TTSInterface(ABC):
    """
    TTS 接口抽象类
    
    定义文本转语音服务的统一接口
    """
    
    @abstractmethod
    def speak(self, text: str, voice: Optional[str] = None) -> bool:
        """
        播放文本
        
        Args:
            text: 要播放的文本
            voice: 语音类型（可选）
            
        Returns:
            是否成功播放
        """
        pass
    
    @abstractmethod
    def save_audio(self, text: str, filepath: str, voice: Optional[str] = None) -> bool:
        """
        保存音频到文件
        
        Args:
            text: 要转换的文本
            filepath: 输出文件路径
            voice: 语音类型（可选）
            
        Returns:
            是否成功保存
        """
        pass


class MockTTS(TTSInterface):
    """
    模拟 TTS 实现（用于测试）
    """
    
    def speak(self, text: str, voice: Optional[str] = None) -> bool:
        """
        模拟播放文本
        
        Args:
            text: 要播放的文本
            voice: 语音类型（可选）
            
        Returns:
            是否成功播放
        """
        print(f"[TTS] {text}")
        return True
    
    def save_audio(self, text: str, filepath: str, voice: Optional[str] = None) -> bool:
        """
        模拟保存音频到文件
        
        Args:
            text: 要转换的文本
            filepath: 输出文件路径
            voice: 语音类型（可选）
            
        Returns:
            是否成功保存
        """
        print(f"[TTS] Saving '{text}' to {filepath}")
        return True


class SystemTTS(TTSInterface):
    """
    系统 TTS 实现（Windows）
    """
    
    def __init__(self):
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            # 获取可用的声音
            self.voices = self.engine.getProperty('voices')
        except ImportError:
            print("Warning: pyttsx3 not installed. Install with 'pip install pyttsx3'")
            self.engine = None
    
    def speak(self, text: str, voice: Optional[str] = None) -> bool:
        """
        播放文本
        
        Args:
            text: 要播放的文本
            voice: 语音类型（可选）
            
        Returns:
            是否成功播放
        """
        if not self.engine:
            print(f"[TTS] {text}")
            return False
            
        try:
            if voice:
                # 尝试设置声音
                for v in self.voices:
                    if voice.lower() in v.name.lower():
                        self.engine.setProperty('voice', v.id)
                        break
            
            self.engine.say(text)
            self.engine.runAndWait()
            return True
        except Exception as e:
            print(f"TTS Error: {e}")
            return False
    
    def save_audio(self, text: str, filepath: str, voice: Optional[str] = None) -> bool:
        """
        保存音频到文件
        
        Args:
            text: 要转换的文本
            filepath: 输出文件路径
            voice: 语音类型（可选）
            
        Returns:
            是否成功保存
        """
        if not self.engine:
            print(f"[TTS] Cannot save audio without pyttsx3")
            return False
            
        try:
            if voice:
                # 尝试设置声音
                for v in self.voices:
                    if voice.lower() in v.name.lower():
                        self.engine.setProperty('voice', v.id)
                        break
            
            self.engine.save_to_file(text, filepath)
            self.engine.runAndWait()
            return True
        except Exception as e:
            print(f"TTS Save Error: {e}")
            return False