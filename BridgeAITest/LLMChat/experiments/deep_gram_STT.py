import requests
from django.conf import settings
DEEPGRAM_URL = "https://api.deepgram.com/v1/speak?model=aura-2-thalia-en"


payload = {
    "text": "Hello, how can I help you today? My name is Emily and I'm very glad to meet you. What do you think of this new text-to-speech API?"
}

headers = {
    "Authorization": f"Token {settings.DEEPGRAM_API_KEY}",
    "Content-Type": "application/json"
}

audio_file_path = "output.mp3"  # Path to save the audio file

with open(audio_file_path, 'wb') as file_stream:
    response = requests.post(DEEPGRAM_URL, headers=headers, json=payload, stream=True)
    for chunk in response.iter_content(chunk_size=1024):
        if chunk:
            file_stream.write(chunk) # Write each chunk of audio data to the file

print("Audio download complete")
