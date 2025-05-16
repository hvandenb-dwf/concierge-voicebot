from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import cloudinary
import cloudinary.uploader
from elevenlabs import ElevenLabs, VoiceSettings
import openai

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory=os.path.join(os.getcwd(), "static")), name="static")

# Root route fallback for testing index.html
def load_index():
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>index.html not found</h1>"

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content=load_index())

# ENV keys (Render will provide these)
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Init clients
openai.api_key = OPENAI_API_KEY
eleven_client = ElevenLabs(api_key=ELEVEN_API_KEY)
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

class SpeechData(BaseModel):
    text: str

@app.post("/gather")
async def gather(request: Request):
    form = await request.form()
    speech_result = form.get("SpeechResult", "").strip()
    if not speech_result:
        speech_result = "Ik heb niets gehoord. Kunt u het opnieuw proberen?"

    # GPT-4 reply
    chat_response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Je bent een vriendelijke Nederlandse klantenservice bot."},
            {"role": "user", "content": speech_result},
        ]
    )
    reply = chat_response.choices[0].message.content.strip()

    # ElevenLabs voice
    audio_stream = eleven_client.text_to_speech.convert(
        voice_id="YUdpWWny7k5yb4QCeweX",  # Ruth
        model_id="eleven_multilingual_v2",
        text=reply,
        voice_settings=VoiceSettings(
            stability=0.5,
            similarity_boost=0.75,
            style=0.3,
            use_speaker_boost=True
        )
    )

    # Save audio and upload to Cloudinary
    audio_path = "response.mp3"
    with open(audio_path, "wb") as tmp:
        tmp.write(audio_stream.read())

    upload_result = cloudinary.uploader.upload(
        audio_path,
        resource_type="video",
        folder="voicebot-audio",
        upload_preset="concierge_voicebot",
    )
    secure_url = upload_result.get("secure_url")

    twiml_response = f"""
        <Response>
            <Play>{secure_url}</Play>
            <Gather input="speech" action="/gather" method="POST" timeout="6" />
        </Response>
    """

    return HTMLResponse(content=twiml_response, media_type="application/xml")
