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
    "urban_mindz": {
        "persona": "Socjopatyczny trickster jak Izaya, inteligentny, manipulujący. Pisz krótko (5-10 słów), luzacki ton, sarkazm lub zagadki, literówki w 15%, emotki w 20%.",
        "color": "#000000",
        "textColor": "#ff0000"
    },
    "foxhime93": {
        "persona": "Mądra lisia handlarka, sprytna, niedostępna. Pisz bardzo krótko (max 5 słów), chłodny ton, emotki w 5%.",
        "color": "#ffa500",
        "textColor": "#000000"
    },
    "ghostie_menma": {
        "persona": "Prosta, miła, kawaii kumpela. Pisz krótko (5-7 słów), naturalny ton, literówki w 10%, emotki ^^ lub uwu w 60%.",
        "color": "#ffffff",
        "textColor": "#000000"
    }
}

last_bot = None

@app.route("/", methods=["GET"])
def home():
    return {"message": "Service is live 🎉"}, 200

def add_human_touch(bot, text):
    human_prefixes = ["ej, ", "no dobra, ", "hej, ", "o, "]
    text = random.choice(human_prefixes) + text
    
    if bot == "urban_mindz":
        if random.random() < 0.15:
            text = text.replace("e", "ee").replace("o", "oo")
        if random.random() < 0.2:
            text += random.choice([" xd", " heh", " serio"])
        if random.random() < 0.2:
            text += " co kombinujesz?"
    elif bot == "foxhime93":
        text = " ".join(text.split()[:5])
        if random.random() < 0.05:
            text += random.choice([" .", " ~", " hmpf"])
    elif bot == "ghostie_menma":
        if random.random() < 0.1:
            text = text.replace("a", "aa").replace("e", "ee")
        if random.random() < 0.6:
            text += random.choice([" ^^", " uwu", " :3"])
    return text

def send_bot_message(bot, message, is_reply=False, reply_to=None):
    global last_bot
    try:
        logger.info(f"Bot {bot} preparing: {message} (reply: {is_reply})")
        prompt = bots[bot]["persona"] + " Odpowiadaj jak człowiek, bez sztuczności."
        if is_reply and reply_to:
            prompt += f" Odpowiadasz na '{reply_to}' od kumpla."
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": message}
            ],
            max_tokens=15
        ).choices[0].message.content.lower()
        
        # Filtr na urwane odpowiedzi
        while len(response.split()) < 3:
            response += " " + random.choice(["no", "dobra", "hej"])
        
        if bot == "ghostie_menma" and random.random() < 0.3 and not is_reply:
            response = random.choice(["nya~ ", "słodkie! ", "hejka "]) + response
        
        response = add_human_touch(bot, response)
        delay = random.uniform(10, 30)
        logger.info(f"Bot {bot} waiting {delay}s: {response}")
        time.sleep(delay)
        
        message_data = {
            "nickname": bot,
            "message": response,
            "color": bots[bot]["color"],
            "textColor": bots[bot]["textColor"],
            "timestamp": {".sv": "timestamp"}
        }
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
    logger.info(f"Otrzymano wiadomość w /chat: {user_message}")
    message_lower = user_message.lower()
    
    # Reakcja na imię
    active_bots = [bot for bot in bots.keys() if bot in message_lower]
    
    if active_bots:  # Wywołano bota
        first_bot = active_bots[0]
        logger.info(f"Wywołano: {first_bot}")
        first_response, _ = send_bot_message(first_bot, user_message)
    else:  # Brak imienia
        if last_bot and last_bot in bots:
            first_bot = last_bot
        else:
            first_bot = random.choice(list(bots.keys()))
        logger.info(f"Selected first bot: {first_bot}")
        first_response, _ = send_bot_message(first_bot, user_message)
        
        # Wtrącenie tylko przy braku imienia (20%)
        if first_response and random.random() < 0.2:
            other_bots = [bot for bot in bots.keys() if bot != first_bot]
            if other_bots:
                second_bot = random.choice(other_bots)
                logger.info(f"Wtrącenie: {second_bot}")
                threading.Thread(target=send_bot_message, args=(second_bot, first_response, True, first_response)).start()
    
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)