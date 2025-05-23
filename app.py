import os
import tempfile
import cloudinary
import cloudinary.uploader
from fastapi import FastAPI, Request, Form, Response
from elevenlabs import ElevenLabs, VoiceSettings
from twilio.twiml.voice_response import VoiceResponse
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# ElevenLabs configuratie
voice_id = "YUdpWWny7k5yb4QCeweX"  # Ruth - native NL voice
model_id = "eleven_multilingual_v2"  # multilingual model required for Dutch

eleven_client = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))

voice_settings = VoiceSettings(
    stability=0.5,
    similarity_boost=0.75,
    style=0.3,
    use_speaker_boost=True
)

# Cloudinary configuratie
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

@app.post("/voice")
async def voice():
    response = VoiceResponse()
    response.gather(
        input="speech",
        action="/gather",
        method="POST"
    ).say("Welkom bij uw digitale assistent. Wat kan ik voor u doen?")
    return Response(content=str(response), media_type="application/xml")

@app.post("/gather")
async def gather(request: Request):
    form = await request.form()
    speech_result = form.get("SpeechResult", "").strip()
    if not speech_result:
        speech_result = "Ik heb niets gehoord. Kunt u het opnieuw proberen?"

    if "openingstijden" in speech_result.lower():
        text = "Onze openingstijden zijn van negen tot vijf, maandag tot en met vrijdag."
    else:
        text = "Ik heb u niet goed verstaan. Kunt u dat herhalen?"

    # Genereer audiostream
    audio_stream = eleven_client.text_to_speech.convert(
        voice_id=voice_id,
        model_id=model_id,
        text=text,
        voice_settings=voice_settings
    )

    # Schrijf stream chunks naar tijdelijk bestand
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        for chunk in audio_stream:
            tmp.write(chunk)
        tmp_path = tmp.name

    # Upload naar Cloudinary
    upload_result = cloudinary.uploader.upload(
        tmp_path,
        resource_type="video",
        folder="voicebot-audio",
        upload_preset="concierge_voicebot"
    )

    secure_url = upload_result.get("secure_url")

    response = VoiceResponse()
    response.play(secure_url)
    return Response(content=str(response), media_type="application/xml")
