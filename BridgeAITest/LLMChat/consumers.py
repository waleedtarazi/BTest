import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .services import ChatService
from .models import ModelProvider
from asgiref.sync import sync_to_async
from django.core.exceptions import ValidationError

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handle WebSocket connection."""
        await self.accept()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        pass

    async def get_provider(self, provider_id=None):
        """Get the LLM provider."""
        if provider_id:
            try:
                return await sync_to_async(ModelProvider.objects.get)(id=provider_id, is_active=True)
            except ModelProvider.DoesNotExist:
                raise ValidationError("Invalid or inactive provider_id")
        
        provider = await sync_to_async(
            lambda: ModelProvider.objects.filter(is_active=True).order_by('-priority').first()
        )()
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
                async for chunk in chat_service.chat_stream(**chat_params):
                    if chunk:
                        await self.send(json.dumps({
                            'type': 'chat.message',
                            'chunk': chunk
                        }))
                
                # Send completion message
                await self.send(json.dumps({
                    'type': 'chat.complete'
                }))
            else:
                # Send complete response at once
                response = await chat_service.chat(**chat_params)
                await self.send(json.dumps({
                    'type': 'chat.message',
                    'provider': {
                        'id': provider.id,
                        'name': provider.name,
                        'model': provider.model_name
                    },
                    'conversation_id': response['conversation_id'],
                    'reply': response['reply'],
                    'usage': response['usage']
                }))

        except ValidationError as e:
            await self.send(json.dumps({
                'error': str(e)
            }))
        except Exception as e:
            await self.send(json.dumps({
                'error': f'An unexpected error occurred: {str(e)}'
            })) 