from rest_framework import serializers

class ChatRequestSerializer(serializers.Serializer):
    session_id = serializers.UUIDField(required=False)
    message = serializers.CharField()

class ChatResponseSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    response = serializers.CharField()
    tokens_prompt = serializers.IntegerField(required=False)
    tokens_completion = serializers.IntegerField(required=False)
    tokens_total = serializers.IntegerField(required=False)
    cost = serializers.FloatField(required=False)
