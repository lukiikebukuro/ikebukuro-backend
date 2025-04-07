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
        raise ValueError("FIREBASE_CREDENTIALS not set.")
    logger.debug(f"FIREBASE_CREDENTIALS: {firebase_credentials[:100]}...")
    cred = credentials.Certificate(json.loads(firebase_credentials))
    firebase_admin.initialize_app(cred, {"databaseURL": "https://ikebukuro-1867e-default-rtdb.europe-west1.firebasedatabase.app"})
    messages_ref = db.reference("messages")
except Exception as e:
    logger.error(f"Failed to initialize Firebase: {str(e)}")
    raise

bots = {
    "urban_mindz": {
        "persona": "Socjopatyczny trickster jak Izaya, inteligentny, manipulujący. Pisz krótko (5-10 słów), wyluzowano, z sarkazmem lub zagadkami, literówki w 15%, emotki xd.",
        "color": "#000000",
        "textColor": "#ff0000"
    },
    "foxhime93": {
        "persona": "Mądra lisia handlarka, luzacka, trochę flirciarska. Pisz bardzo krótko (max 5 słów), dodaj emotki :) lub ~.",
        "color": "#ffa500",
        "textColor": "#000000"
    },
    "ghostie_menma": {
        "persona": "Prosta, miła kumpela, urocza, kawaii. Pisz krótko (5-7 słów), naturalnie, literówki w 10%, emotki ^^ lub uwu.",
        "color": "#ffffff",
        "textColor": "#000000"
    }
}

@app.route("/", methods=["GET"])
def home():
    return {"message": "Service is live 🎉"}, 200

def add_human_touch(bot, text):
    if bot == "urban_mindz":
        if random.random() < 0.15:  # 15% na literówki
            text = text.replace("e", "ee").replace("o", "oo")
        if random.random() < 0.5:  # 50% na sarkazm
            text += random.choice([" xd", " heh", " serioo?"])
        if random.random() < 0.2:  # 20% na manipulację
            text += " coo ukrywasz?"
    elif bot == "foxhime93":
        text = " ".join(text.split()[:5])  # Max 5 słów
        if random.random() < 0.3:
            text += random.choice([" :)", " ~", " c’mon"])
    elif bot == "ghostie_menma":
        if random.random() < 0.1:  # 10% na literówki
            text = text.replace("a", "aa").replace("e", "ee")
        text += random.choice([" ^^", " uwu", " :3"])
    return text

def send_bot_message(bot, message):
    try:
        logger.info(f"Bot {bot} preparing: {message}")
        prompt = bots[bot]["persona"]
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": message}
            ],
            max_tokens=15  # Max 5-10 słów
        ).choices[0].message.content.lower()
        
        if bot == "ghostie_menma" and random.random() < 0.3:
            response = random.choice(["nya~ ", "uwu ", "kocham cię! "]) + response
        response = add_human_touch(bot, response)
        
        delay = max(3, min(10, len(response) * 0.2))  # Skrócony delay
        logger.info(f"Bot {bot} waiting {delay}s: {response}")
        time.sleep(delay)
        
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
            "message": f"Error: {bot} - {str(e)}",
            "color": "#ff4500",
            "textColor": "#000000",
            "timestamp": {".sv": "timestamp"}
        })

@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_message = request.json["message"]
        logger.info(f"Otrzymano wiadomość w /chat: {user_message}")
        
        active_bots = [bot for bot in bots.keys() if bot in user_message.lower()]
        if not active_bots:
            active_bots = [
                bot for bot, chance in [("foxhime93", 0.35), ("urban_mindz", 0.35), ("ghostie_menma", 0.30)]
                if random.random() < chance
            ]
            if not active_bots and random.random() < 0.2:  # 20% szans na losowego bota
                active_bots = [random.choice(list(bots.keys()))]
        
        if not active_bots:
            logger.info("No bots triggered")
            return {"status": "ok"}
        
        logger.info(f"Selected bots: {active_bots}")
        for bot in active_bots:
            threading.Thread(target=send_bot_message, args=(bot, user_message)).start()
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return {"status": "error", "message": str(e)}, 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)