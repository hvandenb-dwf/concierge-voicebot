from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
from elevenlabs import ElevenLabs
from elevenlabs.client import VoiceSettings
from uuid import uuid4
import os
import traceback
import time
import requests
import tempfile

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
eleven_client = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))

BOT_MODE = 2

CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_UPLOAD_URL = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/auto/upload"
CLOUDINARY_UPLOAD_PRESET = "voicebot-audio"

voice_id = "YUdpWWny7k5yb4QCeweX"  # Ruth - native NL voice
model_id = "eleven_multilingual_v2"  # multilingual model required for Dutch

voice_settings = VoiceSettings(
    stability=0.5,
    similarity_boost=0.75,
    style=0.3,
    use_speaker_boost=True
)

def generate_audio_from_text(text: str) -> str:
    try:
        audio_stream = eleven_client.text_to_speech.convert(
            voice_id=voice_id,
            model_id=model_id,
            text=text,
            voice_settings=voice_settings
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            for chunk in audio_stream:
                tmp_file.write(chunk)
            tmp_file_path = tmp_file.name

        files = {"file": open(tmp_file_path, "rb")}
        data = {
            "upload_preset": CLOUDINARY_UPLOAD_PRESET,
            "api_key": CLOUDINARY_API_KEY,
            "timestamp": int(time.time())
        }
        response = requests.post(CLOUDINARY_UPLOAD_URL, files=files, data=data, auth=(CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET))
        os.unlink(tmp_file_path)

        if response.status_code == 200:
            uploaded_url = response.json()["secure_url"]
            return uploaded_url
        else:
            print(f"Cloudinary error: {response.status_code}, {response.text}")
            return None

    except Exception as e:
        print(f"ElevenLabs or Cloudinary error: {e}")
        return None

@app.post("/voice")
async def voice():
    response = VoiceResponse()
    gather = Gather(input='speech', action='/gather', method='POST', timeout=5, language='nl-NL')
    gather.say("Welkom bij de conciërgebot. Stel uw vraag na de piep.", voice='alice', language='nl-NL')
    response.append(gather)
    response.redirect('/voice')
    return Response(content=str(response), media_type="application/xml")

@app.post("/gather")
async def gather(request: Request):
    form = await request.form()
    speech_result = form.get("SpeechResult", "").strip()

    if not speech_result:
        speech_result = "Ik heb niets gehoord. Kunt u het opnieuw proberen?"

    if "openingstijden" in speech_result.lower():
        bot_reply = "Wij zijn geopend van maandag tot en met vrijdag van 9 tot 17 uur."
    else:
        bot_reply = "Ik zal uw vraag doorgeven aan het team."

    audio_url = generate_audio_from_text(bot_reply)

    response = VoiceResponse()
    if audio_url:
        response.play(audio_url)
    else:
        response.say(bot_reply, voice='alice', language='nl-NL')

    response.redirect('/voice')
    return Response(content=str(response), media_type="application/xml")
