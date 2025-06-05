import json
import asyncio
import websockets
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
import logging
import threading

logger = logging.getLogger(__name__)

class AudioTranscriptionConsumer(AsyncWebsocketConsumer):
    """Consumer for converting audio to text using Deepgram."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._deepgram_ws = None
        self._exit = threading.Event()

    async def connect(self):
        """Initialize WebSocket connection and connect to Deepgram."""
        try:
            await self.accept()
            
            if not hasattr(settings, 'DEEPGRAM_API_KEY'):
                raise ValueError("DEEPGRAM_API_KEY not found in settings")
            
            # Connect to Deepgram WebSocket
            deepgram_url = "wss://api.deepgram.com/v1/listen?encoding=linear16&sample_rate=16000"
            self._deepgram_ws = await websockets.connect(
                deepgram_url,
                additional_headers={"Authorization": f"Token {settings.DEEPGRAM_API_KEY}"}
            )

            # Start receiving transcriptions
            self._transcription_task = asyncio.create_task(self._receive_transcription())
            
            logger.info("Audio transcription connection established")
            await self.send(json.dumps({'status': 'ready'}))
            
        except Exception as e:
            logger.error(f"Failed to initialize audio transcription: {str(e)}")
            await self.cleanup()
            await self.close()

    async def disconnect(self, close_code):
        """Clean up WebSocket connections."""
        await self.cleanup()

    async def receive(self, text_data=None, bytes_data=None):
        """Handle incoming audio data and forward to Deepgram."""
        try:
            if bytes_data and self._deepgram_ws and not self._exit.is_set():
                await self._deepgram_ws.send(bytes_data)
        except Exception as e:
            logger.error(f"Error processing audio data: {str(e)}")
            await self.close()

    async def _receive_transcription(self):
        """Process transcription results from Deepgram."""
        try:
            while not self._exit.is_set() and self._deepgram_ws:
                message = await self._deepgram_ws.recv()
                data = json.loads(message)
                
                if 'channel' in data:
                    transcript = data['channel']['alternatives'][0]['transcript']
                    if transcript.strip():
                        await self.send(json.dumps({
                            'text': transcript
                        }))
                        
        except websockets.exceptions.ConnectionClosed:
            if not self._exit.is_set():
                logger.info("Deepgram connection closed unexpectedly")
        except asyncio.CancelledError:
            logger.info("Transcription task cancelled")
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
        finally:
            if not self._exit.is_set():
                await self.cleanup()
                await self.close()

    async def cleanup(self):
        """Clean up resources."""
        self._exit.set()
        
        if hasattr(self, '_transcription_task'):
            self._transcription_task.cancel()
            try:
                await self._transcription_task
            except asyncio.CancelledError:
                pass

        if self._deepgram_ws:
            await self._deepgram_ws.close()
            self._deepgram_ws = None 