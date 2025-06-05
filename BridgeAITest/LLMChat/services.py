# TODO:
# look for the correct way to call a ChatModel depending on the provider
from langchain_community.chat_models import ChatOpenAI, ChatAnthropic
from langchain_huggingface import HuggingFaceEndpoint
from langchain_cohere import ChatCohere
from .models import ModelProvider, Conversation, ChatLog, Tool
from typing import List, Dict, Any, Optional, AsyncGenerator
from langchain_core.tools import BaseTool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from .llm_providers import LLMProviderFactory
from asgiref.sync import sync_to_async
import logging

logger = logging.getLogger(__name__)

# Create async versions of database operations
create_chat_log = sync_to_async(ChatLog.objects.create)
get_conversation = sync_to_async(Conversation.objects.get)
create_conversation = sync_to_async(Conversation.objects.create)
get_chat_history = sync_to_async(lambda conv_id: list(ChatLog.objects.filter(conversation_id=conv_id)))
get_enabled_tools_sync = sync_to_async(lambda: list(Tool.objects.filter(enabled=True)))

async def get_chat_model(provider: ModelProvider):
    """Instantiate the LangChain chat model for the given provider config."""
    try:
        if provider.provider == 'openai':
            llm = ChatOpenAI(
                model=provider.model_name,
                temperature=provider.temperature,
                openai_api_key=provider.api_key
            )
        elif provider.provider == 'anthropic':
            llm = ChatAnthropic(
                model=provider.model_name,
                temperature=provider.temperature,
                anthropic_api_key=provider.api_key
            )
        elif provider.provider == 'cohere':
            llm = ChatCohere(
                model=provider.model_name,
                temperature=provider.temperature,
                cohere_api_key=provider.api_key
            )
        elif provider.provider == 'huggingface':
            llm = HuggingFaceEndpoint(
                repo_id=provider.extra_settings.get('api_base'),
                task="text-generation",
                max_new_tokens=provider.max_tokens,
                huggingfacehub_api_token=provider.api_key,
                temperature=provider.temperature)
        else:
            raise ValueError(f"Unsupported provider: {provider.provider}")
        
        # Attach tools if enabled
        return await attach_tools(llm)
    except Exception as e:
        logger.error(f"Error initializing chat model: {str(e)}")
        raise


from LLMChat.tools import add, get_current_time
from .models import Tool
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

class ChatService:
    """Main service for handling chat operations."""
    
    def __init__(self, provider: ModelProvider):
        self.provider = provider
        self.strategy = None  # Will be initialized lazily
        self.llm = None  # Will be initialized lazily
        
    async def _ensure_llm(self):
        """Ensure LLM is initialized."""
        if self.llm is None:
            if self.strategy is None:
                self.strategy = await LLMProviderFactory.get_strategy(self.provider.provider)
            self.llm = await get_chat_model(self.provider)
    
    async def get_conversation_history(self, conversation_id: int) -> List[dict]:
        """Get the chat history for a conversation."""
        chat_logs = await get_chat_history(conversation_id)
        messages = []
        for log in chat_logs:
            messages.extend([
                HumanMessage(content=log.user_message),
                AIMessage(content=log.ai_response)
            ])
        return messages

    async def prepare_messages(self, message: str, conversation_id: Optional[int] = None, system_prompt: Optional[str] = None) -> List[Any]:
        """Prepare messages for chat."""
        ## TODO: i guess it's better to store the conversation in the session(cache)
        try:
            # Get or create conversation
            conversation = None
            if conversation_id:
                try:
                    conversation = await get_conversation(id=conversation_id)
                except Exception as e:
                    logger.error(f"Error getting conversation {conversation_id}: {str(e)}")
                    conversation = None
            
            if not conversation:
                conversation = await create_conversation(system_prompt=system_prompt or "")
            
            # Prepare messages
            messages = []
            if system_prompt or conversation.system_prompt:
                messages.append(SystemMessage(content=system_prompt or conversation.system_prompt))
            
            # Add conversation history
            history_messages = await self.get_conversation_history(conversation.id)
            messages.extend(history_messages)
            
            # Add current message
            messages.append(HumanMessage(content=message))
            
            return messages, conversation
        except Exception as e:
            logger.error(f"Error preparing messages: {str(e)}", exc_info=True)
            raise

    async def chat_stream(self, message: str, conversation_id: Optional[int] = None, system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream the chat response."""
        conversation = None
        try:
            await self._ensure_llm()
            messages, conversation = await self.prepare_messages(message, conversation_id, system_prompt)
            full_response = []
            async for chunk in self.llm.astream(messages):
                if chunk.content:
                    full_response.append(chunk.content)
                    yield chunk.content
            
            # Log the chat after completion
            print(f"CHAT-FULL-RESPONSE: {full_response}")
            await create_chat_log(
                provider=self.provider,
                conversation=conversation,
                system_prompt=system_prompt or conversation.system_prompt or "",
                user_message=message,
                ai_response="".join(full_response),
                input_tokens=0,  # Token counting for streaming responses
                output_tokens=0,
                total_tokens=0
            )
            
        except Exception as e:
            logger.error(f"Error in chat_stream: {str(e)}", exc_info=True)
            error_message = f"Error: {str(e)}"
            yield error_message
            
            # Only try to log if we have a conversation
            if conversation:
                # Log error in chat history
                await create_chat_log(
                    provider=self.provider,
                    conversation=conversation,
                    system_prompt=system_prompt or conversation.system_prompt or "",
                    user_message=message,
                    ai_response=error_message,
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0
                )

    async def chat(self, message: str, conversation_id: Optional[int] = None, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Process a chat message and return the response."""
        try:
            await self._ensure_llm()
            messages, conversation = await self.prepare_messages(message, conversation_id, system_prompt)
            
            # Get response
            response = await self.llm.ainvoke(messages)
            
            # Extract usage statistics
            usage = self.strategy.get_token_usage(response)
            
            # Log the chat
            await create_chat_log(
                provider=self.provider,
                conversation=conversation,
                system_prompt=system_prompt or conversation.system_prompt or "",
                user_message=message,
                ai_response=response.content,
                input_tokens=usage['input_tokens'],
                output_tokens=usage['output_tokens'],
                total_tokens=usage['total_tokens']
            )
            
            return {
                'reply': response.content,
                'usage': usage,
                'conversation_id': conversation.id
            }
            
        except Exception as e:
            logger.error(f"Error in chat: {str(e)}", exc_info=True)
            raise

# Update the get_active_provider function
get_active_provider = sync_to_async(lambda: ModelProvider.objects.filter(is_active=True).order_by('-priority').first())

async def get_enabled_tools() -> List[BaseTool]:
    """Get all enabled tools from the database."""
    from .tools import TOOL_REGISTRY
    
    tools = []
    tool_configs = await get_enabled_tools_sync()
    for tool_config in tool_configs:
        if tool_config.name in TOOL_REGISTRY:
            tools.append(TOOL_REGISTRY[tool_config.name])
    return tools