from abc import ABC, abstractmethod
from typing import Dict, Any
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_cohere import ChatCohere
from langchain_huggingface import HuggingFaceEndpoint
from langchain_community.chat_models import (
    ChatOpenAI, 
    ChatAnthropic,
)
from langchain_openai import AzureChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from asgiref.sync import sync_to_async

class LLMProviderStrategy(ABC):
    """Abstract base class for LLM provider strategies."""
    
    @abstractmethod
    def create_chat_model(self, config: Dict[str, Any]) -> BaseChatModel:
        """Create and return a LangChain chat model instance."""
        pass

    @abstractmethod
    def get_token_usage(self, response: Any) -> Dict[str, int]:
        """Extract token usage from the model's response."""
        pass

class OpenAIStrategy(LLMProviderStrategy):
    def create_chat_model(self, config: Dict[str, Any]) -> BaseChatModel:
        return ChatOpenAI(
            model=config['model_name'],
            temperature=config['temperature'],
            max_tokens=config['max_tokens'],
            top_p=config['top_p'],
            openai_api_key=config['api_key'],
        )

    def get_token_usage(self, response: Any) -> Dict[str, int]:
        print(response)
        usage = response.response_metadata.get('token_usage')
        print("----------------     ")
        print(usage)
        print("----------------     ")
        return {
            'input_tokens': usage.get('prompt_tokens', 0),
            'output_tokens': usage.get('completion_tokens', 0),
            'total_tokens': usage.get('total_tokens', 0)
        }

class AnthropicStrategy(LLMProviderStrategy):
    def create_chat_model(self, config: Dict[str, Any]) -> BaseChatModel:
        return ChatAnthropic(
            model=config['model_name'],
            temperature=config['temperature'],
            max_tokens=config['max_tokens'],
            anthropic_api_key=config['api_key'],
        )

    def get_token_usage(self, response: Any) -> Dict[str, int]:
        # Anthropic provides usage in response headers
        usage = response.usage
        return {
            'input_tokens': usage.input_tokens,
            'output_tokens': usage.output_tokens,
            'total_tokens': usage.input_tokens + usage.output_tokens
        }

class CohereStrategy(LLMProviderStrategy):
    def create_chat_model(self, config: Dict[str, Any]) -> BaseChatModel:
        return ChatCohere(
            model=config['model_name'],
            temperature=config['temperature'],
            max_tokens=config['max_tokens'],
            cohere_api_key=config['api_key'],
        )

    def get_token_usage(self, response: Any) -> Dict[str, int]:
        tokens = response.usage_metadata
 
        return {
            'input_tokens': tokens.get('input_tokens', 0),
            'output_tokens': tokens.get('output_tokens', 0),
            'total_tokens': tokens.get('total_tokens', 0)
        }

class HuggingFaceStrategy(LLMProviderStrategy):
    
    def create_chat_model(self, config: Dict[str, Any]) -> BaseChatModel:
        print("----------------     ")
        print(config)
        print("----------------     ")
        llm = HuggingFaceEndpoint(
                repo_id=config['extra_settings'].get('api_base'),
                task="text-generation",
                max_new_tokens=config['max_tokens'],
                huggingfacehub_api_token=config['api_key'],
                temperature=config['temperature'],
            )
        return llm

    def get_token_usage(self, response: Any) -> Dict[str, int]:
        print("----------------     ")
        print(response)
        print("----------------     ")
        text = response.content
        estimated_tokens = len(text.split()) * 1.3  # rough estimate
        return {
            'input_tokens': 0,  # not provided by HF
            'output_tokens': int(estimated_tokens),
            'total_tokens': int(estimated_tokens)
        }

class AzureOpenAIStrategy(LLMProviderStrategy):
    def create_chat_model(self, config: Dict[str, Any]) -> BaseChatModel:
        return AzureChatOpenAI(
            deployment_name=config['model_name'],
            temperature=config['temperature'],
            max_tokens=config['max_tokens'],
            azure_endpoint=config['extra_settings']['api_base'],
            azure_api_key=config['api_key'],
            api_version=config['extra_settings'].get('api_version', '2023-05-15'),
        )

    def get_token_usage(self, response: Any) -> Dict[str, int]:
        usage = response.usage
        return {
            'input_tokens': usage.prompt_tokens,
            'output_tokens': usage.completion_tokens,
            'total_tokens': usage.total_tokens
        }

class GoogleStrategy(LLMProviderStrategy):
    def create_chat_model(self, config: Dict[str, Any]) -> BaseChatModel:
        return ChatGoogleGenerativeAI(
            model=config['model_name'],
            temperature=config['temperature'],
            max_output_tokens=config['max_tokens'],
            google_api_key=config['api_key'],
        )

    def get_token_usage(self, response: Any) -> Dict[str, int]:
        usage = response.usage
        return {
            'input_tokens': usage.get('prompt_tokens', 0),
            'output_tokens': usage.get('completion_tokens', 0),
            'total_tokens': usage.get('total_tokens', 0)
        }

class LLMProviderFactory:
    """Factory class for creating LLM provider strategies."""
    
    _strategies = {
        'openai': OpenAIStrategy(),
        'anthropic': AnthropicStrategy(),
        'cohere': CohereStrategy(),
        'huggingface': HuggingFaceStrategy(),
        'azure_openai': AzureOpenAIStrategy(),
        'google': GoogleStrategy(),
    }

    @classmethod
    async def get_strategy(cls, provider: str) -> LLMProviderStrategy:
        from .models import ModelProvider
        get_active_provider = sync_to_async(lambda: ModelProvider.objects.filter(is_active=True).first())
        active_provider = await get_active_provider()
        
        if not active_provider:
            raise ValueError("No active provider configured")
            
        if active_provider.provider != provider:
            raise ValueError(f"Requested provider {provider} does not match active provider {active_provider.provider}")
            
        strategy = cls._strategies.get(provider)
        if not strategy:
            raise ValueError(f"Unsupported provider: {provider}")
            
        return strategy

    @classmethod
    def register_strategy(cls, provider: str, strategy: LLMProviderStrategy):
        """Register a new provider strategy."""
        cls._strategies[provider] = strategy

async def attach_tools(llm):
    """Bind the enabled tools to the chat model."""
    tools = []
    # Add tools that are enabled in the database
    enabled_tools = await get_enabled_tools_sync()
    for tool_cfg in enabled_tools:
        if tool_cfg.name == 'add':
            tools.append(add)
        elif tool_cfg.name == 'get_current_time':
            tools.append(get_current_time)
    if tools:
        llm = llm.bind_tools(tools)
    return llm