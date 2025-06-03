from django.db import models
from django.core.exceptions import ValidationError

class ModelProvider(models.Model):
    """LLM Provider configuration (editable via admin)."""
    PROVIDER_CHOICES = [
        ('openai', 'OpenAI'),
        ('cohere', 'Cohere'),
        ('anthropic', 'Anthropic'),
        ('huggingface', 'HuggingFace'),
        ('azure_openai', 'Azure OpenAI'),
        ('google', 'Google PaLM/Gemini'),
    ]
    
    name = models.CharField(max_length=50, unique=True)
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    model_name = models.CharField(max_length=100)
    api_key = models.CharField(max_length=200)
    
    # Common model parameters
    temperature = models.FloatField(default=0.7)
    max_tokens = models.IntegerField(default=20)
    top_p = models.FloatField(default=1.0, help_text="Nucleus sampling parameter")
    
    # Provider-specific settings (stored as JSON)
    extra_settings = models.JSONField(default=dict, blank=True, 
                                    help_text="Additional provider-specific settings")
    
    # Control fields
    is_active = models.BooleanField(default=False)
    priority = models.IntegerField(default=0, help_text="Higher priority models are tried first")
    description = models.TextField(blank=True)
    
    # Cost tracking (per 1K tokens)
    input_cost_per_1k = models.DecimalField(max_digits=10, decimal_places=6, default=0.0)
    output_cost_per_1k = models.DecimalField(max_digits=10, decimal_places=6, default=0.0)

    class Meta:
        ordering = ['-priority', 'name']

    def __str__(self):
        return f"{self.name} ({self.provider})"

    def clean(self):
        """Validate provider-specific requirements."""
        if self.provider == 'azure_openai' and 'api_base' not in self.extra_settings:
            raise ValidationError({'extra_settings': 'Azure OpenAI requires api_base URL'})
        
        if self.provider == 'huggingface' and 'api_base' not in self.extra_settings:
            raise ValidationError({'extra_settings': 'HuggingFace requires api_base URL'})

class Tool(models.Model):
    """Metadata for a custom tool (Python function) that LLM can call."""
    name = models.CharField(max_length=100, unique=True)  # tool identifier
    description = models.TextField()
    enabled = models.BooleanField(default=True)
    # (Optionally) store code reference or arguments schema; for simplicity, we assume tools are defined in code.

    def __str__(self):
        return self.name
    

class Conversation(models.Model):
    """Represents a chat conversation session."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=200, blank=True)
    system_prompt = models.TextField(blank=True)
    
    def __str__(self):
        return f"Conversation {self.id} - {self.title or 'Untitled'}"

class ChatLog(models.Model):
    """Stores each chat request/response and token usage."""
    provider = models.ForeignKey(ModelProvider, on_delete=models.PROTECT)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    system_prompt = models.TextField()
    user_message = models.TextField()
    ai_response = models.TextField()
    input_tokens = models.IntegerField()
    output_tokens = models.IntegerField()
    total_tokens = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"ChatLog {self.id} with {self.provider.name} at {self.created_at}"