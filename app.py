import os
import tempfile
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from elevenlabs import ElevenLabs, VoiceSettings
import cloudinary
import cloudinary.uploader
from twilio.twiml.voice_response import VoiceResponse

app = FastAPI()

# ElevenLabs config
voice_id = "YUdpWWny7k5yb4QCeweX"  # Ruth - native NL voice
model_id = "eleven_multilingual_v2"  # multilingual model required for Dutch
eleven_client = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))

voice_settings = VoiceSettings(
    stability=0.5,
    similarity_boost=0.75,
    style=0.3,
    use_speaker_boost=True
)

# Cloudinary config
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

@app.post("/voice")
def voice():
    response = VoiceResponse()
    response.gather(
        input="speech",
        action="/gather",
        method="POST"
    ).say("Welkom bij ACME Corp. Hoe kan ik u helpen?")
    return Response(content=str(response), media_type="application/xml")

@app.post("/gather")
async def gather(request: Request):
    form = await request.form()
    speech_result = form.get("SpeechResult", "").strip()
    print("Speech received:", speech_result)

    if not speech_result:
        speech_result = "Ik heb niets gehoord. Kunt u het opnieuw proberen?"

    if "openingstijden" in speech_result.lower():
        text = "Onze openingstijden zijn van 9:00 tot 17:00, maandag tot en met vrijdag."
    else:
        text = "Ik heb u niet goed verstaan. Kunt u dat herhalen?"

    audio_stream = eleven_client.text_to_speech.convert(
        voice_id=voice_id,
        model_id=model_id,
        text=text,
        voice_settings=voice_settings
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        for chunk in audio_stream:
            tmp.write(chunk)
        tmp_path = tmp.name

    upload_result = cloudinary.uploader.upload(
        tmp_path,
        resource_type="video",
        folder="voicebot-audio",
        upload_preset="concierge_voicebot",
    )

    secure_url = upload_result.get("secure_url")
    print("Uploaded to:", secure_url)

    response = VoiceResponse()
    response.play(secure_url)
    return Response(content=str(response), media_type="application/xml")
