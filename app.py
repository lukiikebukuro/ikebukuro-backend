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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Firebase
try:
    firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")
    if not firebase_credentials:
        raise ValueError("FIREBASE_CREDENTIALS environment variable is not set.")
    logger.debug(f"FIREBASE_CREDENTIALS: {firebase_credentials[:100]}...")
    cred = credentials.Certificate(json.loads(firebase_credentials))
    firebase_admin.initialize_app(cred, {"databaseURL": "https://ikebukuro-1867e-default-rtdb.europe-west1.firebasedatabase.app"})
    messages_ref = db.reference("messages")
except Exception as e:
    logger.error(f"Failed to initialize Firebase: {str(e)}")
    raise

bots = {
    "urban_mindz": {
        "persona": "socjopatyczny trickster, mega inteligentny i manipulujący, pisz wyluzowano z błędami typu 'hejj' czy 'okk', rzucaj sarkazm albo zagadki, dodaj emotki xd",
        "color": "#000000",  # Czarny (ramka)
        "textColor": "#ff0000"  # Czerwony (tekst)
    },
    "foxhime93": {
        "persona": "mądra lisia handlarka, trochę poważna ale z ludzkim luzem, pisz krótkie zdania, czasem flirciarskie, uzywaj emotek :)",
        "color": "#ffa500",  # Pomarańczowy (ramka)
        "textColor": "#000000"  # Czarny (tekst)
    },
    "ghostie_menma": {
        "persona": "prosta, miła, fajna kumpela, pisz krótko i naturalnie, czasem z literówkami, dodaj emotki ^^",
        "color": "#ffffff",  # Biały (ramka)
        "textColor": "#000000"  # Czarny (tekst)
    }
}

@app.route("/", methods=["GET"])
def home():
    return {"message": "Service is live 🎉"}, 200

def add_human_touch(bot, text):
    if random.random() < 0.2:
        text = text.replace("e", "ee").replace("o", "oo").replace("a", "aa")
    if bot == "urban_mindz":
        if random.random() < 0.6:
            text += random.choice([" xd", " ;]", " heh"])
        if random.random() < 0.2:
            text += " coś ukrywasz, coo?"
    elif bot == "foxhime93":
        text = " ".join(text.split()[:5])
        if random.random() < 0.3:
            text += random.choice([" :)", " ~", " c’mon"])
    elif bot == "ghostie_menma":
        if random.random() < 0.5:
            text += random.choice([" ^^", " hehe", " :D"])
    return text

def send_bot_message(bot, message):
    try:
        logger.info(f"Bot {bot} is preparing a response to: {message}")
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": bots[bot]["persona"]},
                {"role": "user", "content": message}
            ]
        ).choices[0].message.content.lower()
        response = add_human_touch(bot, response)
        delay = max(6, min(30, len(response) * 0.2))
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
    logger.info(f"Otrzymano wiadomość w /chat: {user_message}")  # Dodane
    active_bots = [
        bot for bot, chance in [("foxhime93", 0.35), ("urban_mindz", 0.35), ("ghostie_menma", 0.30)]
        if random.random() < chance
    ]
    if not active_bots:
        active_bots = [random.choice(list(bots.keys()))]
    if len(active_bots) > 1:
        if random.random() < 0.70:
            active_bots = [random.choice(active_bots)]
        elif len(active_bots) > 2 and random.random() < 0.75:
            active_bots = random.sample(active_bots, 2)
    logger.info(f"Selected bots: {active_bots}")
    for bot in active_bots:
        threading.Thread(target=send_bot_message, args=(bot, user_message)).start()
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)