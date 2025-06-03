from django.db import models

# Create your models here.
class LLMProvider(models.Model):
    name = models.CharField(max_length=50)
    model = models.CharField(max_length=100) ## model name/repo
    api_key = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=False)
    # provider field(coher, openAI)
    
    def __str__(self):
        return f"name: {self.name}, model: {self.model}"
    

from django.utils import timezone
import uuid

class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now)
    
class ChatMessage(models.Model):
    ROLE_CHOICES = [("user", "User"), ("assistant", "Assistant")]
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    
    tokens_prompt = models.IntegerField(null=True, blank=True)
    tokens_completion = models.IntegerField(null=True, blank=True)
    tokens_total = models.IntegerField(null=True, blank=True)
    cost = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(default= timezone.now)