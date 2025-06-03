from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
import logging
from typing import Optional
from asgiref.sync import async_to_sync
from django.shortcuts import render

from .serializers import ChatRequestSerializer, ConversationSerializer, ChatLogSerializer
from .services import ChatService, get_active_provider
from .models import ModelProvider, Conversation, ChatLog
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)

def chat_test_view(request):
    """Render the chat test interface."""
    return render(request, 'chat.html')

class ConversationAPIView(APIView):
    """API endpoint for managing conversations."""
    authentication_classes = []  # Disable authentication for testing
    permission_classes = []      # Disable permissions for testing
    
    def get(self, request, conversation_id=None):
        """Get conversation details and history."""
        try:
            if conversation_id:
                conversation = Conversation.objects.get(id=conversation_id)
                messages = ChatLog.objects.filter(conversation_id=conversation_id)
                
                return Response({
                    'conversation': ConversationSerializer(conversation).data,
                    'messages': ChatLogSerializer(messages, many=True).data
                })
            else:
                conversations = Conversation.objects.all().order_by('-updated_at')
                return Response(ConversationSerializer(conversations, many=True).data)
                
        except Conversation.DoesNotExist:
            return Response(
                {"error": "Conversation not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in ConversationAPIView: {str(e)}", exc_info=True)
            return Response(
                {"error": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ChatAPIView(APIView):
    """API endpoint for non-streaming chat interactions."""
    authentication_classes = []  # Disable authentication for testing
    permission_classes = []      # Disable permissions for testing
    
    def get_provider(self, provider_id: Optional[int] = None) -> ModelProvider:
        """Get the LLM provider based on ID or default active provider."""
        if provider_id:
            try:
                return ModelProvider.objects.get(id=provider_id, is_active=True)
            except ModelProvider.DoesNotExist:
                raise ValidationError("Invalid or inactive provider_id")
        
        provider = ModelProvider.objects.filter(is_active=True).order_by('-priority').first()
        if not provider:
            raise ValidationError("No active LLM provider configured")
        return provider

    def post(self, request):
        """Handle non-streaming chat requests."""
        try:
            # Validate request data
            serializer = ChatRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"error": "Invalid request", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            data = serializer.validated_data
            
            # Get provider configuration
            try:
                provider = self.get_provider(data.get('provider_id'))
            except ValidationError as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Initialize chat service
            chat_service = ChatService(provider)
            
            # Prepare chat parameters
            chat_params = {
                'message': data['message'],
                'system_prompt': data.get('system_prompt'),
                'conversation_id': data.get('conversation_id')
            }
            
            # Process chat message using async_to_sync
            chat_method = async_to_sync(chat_service.chat)
            response = chat_method(**chat_params)
            
            return Response({
                'provider': {
                    'id': provider.id,
                    'name': provider.name,
                    'model': provider.model_name
                },
                'conversation_id': response['conversation_id'],
                'reply': response['reply'],
                'usage': response['usage']
            })
                
        except Exception as e:
            logger.error(f"Unexpected error in ChatAPIView: {str(e)}", exc_info=True)
            return Response(
                {"error": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
