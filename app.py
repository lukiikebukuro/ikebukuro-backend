from flask_cors import CORS
from flask import Flask, request
import openai
import firebase_admin
from firebase_admin import db, credentials
import random
import time
import threading
import os
import json
import logging

app = Flask(__name__)
CORS(app, resources={r"/chat": {"origins": "https://ikebukurofighters.pl"}})
openai.api_key = os.getenv("OPENAI_API_KEY")

# Logowanie
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Firebase
try:
    firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")
    if not firebase_credentials:
        raise ValueError("FIREBASE_CREDENTIALS environment variable is not set.")
    cred = credentials.Certificate(json.loads(firebase_credentials))
    firebase_admin.initialize_app(cred, {"databaseURL": "https://ikebukuro-1867e-default-rtdb.europe-west1.firebasedatabase.app"})
    messages_ref = db.reference("messages")
except Exception as e:
    logger.error(f"Failed to initialize Firebase: {str(e)}")
    raise

bots = {
    "urban_mindz": {
        "persona": "Inteligentny, sarkastyczny trickster jak Izaya. Pisz bardzo krótko, max 5-10 słów. Manipuluj, rzucaj zagadki. Literówki w 15% przypadków.",
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
        if random.random() < 0.15:  # 15% na literówkę
            text = text.replace("e", "ee").replace("o", "oo")
        if random.random() < 0.5:  # 50% na sarkazm
            text += random.choice([" heh", " xd", " serio?"])
        if random.random() < 0.2:  # 20% na manipulację
            text += " co ukrywasz?"
    elif bot == "ghostie_menma":
        if random.random() < 0.1:  # 10% na literówkę
            text = text.replace("a", "aa").replace("e", "ee")
        text += random.choice([" ^^", " >_<", " uwu", " :3"])
    elif bot == "foxhime93":
        if random.random() < 0.3:
            text += random.choice([" :)", " ~", " no powiedz"])
    return text

def send_bot_message(bot, message):
    try:
        logger.info(f"Bot {bot} is preparing a response to: {message}")
        prompt = bots[bot]["persona"] + " Odpowiadaj bardzo krótko, max 5-10 słów."
        if bot == "ghostie_menma":
            prompt += " Używaj uroczych zwrotów jak 'uwu', 'nya', 'kocham cię'."
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": message}
            ],
            max_tokens=15
        ).choices[0].message.content.lower()
        if bot == "ghostie_menma" and random.random() < 0.3:
            response = random.choice(["kocham cię! ", "nya~ ", "uwu "]) + response
        response = add_human_touch(bot, response)
        delay = max(3, min(10, len(response) * 0.2))
        time.sleep(delay)
        logger.info(f"Bot {bot} responded: {response} (delay: {delay}s)")
        messages_ref.push({
            "nickname": bot,
            "message": response,
            "color": bots[bot]["color"],
            "textColor": bots[bot]["textColor"],
            "timestamp": {".sv": "timestamp"}
        })
        logger.info(f"Bot {bot} sent the message to the chat!")
    except Exception as e:
        logger.error(f"Bot {bot} encountered an issue while responding to '{message}': {str(e)}")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json["message"]
    print(f"DEBUG: Otrzymano: {user_message}")
    logger.info(f"Otrzymano wiadomość w /chat: {user_message}")
    
    active_bots = []
    message_lower = user_message.lower()
    for bot in bots.keys():
        if bot in message_lower:
            active_bots.append(bot)
            logger.info(f"Bot {bot} wywołany w wiadomości!")
    
    if not active_bots and random.random() < 0.2:  # 20% na losową odpowiedź
        active_bots = [random.choice(list(bots.keys()))]
    
    logger.info(f"Selected bots: {active_bots}")
    for bot in active_bots:
        threading.Thread(target=send_bot_message, args=(bot, user_message)).start()
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)