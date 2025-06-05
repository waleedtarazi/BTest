import logging
import websockets
import json
import asyncio
import time
import pyaudio
import wave
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
)
from django.conf import settings
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
WEBSOCKET_URL = "ws://localhost:8000/ws/voice/"
DEEPGRAM_API_KEY = ""

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # Must match Deepgram's expected sample rate

# Heartbeat interval in seconds
HEARTBEAT_INTERVAL = 0.5
RECONNECT_DELAY = 5

class VoiceReceiver:
    def __init__(self):
        self.deepgram = None
        self.dg_connection = None
        self.last_audio_time = 0
        self.is_running = False
        self.audio = pyaudio.PyAudio()
        self.stream = None

    def setup_audio(self):
        """Initialize audio input stream"""
        try:
            self.stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
            logger.info("Audio input stream initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize audio: {e}")
            return False

    async def setup_deepgram(self):
        """Initialize Deepgram connection with retry logic"""
        try:
            logging.info("Setting up Deepgram connection...")
            self.deepgram = DeepgramClient(settings.DEEPGRAM_API_KEY)
            self.dg_connection = self.deepgram.listen.websocket.v("1")

            def on_message(self, result, **kwargs):
                """Handle transcription results from Deepgram"""
                sentence = result.channel.alternatives[0].transcript
                if sentence.strip():
                    logger.info(f"Transcribed: {sentence}")

            # Set up Deepgram event handler
            self.dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)

            # Configure Deepgram options
            options = LiveOptions(
                smart_format=True,
                model="nova-3",
                language="en-US",
                encoding="linear16",
                sample_rate=RATE,
                interim_results=True
            )

            logger.info("Starting Deepgram connection...")
            if not self.dg_connection.start(options):
                logger.error("Failed to start Deepgram connection")
                return False
            return True
        except Exception as e:
            logger.error(f"Deepgram setup error: {e}")
            return False

    async def send_heartbeat(self, websocket):
        """Send periodic heartbeat to keep connections alive"""
        while self.is_running:
            try:
                await websocket.send(json.dumps({"type": "heartbeat"}))
                await asyncio.sleep(HEARTBEAT_INTERVAL)
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                break

    async def process_audio(self, websocket):
        """Process and send audio data"""
        while self.is_running:
            try:
                # Read audio data from microphone
                data = self.stream.read(CHUNK, exception_on_overflow=False)
                if data:
                    # Send to both Deepgram and WebSocket
                    self.dg_connection.send(data)
                    await websocket.send(data)
                    self.last_audio_time = time.time()
            except Exception as e:
                logger.error(f"Audio processing error: {e}")
                break
            await asyncio.sleep(0.001)  # Small delay to prevent CPU overload

    async def handle_websocket(self):
        """Main WebSocket handling loop"""
        try:
            if not self.setup_audio():
                return

            if not await self.setup_deepgram():
                return

            self.is_running = True
            logger.info(f"Connecting to WebSocket at {WEBSOCKET_URL}")
            
            async with websockets.connect(WEBSOCKET_URL) as websocket:
                logger.info("Connected to voice WebSocket")
                
                # Start heartbeat and audio processing tasks
                heartbeat_task = asyncio.create_task(self.send_heartbeat(websocket))
                audio_task = asyncio.create_task(self.process_audio(websocket))
                
                # Send initial message to start voice streaming
                await websocket.send(json.dumps({
                    "type": "voice.start"
                }))

                try:
                    while self.is_running:
                        message = await websocket.recv()
                        if isinstance(message, str):
                            try:
                                data = json.loads(message)
                                if data.get('type') == 'voice.stop':
                                    logger.info("Received stop signal")
                                    break
                            except json.JSONDecodeError:
                                logger.warning(f"Received invalid JSON: {message}")
                        elif not isinstance(message, bytes):
                            logger.warning(f"Received unknown message type: {type(message)}")

                except websockets.exceptions.ConnectionClosed:
                    logger.info("WebSocket connection closed")
                finally:
                    # Cancel background tasks
                    heartbeat_task.cancel()
                    audio_task.cancel()
                    try:
                        await websocket.send(json.dumps({
                            "type": "voice.stop"
                        }))
                    except:
                        pass

        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            self.is_running = False
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if self.dg_connection:
                self.dg_connection.finish()

    def cleanup(self):
        """Clean up resources"""
        if self.audio:
            self.audio.terminate()

async def main():
    receiver = VoiceReceiver()
    try:
        while True:
            try:
                await receiver.handle_websocket()
            except Exception as e:
                logger.error(f"Connection error: {e}")
                logger.info(f"Retrying in {RECONNECT_DELAY} seconds...")
                await asyncio.sleep(RECONNECT_DELAY)
    finally:
        receiver.cleanup()

if __name__ == "__main__":
    logger.info("Starting voice receiver...")
    asyncio.run(main()) 
    asyncio.run(main()) 