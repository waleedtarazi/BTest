from deepgram import DeepgramClient, DeepgramClientOptions, LiveTranscriptionEvents, LiveOptions
import httpx
import threading
import websockets
from django.conf import settings

# The API key you created in step 1
DEEPGRAM_API_KEY = ''

# URL for the real-time streaming audio you would like to transcribe
URL = 'http://stream.live.vc.bbcmedia.co.uk/bbc_world_service'

def main():
    try:
        try:
            deepgram = DeepgramClient(settings.DEEPGRAM_API_KEY)
            dg_connection = deepgram.listen.live.v('1')
        except websockets.exceptions.InvalidStatus as e:
            print(f"ERROR: {e.headers.get('dg-error')}")
            print(f"Request ID: {e.headers.get('dg-request-id')}")
            return
        # Listen for any transcripts received from Deepgram and write them to the console
        def on_message(self, result, **kwargs):
            print(f" this is a result: {result}")
            sentence = result.channel.alternatives[0].transcript
            if len(sentence) == 0:
                return
            print(f'transcript: {sentence}')

        dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)

        # Create a websocket connection to Deepgram
        options = LiveOptions(
            smart_format=True, model="nova-2", language="en-GB"
        )
        dg_connection.start(options)

        lock_exit = threading.Lock()
        exit = False

        # Listen for the connection to open and send streaming audio from the URL to Deepgram
        def myThread():
            with httpx.stream('GET', URL) as r:
                for data in r.iter_bytes():
                    lock_exit.acquire()
                    if exit:
                        break
                    lock_exit.release()

                    dg_connection.send(data)

        myHttp = threading.Thread(target=myThread)
        myHttp.start()

        input('Press Enter to stop transcription...\n')
        lock_exit.acquire()
        exit = True
        lock_exit.release()

        myHttp.join()

        # Indicate that we've finished by sending the close stream message
        dg_connection.finish()
        print('Finished')

    except Exception as e:
        print(f'Could not open socket: {e}')
        return

if __name__ == '__main__':
    main()