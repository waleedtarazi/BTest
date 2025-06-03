from django.urls import path
from .views import ChatAPIView, ConversationAPIView
from .views import chat_test_view

urlpatterns = [
    path('chat/', ChatAPIView.as_view(), name='chat'),
    path('conversations/', ConversationAPIView.as_view(), name='conversations-list'),
    path('conversations/<int:conversation_id>/', ConversationAPIView.as_view(), name='conversation-detail'),
    path('test/', chat_test_view, name='chat-test'),
]
