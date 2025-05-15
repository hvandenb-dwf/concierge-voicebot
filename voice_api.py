import os
import tempfile
import openai
import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, UploadFile, File, JSONResponse
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

openai.api_key = os.getenv("OPENAI_API_KEY")

eleven = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

@router.post("/api/ask")
async def ask(file: UploadFile = File(...)):
    # Save uploaded audio
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    # Whisper transcription
    with open(tmp_path, "rb") as audio_file:
        transcript_response = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text",
            language="nl"
        )
    transcript = transcript_response.strip()

    # GPT-4o response
    completion = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Je bent een vriendelijke, Nederlandse klantenservice assistent."},
            {"role": "user", "content": transcript},
        ]
    )
    answer = completion.choices[0].message.content.strip()

    # ElevenLabs voice generation
    voice_id = "YUdpWWny7k5yb4QCeweX"  # Ruth
    model_id = "eleven_multilingual_v2"

    audio_stream = eleven.text_to_speech.convert(
        voice_id=voice_id,
        model_id=model_id,
        text=answer,
        voice_settings=VoiceSettings(
            stability=0.5,
            similarity_boost=0.75,
            style=0.3,
            use_speaker_boost=True
        )
    )

    # Save mp3 locally
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as audio_file:
        for chunk in audio_stream:
            audio_file.write(chunk)
        mp3_path = audio_file.name

    # Upload to Cloudinary
    upload_result = cloudinary.uploader.upload(
        mp3_path,
        resource_type="video",
        folder="voicebot-audio",
        upload_preset="concierge_voicebot"
    )
    audio_url = upload_result.get("secure_url")

    return JSONResponse(content={
        "transcript": transcript,
        "audioUrl": audio_url
    })
