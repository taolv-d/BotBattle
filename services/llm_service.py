from typing import Dict, Any, Optional, List
import json


class LLMService:
    """
    LLM 服务类
    
    提供大语言模型交互服务的抽象接口
    """
    
    def __init__(self, model_config: Dict[str, Any]):
        """
        初始化 LLM 服务
        
        Args:
            model_config: 模型配置
        """
        self.model_config = model_config
        self.provider = model_config.get("provider", "mock")
        self.model_params = model_config.get("params", {})
        
        # 根据配置初始化对应的 LLM 提供商
        if self.provider == "openai":
            self._init_openai()
        elif self.provider == "anthropic":
            self._init_anthropic()
        elif self.provider == "ollama":
            self._init_ollama()
        else:
            # 默认使用模拟实现
            self.provider_instance = MockLLM()
    
    def _init_openai(self):
        """初始化 OpenAI 服务"""
        try:
            import openai
            api_key = self.model_config.get("api_key")
            if not api_key:
                raise ValueError("OpenAI API key is required")
            
            openai.api_key = api_key
            self.provider_instance = OpenAILLM(self.model_config)
        except ImportError:
            print("Warning: openai package not installed. Using mock implementation.")
            self.provider_instance = MockLLM()
        except Exception as e:
            print(f"Error initializing OpenAI: {e}. Using mock implementation.")
            self.provider_instance = MockLLM()
    
    def _init_anthropic(self):
        """初始化 Anthropic 服务"""
        try:
            import anthropic
            api_key = self.model_config.get("api_key")
            if not api_key:
                raise ValueError("Anthropic API key is required")
            
            client = anthropic.Anthropic(api_key=api_key)
            self.provider_instance = AnthropicLLM(client, self.model_config)
        except ImportError:
            print("Warning: anthropic package not installed. Using mock implementation.")
            self.provider_instance = MockLLM()
        except Exception as e:
            print(f"Error initializing Anthropic: {e}. Using mock implementation.")
            self.provider_instance = MockLLM()
    
    def _init_ollama(self):
        """初始化 Ollama 服务"""
        try:
            import ollama
            self.provider_instance = OllamaLLM(ollama, self.model_config)
        except ImportError:
            print("Warning: ollama package not installed. Using mock implementation.")
            self.provider_instance = MockLLM()
        except Exception as e:
            print(f"Error initializing Ollama: {e}. Using mock implementation.")
            self.provider_instance = MockLLM()
    
    async def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        生成响应
        
        Args:
            prompt: 输入提示
            context: 上下文信息
            
        Returns:
            生成的响应文本
        """
        return await self.provider_instance.generate_response(prompt, context)
    
    async def generate_structured_output(self, prompt: str, schema: Dict[str, Any], 
                                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        生成结构化输出
        
        Args:
            prompt: 输入提示
            schema: 输出模式
            context: 上下文信息
            
        Returns:
            结构化输出字典
        """
        return await self.provider_instance.generate_structured_output(prompt, schema, context)


class BaseLLMProvider:
    """LLM 提供商基类"""
    
    async def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """生成响应"""
        raise NotImplementedError
    
    async def generate_structured_output(self, prompt: str, schema: Dict[str, Any], 
                                       context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成结构化输出"""
        raise NotImplementedError


class MockLLM(BaseLLMProvider):
    """模拟 LLM 实现（用于测试）"""
    
    async def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """模拟生成响应"""
        # 根据提示内容返回模拟响应
        if "夜晚行动" in prompt or "night" in prompt.lower():
            return '{"action": "skip", "target": null}'
        elif "发言" in prompt or "speech" in prompt.lower():
            return "这是一个模拟发言。"
        elif "投票" in prompt or "vote" in prompt.lower():
            return '{"target": 1}'
        else:
            return "这是来自模拟LLM的响应。"
    
    async def generate_structured_output(self, prompt: str, schema: Dict[str, Any], 
                                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """模拟生成结构化输出"""
        # 返回符合模式的模拟数据
        if "target" in schema.get("properties", {}):
            return {"target": 1}
        elif "action" in schema.get("properties", {}):
            return {"action": "skip"}
        else:
            return {}


class OpenAILLM(BaseLLMProvider):
    """OpenAI LLM 实现"""
    
    def __init__(self, config: Dict[str, Any]):
        self.client = None  # 由外部传入
        self.model = config.get("model", "gpt-3.5-turbo")
        self.temperature = config.get("temperature", 0.7)
    
    async def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """生成响应"""
        import asyncio
        loop = asyncio.get_event_loop()
        
        # 在线程池中运行同步调用
        response = await loop.run_in_executor(None, lambda: self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature
        ))
        
        return response.choices[0].message.content
    
    async def generate_structured_output(self, prompt: str, schema: Dict[str, Any], 
                                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成结构化输出"""
        import asyncio
        loop = asyncio.get_event_loop()
        
        # 使用函数调用获取结构化输出
        response = await loop.run_in_executor(None, lambda: self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            functions=[{
                "name": "extract_info",
                "description": "Extract structured information",
                "parameters": schema
            }],
            function_call={"name": "extract_info"},
            temperature=self.temperature
        ))
        
        # 解析函数参数
        function_call = response.choices[0].message.function_call
        if function_call:
            return json.loads(function_call.arguments)
        else:
            return {}


class AnthropicLLM(BaseLLMProvider):
    """Anthropic LLM 实现"""
    
    def __init__(self, client, config: Dict[str, Any]):
        self.client = client
        self.model = config.get("model", "claude-3-haiku-20240307")
        self.temperature = config.get("temperature", 0.7)
    
    async def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """生成响应"""
        import asyncio
        loop = asyncio.get_event_loop()
        
        # 在线程池中运行同步调用
        response = await loop.run_in_executor(None, lambda: self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}]
        ))
        
        return response.content[0].text
    
    async def generate_structured_output(self, prompt: str, schema: Dict[str, Any], 
                                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成结构化输出"""
        # Anthropic 没有原生的函数调用，需要手动解析JSON
        import asyncio
        import json
        loop = asyncio.get_event_loop()
        
        formatted_prompt = f"{prompt}\n\n请严格按照以下JSON格式返回结果：\n{json.dumps(schema)}"
        
        response = await loop.run_in_executor(None, lambda: self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            temperature=0.1,  # 低温度确保格式准确
            messages=[{"role": "user", "content": formatted_prompt}]
        ))
        
        try:
            # 尝试从响应中提取JSON
            content = response.content[0].text
            # 查找JSON部分
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return {}
        except json.JSONDecodeError:
            return {}


class OllamaLLM(BaseLLMProvider):
    """Ollama LLM 实现"""
    
    def __init__(self, ollama_client, config: Dict[str, Any]):
        self.ollama = ollama_client
        self.model = config.get("model", "llama2")
        self.options = config.get("options", {})
    
    async def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """生成响应"""
        import asyncio
        loop = asyncio.get_event_loop()
        
        # 在线程池中运行同步调用
        response = await loop.run_in_executor(None, lambda: self.ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            options=self.options
        ))
        
        return response['message']['content']
    
    async def generate_structured_output(self, prompt: str, schema: Dict[str, Any], 
                                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成结构化输出"""
        import asyncio
        import json
        loop = asyncio.get_event_loop()
        
        formatted_prompt = f"{prompt}\n\n请严格按照以下JSON格式返回结果：\n{json.dumps(schema)}"
        
        response = await loop.run_in_executor(None, lambda: self.ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": formatted_prompt}],
            options={**self.options, "temperature": 0.1}  # 低温度确保格式准确
        ))
        
        try:
            # 尝试从响应中提取JSON
            content = response['message']['content']
            # 查找JSON部分
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return {}
        except json.JSONDecodeError:
            return {}