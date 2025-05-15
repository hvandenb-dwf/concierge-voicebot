import os
import tempfile
import cloudinary
import cloudinary.uploader
from fastapi import FastAPI, Request, Form
from fastapi.responses import JSONResponse
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
import openai

app = FastAPI()

# Load environment variables
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

# Configure Cloudinary
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

# Setup clients
openai.api_key = OPENAI_API_KEY
eleven_client = ElevenLabs(api_key=ELEVEN_API_KEY)

# Configure ElevenLabs voice
voice_id = "YUdpWWny7k5yb4QCeweX"  # Ruth - native NL voice
model_id = "eleven_multilingual_v2"
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

    # OpenAI GPT-4 call
    messages = [
        {"role": "system", "content": "Je bent een virtuele receptioniste voor ACME Corp. We zijn gevestigd in Amsterdam."},
        {"role": "user", "content": speech_result},
    ]
    chat_response = openai.chat.completions.create(
        model="gpt-4",
        messages=messages,
    )
    gpt_reply = chat_response.choices[0].message.content.strip()

    # Convert text to speech
    audio_stream = eleven_client.text_to_speech.convert(
        voice_id=voice_id,
        model_id=model_id,
        text=gpt_reply,
        voice_settings=voice_settings,
        output_format="mp3"
    )

    # Write to temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tmp.write(audio_stream.read())
        tmp_path = tmp.name

    # Upload to Cloudinary
    upload_result = cloudinary.uploader.upload(
        tmp_path,
        resource_type="video",
        folder="voicebot-audio",
        upload_preset="concierge_voicebot"
    )

    secure_url = upload_result.get("secure_url")
    return JSONResponse(content={"audio_url": secure_url})
