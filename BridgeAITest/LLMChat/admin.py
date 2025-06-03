from django.contrib import admin
from .models import ModelProvider, Tool, ChatLog

@admin.register(ModelProvider)
class ModelProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "model_name")
    

@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "enabled")

@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "input_tokens", "output_tokens", "total_tokens", "created_at")
    readonly_fields = ("provider", "system_prompt", "user_message", "ai_response",
                       "input_tokens", "output_tokens", "total_tokens", "created_at")
