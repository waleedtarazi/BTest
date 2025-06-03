from rest_framework import serializers
from .models import Conversation, ChatLog

class ChatRequestSerializer(serializers.Serializer):
    """Serializer for chat requests."""
    message = serializers.CharField(required=True)
    system_prompt = serializers.CharField(required=False, allow_blank=True)
    provider_id = serializers.IntegerField(required=False)
    use_tools = serializers.BooleanField(required=False, default=False)
    conversation_id = serializers.IntegerField(required=False)
    stream = serializers.BooleanField(required=False, default=False)

class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ['id', 'title', 'system_prompt', 'created_at', 'updated_at']

class ChatLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatLog
        fields = ['id', 'user_message', 'ai_response', 'created_at']

    
