from django.urls import re_path
from . import consumers
from . import audio_consumers
from . import tts_consumer

websocket_urlpatterns = [
    re_path(r'ws/chat/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/audio/$', audio_consumers.AudioTranscriptionConsumer.as_asgi()),
    re_path(r'ws/voice/$', tts_consumer.TTSConsumer.as_asgi()), 
] 