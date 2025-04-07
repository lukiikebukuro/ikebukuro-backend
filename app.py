from flask_cors import CORS
from flask import Flask, request
import openai
import firebase_admin
from firebase_admin import db, credentials
import random
import time
import os
import json
import logging

app = Flask(__name__)
CORS(app, resources={r"/chat": {"origins": "*"}})  # Testowo otwarte
openai.api_key = os.getenv("OPENAI_API_KEY")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

try:
    firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")
    if not firebase_credentials:
        raise ValueError("FIREBASE_CREDENTIALS not set.")
    cred = credentials.Certificate(json.loads(firebase_credentials))
    firebase_admin.initialize_app(cred, {"databaseURL": "https://ikebukuro-1867e-default-rtdb.europe-west1.firebasedatabase.app"})
    messages_ref = db.reference("messages")
    logger.info("Firebase initialized!")
except Exception as e:
    logger.error(f"Firebase init failed: {str(e)}")
    raise

bots = {
    "urban_mindz": {
        "persona": "Inteligentny, sarkastyczny trickster jak Izaya. Pisz bardzo krótko, max 5-10 słów. Manipuluj, rzucaj zagadki. Literówki w 15%.",
        "color": "#000000",
        "textColor": "#ff0000"
    },
    "foxhime93": {
        "persona": "Mądra, flirciarska handlarka. Pisz bardzo krótko, max 5 słów. Dodawaj emotki :) lub ~.",
        "color": "#ffa500",
        "textColor": "#000000"
    },
    "ghostie_menma": {
        "persona": "Urocza, kawaii dziewczyna. Pisz krótko, max 5-7 słów. Dodawaj emotki jak ^^, >_<, uwu. Literówki w 10%.",
        "color": "#ffffff",
        "textColor": "#000000"
    }
}

@app.route("/", methods=["GET"])
def home():
    return {"message": "Service is live 🎉"}, 200

def add_human_touch(bot, text):
    if bot == "urban_mindz":
        if random.random() < 0.15: text = text.replace("e", "ee").replace("o", "oo")
        if random.random() < 0.5: text += random.choice([" heh", " xd", " serio?"])
        if random.random() < 0.2: text += " co ukrywasz?"
    elif bot == "ghostie_menma":
        if random.random() < 0.1: text = text.replace("a", "aa").replace("e", "ee")
        text += random.choice([" ^^", " >_<", " uwu", " :3"])
    elif bot == "foxhime93":
        if random.random() < 0.3: text += random.choice([" :)", " ~", " no powiedz"])
    return text

def send_bot_message(bot, message):
    try:
        logger.info(f"Bot {bot} preparing: {message}")
        prompt = bots[bot]["persona"] + " Odpowiadaj bardzo krótko, max 5-10 słów."
        if bot == "ghostie_menma":
            prompt += " Używaj uroczych zwrotów jak 'uwu', 'nya', 'kocham cię'."
        
        logger.info(f"Calling OpenAI for {bot}")
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": message}
            ],
            max_tokens=15
        ).choices[0].message.content.lower()
        logger.info(f"OpenAI returned: {response}")
        
        if bot == "ghostie_menma" and random.random() < 0.3:
            response = random.choice(["kocham cię! ", "nya~ ", "uwu "]) + response
        response = add_human_touch(bot, response)
        
        delay = max(3, min(10, len(response) * 0.2))
        logger.info(f"Bot {bot} waiting {delay}s: {response}")
        time.sleep(delay)
        
        logger.info(f"Pushing to Firebase: {response}")
        messages_ref.push({
            "nickname": bot,
            "message": response,
            "color": bots[bot]["color"],
            "textColor": bots[bot]["textColor"],
            "timestamp": {".sv": "timestamp"}
        })
        logger.info(f"Bot {bot} sent: {response}")
    except Exception as e:
        logger.error(f"Bot {bot} failed: {str(e)}")
        messages_ref.push({
            "nickname": "System",
            "message": f"Error: {bot} failed - {str(e)}",
            "color": "#ff4500",
            "textColor": "#000000",
            "timestamp": {".sv": "timestamp"}
        })

@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_message = request.json.get("message", "").strip()
        if not user_message:
            logger.warning("Empty message received.")
            return {"status": "error", "message": "Empty message."}, 400
        
        logger.info(f"Received: {user_message}")
        active_bots = [bot for bot in bots.keys() if bot in user_message.lower()]
        if not active_bots and random.random() < 0.2:
            active_bots = [random.choice(list(bots.keys()))]
            logger.info(f"Random bot: {active_bots}")
        
        if not active_bots:
            logger.info("No bots selected.")
            return {"status": "ok"}
        
        for bot in active_bots:
            logger.info(f"Calling {bot} directly")
            send_bot_message(bot, user_message)  # Bez wątków
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return {"status": "error", "message": str(e)}, 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# Test lokalny
if __name__ == "__main__":
    send_bot_message("urban_mindz", "hej")  # Testowe wywołanie