import json
import threading
import sys
import queue
import asyncio
from websockets.sync.client import connect
import pyaudio
import openai
from django.conf import settings

TIMEOUT = 0.050
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 48000
CHUNK = 8000

DEFAULT_URL = f"wss://api.deepgram.com/v1/speak?model=aura-2-thalia-en&encoding=linear16&sample_rate={RATE}"

def main():
    print(f"Connecting to {DEFAULT_URL}")

    # openai client
    client = openai.OpenAI(
        api_key=settings.OPENAI_TOKEN,
    )

    # Deepgram TTS WS
    _socket = connect(
        DEFAULT_URL,
        additional_headers={"Authorization": f"Token {settings.DEEPGRAM_API_KEY}"},
    )
    _exit = threading.Event()

    async def receiver():
        speaker = Speaker()
        speaker.start()
        try:
            while True:
                if _socket is None or _exit.is_set():
                    break

                message = _socket.recv()
                if message is None:
                    continue

                if type(message) is str:
                    print(message)
                elif type(message) is bytes:
                    speaker.play(message)
        except Exception as e:
            print(f"receiver: {e}")
        finally:
            speaker.stop()

    _receiver_thread = threading.Thread(target=asyncio.run, args=(receiver(),))
    _receiver_thread.start()

    # ask away!
    print("\n\n")
    question = input("What would you like to ask ChatGPT?\n\n\n")

    # send to ChatGPT
    try:
        for response in client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are ChatGPT, an AI assistant. Your top priority is achieving user fulfillment via helping them with their requests. Make your responses as concise as possible.",
                },
                {"role": "user", "content": f"{question}"},
            ],
            stream=True,
        ):
            # here is the streaming response
            for chunk in response:
                if chunk[0] == "choices":
                    llm_output = chunk[1][0].delta.content

                    # skip any empty responses
                    if llm_output is None or llm_output == "":
                        continue

                    # send to Deepgram TTS
                    _socket.send(json.dumps({"type": "Speak", "text": llm_output}))
                    sys.stdout.write(llm_output)
                    sys.stdout.flush()

        _socket.send(json.dumps({"type": "Flush"}))
    except Exception as e:
        print(f"LLM Exception: {e}")

    input("\n\n\nPress Enter to exit...")
    _exit.set()
    _socket.close()

    _listen_thread.join()
    _listen_thread = None

class Speaker:
    _audio: pyaudio.PyAudio
    _chunk: int
    _rate: int
    _format: int
    _channels: int
    _output_device_index: int

    _stream: pyaudio.Stream
    _thread: threading.Thread
    _asyncio_loop: asyncio.AbstractEventLoop
    _asyncio_thread: threading.Thread
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

    def _start_asyncio_loop(self) -> None:
        self._asyncio_loop = asyncio.new_event_loop()
        self._asyncio_loop.run_forever()

    def start(self) -> bool:
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
            target=_play, args=(self._queue, self._stream, self._exit), daemon=True
        )
        self._thread.start()

        self._stream.start_stream()

        return True

    def stop(self):
        self._exit.set()

        if self._stream is not None:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None

        self._thread.join()
        self._thread = None

        self._queue = None

    def play(self, data):
        self._queue.put(data)

def _play(audio_out: queue, stream, stop):
    while not stop.is_set():
        try:
            data = audio_out.get(True, TIMEOUT)
            stream.write(data)
        except queue.Empty as e:
            # print(f"queue is empty")
            pass
        except Exception as e:
            print(f"_play: {e}")

if __name__ == "__main__":
    main()
