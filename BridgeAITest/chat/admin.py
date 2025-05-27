from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import LLMProvider, ChatSession, ChatMessage
# Register your models here.
admin.site.register(ChatSession)
admin.site.register(ChatMessage)

@admin.register(LLMProvider)
class LLMProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "model", "is_active")
    list_editable = ("is_active",)