from fastapi import FastAPI, Request
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
import os
import traceback

app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BOT_MODE = 2  # default; can later be updated via admin panel

def generate_bot_reply(user_input):
    try:
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
        print(f"GPT Reply: {reply}")  # log GPT response to Render logs
        return reply
    except Exception:
        print("OpenAI error:", traceback.format_exc())
        return "Sorry, ik kon dat niet begrijpen."

@app.post("/voice")
async def voice():
    response = VoiceResponse()
    gather = Gather(input='speech', action='/gather', method='POST', timeout=5, language='nl-NL')
    gather.say("Welkom bij de conciërgebot. Stel uw vraag na de piep.", voice='alice', language='nl-NL')
    response.append(gather)
    response.redirect('/voice')  # fallback
    return Response(content=str(response), media_type="application/xml")

@app.post("/gather")
async def gather(request: Request):
    try:
        form = await request.form()
        speech_result = form.get("SpeechResult", "").strip()

        if not speech_result:
            speech_result = "Ik heb niets gehoord. Kunt u het opnieuw proberen?"

        bot_reply = generate_bot_reply(speech_result)

        response = VoiceResponse()
        response.say(bot_reply, voice='alice', language='nl-NL')
        response.redirect('/voice')  # repeat the loop
        return Response(content=str(response), media_type="application/xml")

    except Exception as e:
        print(f"Error in /gather: {e}")
        response = VoiceResponse()
        response.say("Er is iets misgegaan. Probeert u het later nog eens.", voice='alice', language='nl-NL')
        return Response(content=str(response), media_type="application/xml")
