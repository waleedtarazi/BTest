"""WebSocket consumer for text-to-speech streaming using Deepgram."""
import json
import os
import threading
import queue
import logging
from typing import Optional
import pyaudio
from websockets.sync.client import connect
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Audio constants
TIMEOUT = 0.050
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 48000
CHUNK = 8000

# Deepgram constants
DEFAULT_URL = f"wss://api.deepgram.com/v1/speak?model=aura-2-thalia-en&encoding=linear16&sample_rate={RATE}"

class Speaker:
    _audio: pyaudio.PyAudio
    _chunk: int
    _rate: int
    _format: int
    _channels: int
    _output_device_index: int

    _stream: pyaudio.Stream
    _thread: threading.Thread
    _queue: queue.Queue
    _exit: threading.Event

    def __init__(
        self,
        rate: int = RATE,
        chunk: int = CHUNK,
        channels: int = CHANNELS,
        output_device_index: int = None,
    ):
        self._exit = threading.Event()
        self._queue = queue.Queue()

        self._audio = pyaudio.PyAudio()
        self._chunk = chunk
        self._rate = rate
        self._format = FORMAT
        self._channels = channels
        self._output_device_index = output_device_index

        # Log available devices
        device_count = self._audio.get_device_count()
        logger.info(f"Found {device_count} audio devices:")
        for i in range(device_count):
            try:
                dev = self._audio.get_device_info_by_index(i)
                logger.info(f"Device {i}: {dev['name']} (Channels: {dev['maxOutputChannels']}, Rate: {dev['defaultSampleRate']})")
            except Exception as e:
                logger.error(f"Error getting device {i} info: {e}")

    def start(self) -> bool:
        try:
            self._stream = self._audio.open(
                format=self._format,
                channels=self._channels,
                rate=self._rate,
                input=False,
                output=True,
                frames_per_buffer=self._chunk,
                output_device_index=self._output_device_index,
            )

            self._exit.clear()

            self._thread = threading.Thread(
                target=self._play_audio,
                args=(self._queue, self._stream, self._exit),
                daemon=True
            )
            self._thread.start()

            self._stream.start_stream()
            logger.info("Audio system started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start audio: {e}")
            return False

    def stop(self):
        self._exit.set()

        if self._stream is not None:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None

        if self._thread is not None:
            self._thread.join()
            self._thread = None

        if self._audio is not None:
            self._audio.terminate()
            self._audio = None

        self._queue = None

    def play(self, data):
        if self._queue and not self._exit.is_set():
            self._queue.put(data)

    def _play_audio(self, audio_queue: queue.Queue, stream: pyaudio.Stream, stop_event: threading.Event) -> None:
        logger.info("Audio playback thread started")
        while not stop_event.is_set():
            try:
                data = audio_queue.get(timeout=TIMEOUT)
                if data:
                    stream.write(data)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Audio playback error: {e}")
                break
        logger.info("Audio playback thread stopping")

class TTSConsumer(AsyncWebsocketConsumer):
    """Consumer for handling text-to-speech streaming using Deepgram."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._speaker: Optional[Speaker] = None
        self._deepgram_ws = None
        self._exit = threading.Event()
        self._receiver_thread = None

    async def connect(self) -> None:
        try:
            logger.info("New WebSocket connection request received")
            await self.accept()
            logger.info("WebSocket connection accepted")
            
            if not hasattr(settings, 'DEEPGRAM_API_KEY'):
                raise ValueError("DEEPGRAM_API_KEY not found in settings")

            # Initialize audio system
            logger.info("Initializing audio system...")
            self._speaker = Speaker()
            if not self._speaker.start():
                raise RuntimeError("Failed to initialize audio output")
            logger.info("Audio system initialized successfully")

            # Start Deepgram receiver thread
            self._receiver_thread = threading.Thread(
                target=self._setup_deepgram,
                daemon=True
            )
            self._receiver_thread.start()
            logger.info("Deepgram connection thread started")
            
            await self.send(json.dumps({'status': 'ready'}))

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            await self.close()

    def _setup_deepgram(self) -> None:
        try:
            # Connect to Deepgram
            logger.info(f"Connecting to Deepgram at {DEFAULT_URL}")
            self._deepgram_ws = connect(
                DEFAULT_URL,
                additional_headers={
                    "Authorization": f"Token {settings.DEEPGRAM_API_KEY}"
                }
            )
            logger.info("Successfully connected to Deepgram")
            
            # Start receiving messages
            while not self._exit.is_set():
                try:
                    message = self._deepgram_ws.recv()
                    if message is None:
                        continue

                    if isinstance(message, str):
                        try:
                            data = json.loads(message)
                            logger.debug(f"Received text message from Deepgram: {data}")
                        except json.JSONDecodeError:
                            logger.warning(f"Received invalid JSON from Deepgram: {message[:100]}")
                    elif isinstance(message, bytes) and self._speaker:
                        logger.debug(f"Received {len(message)} bytes of audio data")
                        self._speaker.play(message)
                    else:
                        logger.warning(f"Received unexpected message type: {type(message)}")
                        
                except Exception as e:
                    logger.error(f"Error processing Deepgram message: {e}")
                    if not self._exit.is_set():
                        break
                    
        except Exception as e:
            logger.error(f"Deepgram connection error: {e}")

    async def disconnect(self, close_code: int) -> None:
        logger.info(f"WebSocket disconnecting with code: {close_code}")
        self._exit.set()
        
        if self._deepgram_ws:
            try:
                self._deepgram_ws.close()
                logger.info("Deepgram connection closed")
            except Exception as e:
                logger.error(f"Error closing Deepgram connection: {e}")
            self._deepgram_ws = None

        if self._speaker:
            self._speaker.stop()
            logger.info("Audio system stopped")
            self._speaker = None

        if self._receiver_thread:
            self._receiver_thread.join(timeout=1.0)
            logger.info("Receiver thread stopped")
            self._receiver_thread = None

    async def receive(self, text_data: Optional[str] = None, bytes_data: Optional[bytes] = None) -> None:
        if not text_data or not self._deepgram_ws:
            logger.warning("Received invalid message or TTS service not ready")
            await self.send(json.dumps({'error': 'TTS service not ready'}))
            return

        try:
            data = json.loads(text_data)
            logger.debug(f"Received message: {data}")
            
            if data.get('type') == 'heartbeat':
                await self.send(json.dumps({'type': 'heartbeat'}))
                return
                
            if text := data.get('text'):
                # Clean and validate the text
                text = text.strip()
                if not text:
                    logger.warning("Received empty text")
                    return

                logger.info(f"Processing text: {text[:100]}...")
                
                # Send to Deepgram exactly like the working implementation
                try:
                    # Send the text
                    self._deepgram_ws.send(json.dumps({
                        "type": "Speak",
                        "text": text
                    }))
                    
                    # Send flush command
                    self._deepgram_ws.send(json.dumps({"type": "Flush"}))
                    
                    await self.send(json.dumps({
                        'status': 'processing',
                        'text': text
                    }))
                    logger.info("Text sent to Deepgram")
                except Exception as e:
                    logger.error(f"Failed to send text: {e}")
                    await self.send(json.dumps({'error': str(e)}))

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
            await self.send(json.dumps({'error': 'Invalid JSON format'}))
        except Exception as e:
            logger.error(f"Error processing text: {e}")
            await self.send(json.dumps({'error': str(e)}))