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
        "persona": "Socjopatyczny trickster jak Izaya, mega inteligentny, manipulujący. Pisz bardzo krótko (5-10 słów), wyluzowano, sarkazm lub zagadki, literówki w 15%, emotki xd.",
        "color": "#000000",
        "textColor": "#ff0000"
    },
    "foxhime93": {
        "persona": "Mądra lisia handlarka, ludzka, trochę flirciarska. Pisz bardzo krótko (max 5 słów), dodaj emotki :) lub ~.",
        "color": "#ffa500",
        "textColor": "#000000"
    },
    "ghostie_menma": {
        "persona": "Prosta, miła, kawaii kumpela. Pisz krótko (5-7 słów), naturalnie, unikaj powtórek, literówki w 10%, emotki ^^ lub uwu.",
        "color": "#ffffff",
        "textColor": "#000000"
    }
}

@app.route("/", methods=["GET"])
def home():
    return {"message": "Service is live 🎉"}, 200

def add_human_touch(bot, text):
    human_prefixes = ["ee… ", "no dobra, ", "hej, ", ""]
    text = random.choice(human_prefixes) + text
    
    if bot == "urban_mindz":
        if random.random() < 0.15:  # 15% literówki
            text = text.replace("e", "ee").replace("o", "oo").replace("i", "ii")
        if random.random() < 0.6:  # 60% sarkazm
            text += random.choice([" xd", " heh", " okk"])
        if random.random() < 0.2:  # 20% manipulacja
            text += " co ukrywasz?"
    elif bot == "foxhime93":
        text = " ".join(text.split()[:5])  # Max 5 słów
        if random.random() < 0.4:  # 40% flirt/emotki
            text += random.choice([" :)", " ~", " no powiedz"])
    elif bot == "ghostie_menma":
        if random.random() < 0.1:  # 10% literówki
            text = text.replace("a", "aa").replace("e", "ee")
        if random.random() < 0.6:  # 60% emotki
            text += random.choice([" ^^", " uwu", " :3"])
    return text

def send_bot_message(bot, message, is_reply=False, reply_to=None):
    try:
        logger.info(f"Bot {bot} preparing: {message} (reply: {is_reply})")
        prompt = bots[bot]["persona"]
        if is_reply and reply_to:
            prompt += f" Odpowiadasz na '{reply_to}' od innego bota."
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": message}
            ],
            max_tokens=15
        ).choices[0].message.content.lower()
        
        if bot == "ghostie_menma" and random.random() < 0.3 and not is_reply:
            response = random.choice(["nya~ ", "kocham cię! ", "hejka "]) + response
        
        response = add_human_touch(bot, response)
        delay = random.uniform(10, 30)  # 10-30 sekund
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
        return response
    except Exception as e:
        logger.error(f"Bot {bot} failed: {str(e)}")
        messages_ref.push({
            "nickname": "System",
            "message": f"Error: {bot} - {str(e)}",
            "color": "#ff4500",
            "textColor": "#000000",
            "timestamp": {".sv": "timestamp"}
        })
        return None

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json["message"]
    logger.info(f"Otrzymano wiadomość w /chat: {user_message}")
    message_lower = user_message.lower()
    
    # Reakcja na imię – tylko wywołane boty
    active_bots = [bot for bot in bots.keys() if bot in message_lower]
    
    # Jeśli brak imienia lub ogólne "hej", losowy bot
    if not active_bots and "hej" in message_lower:
        active_bots = [
            bot for bot, chance in [("foxhime93", 0.35), ("urban_mindz", 0.35), ("ghostie_menma", 0.30)]
            if random.random() < chance
        ]
        if not active_bots:
            active_bots = [random.choice(list(bots.keys()))]
    
    # Ograniczenie do 1 bota, chyba że wywołano więcej
    if len(active_bots) > 1 and " i " not in message_lower:  # "i" oznacza chęć rozmowy z wieloma
        active_bots = [random.choice(active_bots)]
    
    # Jeśli brak botów (np. "co słychać" bez imienia), losowy z małą szansą
    if not active_bots and random.random() < 0.2:
        active_bots = [random.choice(list(bots.keys()))]
    
    if not active_bots:
        logger.info("No bots triggered")
        return {"status": "ok"}
    
    logger.info(f"Selected bots: {active_bots}")
    
    # Pierwszy bot odpowiada
    first_bot = active_bots[0]
    first_response = send_bot_message(first_bot, user_message)
    
    # Interakcja tylko jeśli wywołano więcej botów (np. "urban i menma")
    if first_response and len(active_bots) > 1 and random.random() < 0.3:
        second_bot = random.choice([b for b in active_bots if b != first_bot])
        threading.Thread(target=send_bot_message, args=(second_bot, first_response, True, first_response)).start()
    
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)