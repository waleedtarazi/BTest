import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .services import ChatService, get_active_provider
from .models import ModelProvider
from asgiref.sync import sync_to_async
from django.core.exceptions import ValidationError
from channels.layers import get_channel_layer
import logging

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handle WebSocket connection."""
        await self.accept()
        # Add to chat group
        await self.channel_layer.group_add("chat_group", self.channel_name)

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Remove from chat group
        await self.channel_layer.group_discard("chat_group", self.channel_name)

    async def get_provider(self, provider_id=None):
        """Get the LLM provider."""
        if provider_id:
            try:
                return await sync_to_async(ModelProvider.objects.get)(id=provider_id, is_active=True)
            except ModelProvider.DoesNotExist:
                raise ValidationError("Invalid or inactive provider_id")
        
        provider = await get_active_provider()
        if not provider:
            raise ValidationError("No active LLM provider configured")
        return provider

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message = data.get('message')
            provider_id = data.get('provider_id')
            system_prompt = data.get('system_prompt')
            conversation_id = data.get('conversation_id')
            stream = data.get('stream', True)  # Default to streaming for WebSocket
            enable_tts = data.get('enable_tts', True)  # New parameter for TTS

            if not message:
                await self.send(json.dumps({
                    'error': 'Message is required'
                }))
                return

            # Get provider and initialize chat service
            provider = await self.get_provider(provider_id)
            chat_service = ChatService(provider)

            chat_params = {
                'message': message,
                'system_prompt': system_prompt,
                'conversation_id': conversation_id
            }

            if stream:
                # Stream the response
                accumulated_text = ""  # Accumulate text for TTS
                async for chunk in chat_service.chat_stream(**chat_params):
                    if chunk:
                        accumulated_text += chunk
                        await self.send(json.dumps({
                            'type': 'chat.message',
                            'chunk': chunk
                        }))
                        
                        # Send to TTS if enabled and we have a complete sentence
                        if enable_tts and any(char in accumulated_text for char in '!.?'):
                            # Send accumulated text to audio group
                            channel_layer = get_channel_layer()
                            print(f"SENDIG to TTS: {accumulated_text}")
                            await channel_layer.group_send(
                                "audio_group",
                                {
                                    "type": "tts.text",
                                    "text": accumulated_text
                                }
                            )
                            accumulated_text = ""  # Reset accumulator
                
                # Send any remaining text to TTS
                if enable_tts and accumulated_text:
                    channel_layer = get_channel_layer()
                    
                    await channel_layer.group_send(
                        "audio_group",
                        {
                            "type": "tts.text",
                            "text": accumulated_text
                        }
                    )
                
                # Send completion messages
                await self.send(json.dumps({
                    'type': 'chat.complete'
                }))
                if enable_tts:
                    await channel_layer.group_send(
                        "audio_group",
                        {
                            "type": "tts.complete"
                        }
                    )
            else:
                # Send complete response at once
                response = await chat_service.chat(**chat_params)
                response_data = {
                    'type': 'chat.message',
                    'provider': {
                        'id': provider.id,
                        'name': provider.name,
                        'model': provider.model_name
                    },
                    'conversation_id': response['conversation_id'],
                    'reply': response['reply'],
                    'usage': response['usage']
                }
                await self.send(json.dumps(response_data))
                
                # Send to TTS if enabled
                if enable_tts:
                    channel_layer = get_channel_layer()
                    await channel_layer.group_send(
                        "audio_group",
                        {
                            "type": "tts.text",
                            "text": response['reply']
                        }
                    )
                    await channel_layer.group_send(
                        "audio_group",
                        {
                            "type": "tts.complete"
                        }
                    )

        except ValidationError as e:
            await self.send(json.dumps({
                'error': str(e)
            }))
        except Exception as e:
            await self.send(json.dumps({
                'error': f'An unexpected error occurred: {str(e)}'
            })) 