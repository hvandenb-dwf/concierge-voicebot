from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse
from twilio.twiml.voice_response import VoiceResponse
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
import cloudinary
import cloudinary.uploader
import os
import tempfile
import httpx

app = FastAPI()

eleven_client = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))

# Cloudinary config
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

voice_id = "YUdpWWny7k5yb4QCeweX"  # Ruth - native NL voice
model_id = "eleven_multilingual_v2"  # multilingual model required for Dutch

voice_settings = VoiceSettings(
    stability=0.5,
    similarity_boost=0.75,
    style=0.3,
    use_speaker_boost=True
)

@app.post("/gather")
async def gather(request: Request):
    form = await request.form()
    speech_result = form.get("SpeechResult", "").strip()
    if not speech_result:
        speech_result = "Ik heb niets gehoord. Kunt u het opnieuw proberen?"

    # Simpele logic op basis van spraakinput
    if "openingstijden" in speech_result.lower():
        reply_text = "Onze openingstijden zijn van 9:00 tot 17:00, maandag tot en met vrijdag."
    else:
        reply_text = "ACME Corp is gevestigd in Amsterdam. Kan ik ergens anders mee helpen?"

    # Audio genereren met ElevenLabs
    audio_stream = eleven_client.text_to_speech.convert(
        voice_id=voice_id,
        model_id=model_id,
        text=reply_text,
        voice_settings=voice_settings
    )

    # Opslaan naar tijdelijk bestand
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tmp.write(audio_stream.read())
        audio_path = tmp.name

    # Upload naar Cloudinary
    upload_result = cloudinary.uploader.upload(
        audio_path,
        resource_type="video",
        folder="voicebot-audio",
        upload_preset="concierge_voicebot",
    )
    secure_url = upload_result.get("secure_url")

    # TwiML response genereren
    response = VoiceResponse()
    response.play(secure_url)
    return Response(content=str(response), media_type="application/xml")

@app.post("/voice")
def voice():
    response = VoiceResponse()
    response.gather(
        input="speech",
        action="/gather",
        method="POST",
        timeout=6
    ).say("Goedemiddag! ACME Corp. Hoe kan ik u helpen?")
    return Response(content=str(response), media_type="application/xml")
