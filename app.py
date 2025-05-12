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
            model="gpt-4",
            messages=[
                {"role": "system", "content": (
                    "You are a helpful virtual receptionist for ACME Corp. "
                    "Our office hours are 9 AM to 5 PM, Monday to Friday. "
                    "We're located in Amsterdam. Answer all questions based on this info."
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
        return "Sorry, I couldn't understand that."

@app.post("/voice")
async def voice():
    response = VoiceResponse()
    gather = Gather(input='speech', action='/gather', method='POST', timeout=5)
    gather.say("Welcome to your concierge bot. Please ask your question after the beep.", voice='Polly.Joanna', language='en-US')
    response.append(gather)
    response.redirect('/voice')  # fallback
    return Response(content=str(response), media_type="application/xml")

@app.post("/gather")
async def gather(request: Request):
    try:
        form = await request.form()
        speech_result = form.get("SpeechResult", "").strip()

        if not speech_result:
            speech_result = "I didn't catch that. Please try again."

        bot_reply = generate_bot_reply(speech_result)

        response = VoiceResponse()
        response.say(bot_reply, voice='Polly.Joanna', language='en-US')
        response.redirect('/voice')  # repeat the loop
        return Response(content=str(response), media_type="application/xml")

    except Exception as e:
        print(f"Error in /gather: {e}")
        response = VoiceResponse()
        response.say("Sorry, something went wrong. Please try again later.", voice='Polly.Joanna', language='en-US')
        return Response(content=str(response), media_type="application/xml")
