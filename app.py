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

BOT_MODE = 2  # default; can later be updated via admin panel
UPLOADTHING_TOKEN = os.getenv("UPLOADTHING_TOKEN")
UPLOADTHING_ENDPOINT = "https://uploadthing.com/api/uploadFiles-signed"

def generate_bot_reply(user_input):
    try:
        start = time.time()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": (
                    "Je bent een behulpzame virtuele receptioniste voor ACME Corp. "
                    "Onze openingstijden zijn van 9:00 tot 17:00, maandag tot en met vrijdag. "
                    "We zijn gevestigd in Amsterdam. Beantwoord vragen op basis van deze informatie."
                )},
                {"role": "user", "content": user_input}
            ],
            max_tokens=100
        )
        reply = response.choices[0].message.content.strip()
        print(f"GPT Reply: {reply} (Generated in {time.time() - start:.2f}s)")
        return reply
    except Exception:
        print("OpenAI error:", traceback.format_exc())
        return "Sorry, ik kon dat niet begrijpen."

def generate_audio_from_text(text: str) -> str:
    try:
        voice_id = "EXAVITQu4vr4xnSDxMaL"
        print(f"UPLOADTHING_TOKEN = {UPLOADTHING_TOKEN}")  # DEBUG: check token

        audio_stream = eleven_client.text_to_speech.convert(
            voice_id=voice_id,
            model_id="eleven_monolingual_v1",
            text=text,
            voice_settings=VoiceSettings(stability=0.5, similarity_boost=0.75)
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            for chunk in audio_stream:
                tmp_file.write(chunk)
            tmp_file_path = tmp_file.name

        file_data = open(tmp_file_path, "rb")
        upload_files = {
            "files": (f"{uuid4()}.mp3", file_data, "audio/mpeg")
        }
        headers = {"Authorization": f"Bearer {UPLOADTHING_TOKEN}"}

        response = requests.post(UPLOADTHING_ENDPOINT, files=upload_files, headers=headers)
        file_data.close()
        os.unlink(tmp_file_path)

        if response.status_code == 200:
            uploaded_url = response.json()[0]["fileUrl"]
            print(f"Uploaded to: {uploaded_url}")
            return uploaded_url
        else:
            print(f"UploadThing error: {response.status_code}, {response.text}")
            return None

    except Exception as e:
        print(f"ElevenLabs or Upload error: {e}")
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
    try:
        form = await request.form()
        speech_result = form.get("SpeechResult", "").strip()

        if not speech_result:
            speech_result = "Ik heb niets gehoord. Kunt u het opnieuw proberen?"

        bot_reply = generate_bot_reply(speech_result)
        audio_url = generate_audio_from_text(bot_reply)

        response = VoiceResponse()
        if audio_url:
            response.play(audio_url)
        else:
            response.say(bot_reply, voice='alice', language='nl-NL')

        response.redirect('/voice')
        return Response(content=str(response), media_type="application/xml")

    except Exception as e:
        print(f"Error in /gather: {e}")
        response = VoiceResponse()
        response.say("Er is iets misgegaan. Probeert u het later nog eens.", voice='alice', language='nl-NL')
        return Response(content=str(response), media_type="application/xml")
