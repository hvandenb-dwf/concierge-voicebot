from fastapi import FastAPI, Request
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Gather

app = FastAPI()

BOT_MODE = 2  # default; can later be updated via admin panel

def generate_bot_reply(user_input):
    if BOT_MODE == 1:
        return "Thank you. We've recorded your message. Someone will call you back."
    elif BOT_MODE == 2:
        if "hours" in user_input.lower():
            return "We are open from 9 AM to 5 PM, Monday to Friday."
        return "I'm not sure. I will forward this to our team."
    elif BOT_MODE == 3:
        if "location" in user_input.lower():
            return "Our office is in Amsterdam, Herengracht 101."
        return "I can follow up by email if you want more details."
    return "Sorry, something went wrong."

@app.post("/voice")
async def voice():
    response = VoiceResponse()
    gather = Gather(input='speech', action='/gather', method='POST', timeout=5)
    gather.say("Welcome to your concierge bot. Please ask your question after the beep.")
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
        response.say(bot_reply)
        response.redirect('/voice')  # repeat the loop
        return Response(content=str(response), media_type="application/xml")

    except Exception as e:
        print(f"Error in /gather: {e}")
        response = VoiceResponse()
        response.say("Sorry, something went wrong. Please try again later.")
        return Response(content=str(response), media_type="application/xml")
