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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")
    if not firebase_credentials:
        raise ValueError("FIREBASE_CREDENTIALS not set.")
    cred = credentials.Certificate(json.loads(firebase_credentials))
    firebase_admin.initialize_app(cred, {"databaseURL": "https://ikebukuro-1867e-default-rtdb.europe-west1.firebasedatabase.app"})
    messages_ref = db.reference("messages")
except Exception as e:
    logger.error(f"Failed to initialize Firebase: {str(e)}")
    raise

bots = {
    "urban": {  # Manipulator
        "persona": "Inteligentny, sarkastyczny manipulator jak Izaya Orihara. Pisz krótko (5-10 słów), luzacki ton, zero głupot, literówki w 5%, emotki w 20%.",
        "color": "#000000",
        "textColor": "#ff0000",
        "nen_type": "Manipulator"
    },
    "fox": {  # Specjalista
        "persona": "Mądra lisia handlarka, sprytna, niedostępna. Pisz bardzo krótko (max 5 słów), chłodny ton, emotki w 5%.",
        "color": "#ffa500",
        "textColor": "#000000",
        "nen_type": "Specjalista"
    },
    "menma": {  # Wzmacniacz
        "persona": "Prosta, miła, kawaii kumpela. Pisz krótko (5-7 słów), naturalny ton, kawaii, bez głupot, literówki w 5%, emotki ^^ lub uwu w 60%.",
        "color": "#ffffff",
        "textColor": "#000000",
        "nen_type": "Wzmacniacz"
    }
}

last_bot = None

@app.route("/", methods=["GET"])
def home():
    return {"message": "Service is live 🎉"}, 200

def add_human_touch(bot, text):
    human_prefixes = ["ej, ", "no dobra, ", "hej, ", "o, "]
    text = random.choice(human_prefixes) + text
    
    # Ograniczamy do 5-10 słów
    words = text.split()
    if len(words) > 10:
        text = " ".join(words[:10])
    elif len(words) < 5:
        text += " " + random.choice(["spoko", "luz", "dobra", "no"])
    
    # Blokada nonsensu
    last_word = words[-1]
    if len(last_word) < 3 or last_word in ["kto", "co", "jak", "colts"]:
        text = " ".join(words[:-1]) + " " + random.choice(["fajnie", "git", "super"])
    
    if bot == "urban":
        if random.random() < 0.05:
            text = text.replace("e", "ee").replace("o", "oo")
        if random.random() < 0.2:
            text += random.choice([" xd", " heh", " serio"])
        if random.random() < 0.2:
            text += " co kombinujesz?"
    elif bot == "fox":
        text = " ".join(text.split()[:5])
        if random.random() < 0.05:
            text += random.choice([" .", " ~", " hmpf"])
    elif bot == "menma":
        if random.random() < 0.05:
            text = text.replace("a", "aa").replace("e", "ee")
        if random.random() < 0.6:
            text += random.choice([" ^^", " uwu", " :3"])
    return text

def send_bot_message(bot, message, is_reply=False, reply_to=None):
    global last_bot
    try:
        logger.info(f"Bot {bot} preparing: {message} (reply: {is_reply})")
        prompt = bots[bot]["persona"] + " Odpowiadaj jak człowiek, krótko (5-10 słów), z sensem, bez dziwnych słów."
        if is_reply and reply_to:
            prompt += f" Odpowiadasz na '{reply_to}' od kumpla."
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": message}
            ],
            max_tokens=20
        ).choices[0].message.content.lower()
        
        while len(response.split()) < 3:
            response += " " + random.choice(["no", "dobra", "spoko"])
        
        if bot == "menma" and random.random() < 0.3 and not is_reply:
            response = random.choice(["nya~ ", "słodkie! ", "hejka "]) + response
        
        response = add_human_touch(bot, response)
        delay = random.uniform(10, 30)
        logger.info(f"Bot {bot} waiting {delay}s: {response}")
        time.sleep(delay)
        
        # Formatowanie nazwy: bot(NenType) z wielką literą
        nen_type = bots[bot]["nen_type"]  # np. "Manipulator"
        nickname = f"{bot}({nen_type})"   # np. "urban(Manipulator)"
        
        message_data = {
            "nickname": nickname,
            "message": response,
            "color": bots[bot]["color"],
            "textColor": bots[bot]["textColor"],
            "timestamp": {".sv": "timestamp"}
        }
        logger.info(f"Sending to Firebase: {message_data}")
        ref = messages_ref.push(message_data)
        message_id = ref.key
        logger.info(f"Bot {bot} sent: {response} (ID: {message_id})")
        last_bot = bot
        return response, message_id
    except Exception as e:
        logger.error(f"Bot {bot} failed: {str(e)}")
        messages_ref.push({
            "nickname": "System",
            "message": f"Error: {bot} - {str(e)}",
            "color": "#ff4500",
            "textColor": "#000000",
            "timestamp": {".sv": "timestamp"}
        })
        return None, None

@app.route("/chat", methods=["POST"])
def chat():
    global last_bot
    user_message = request.json["message"]
    logger.info(f"Oを受けた wiadomość w /chat: {user_message}")
    message_lower = user_message.lower()
    
    # Reakcja na imię - pełne nicki
    active_bots = [bot for bot in bots.keys() if bot in message_lower]
    
    if active_bots:  # Wywołano bota
        first_bot = active_bots[0]
        logger.info(f"Wywołano: {first_bot}")
        first_response, _ = send_bot_message(first_bot, user_message)
        last_bot = first_bot  # Nadpisuje last_bot
    else:  # Brak imienia
        if last_bot and last_bot in bots:
            first_bot = last_bot
        else:
            first_bot = random.choice(list(bots.keys()))
        logger.info(f"Selected first bot: {first_bot}")
        first_response, _ = send_bot_message(first_bot, user_message)
        # Wtrącenia wyłączone - jeden bot na raz
    
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)