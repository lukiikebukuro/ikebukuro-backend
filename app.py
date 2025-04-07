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
    logger.debug(f"FIREBASE_CREDENTIALS: {firebase_credentials[:100]}...")
    cred = credentials.Certificate(json.loads(firebase_credentials))
    firebase_admin.initialize_app(cred, {"databaseURL": "https://ikebukuro-1867e-default-rtdb.europe-west1.firebasedatabase.app"})
    messages_ref = db.reference("messages")
except Exception as e:
    logger.error(f"Failed to initialize Firebase: {str(e)}")
    raise

bots = {
    "urban_mindz": {
        "persona": "Socjopatyczny trickster jak Izaya, inteligentny, manipulujący. Pisz krótko (5-10 słów), wyluzowano, sarkazm lub zagadki, literówki w 15%, emotki xd.",
        "color": "#000000",
        "textColor": "#ff0000"
    },
    "foxhime93": {
        "persona": "Mądra lisia handlarka, ludzka, flirciarska. Pisz bardzo krótko (max 5 słów), dodaj emotki :) lub ~.",
        "color": "#ffa500",
        "textColor": "#000000"
    },
    "ghostie_menma": {
        "persona": "Prosta, miła, kawaii kumpela. Pisz krótko (5-7 słów), naturalnie, unikaj powtórek, literówki w 10%, jedna emotka ^^ lub uwu.",
        "color": "#ffffff",
        "textColor": "#000000"
    }
}

last_bot = None

@app.route("/", methods=["GET"])
def home():
    return {"message": "Service is live 🎉"}, 200

def add_human_touch(bot, text):
    human_prefixes = ["ee… ", "no dobra, ", "hej, ", ""]
    text = random.choice(human_prefixes) + text.strip()  # Ensure no trailing "this" or similar artifacts
    
    if bot == "urban_mindz":
        if random.random() < 0.15:
            text = text.replace("e", "ee").replace("o", "oo").replace("i", "ii")
        if random.random() < 0.6:
            text += random.choice([" xd", " heh", " okk"])
        if random.random() < 0.2:
            text += " co ukrywasz?"
    elif bot == "foxhime93":
        text = " ".join(text.split()[:5])  # Limit to 5 words
        if random.random() < 0.2:  # Reduce emote usage
            text += random.choice([".", " no powiedz."])
    elif bot == "ghostie_menma":
        if random.random() < 0.1:
            text = text.replace("a", "aa").replace("e", "ee")
        if random.random() < 0.6:
            text += random.choice([" ^^", " uwu", " :3"])  # Max one emoticon
    return text

def send_bot_message(bot, message, is_reply=False, reply_to=None):
    global last_bot
    try:
        logger.info(f"Bot {bot} preparing: {message} (reply: {is_reply})")
        prompt = bots[bot]["persona"]
        if is_reply and reply_to:
            prompt += f" Odpowiadasz na '{reply_to}' od innego bota."
        
        response = openai.ChatCompletion.create(  # Corrected API call
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": message}
            ],
            max_tokens=15
        ).choices[0].message.content.strip()  # Ensure no trailing artifacts
        
        if bot == "ghostie_menma" and random.random() < 0.3 and not is_reply:
            response = random.choice(["nya~ ", "kocham cię! ", "hejka "]) + response
        
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
        message_id = ref.key  # Message ID
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
    
    # React to bot names
    active_bots = [bot for bot in bots.keys() if bot in message_lower]
    
    if active_bots:  # Specific bot called
        first_bot = active_bots[0]
        first_response, _ = send_bot_message(first_bot, user_message)
    else:  # No specific bot called – continue or pick random
        if last_bot and last_bot in bots:
            first_bot = last_bot
        else:
            first_bot = random.choice(list(bots.keys()))
        logger.info(f"Selected first bot: {first_bot}")
        first_response, _ = send_bot_message(first_bot, user_message)
        
        # Interjection only if no specific bot called (20%)
        if first_response and random.random() < 0.2:
            other_bots = [bot for bot in bots.keys() if bot != first_bot]
            if other_bots:
                second_bot = random.choice(other_bots)
                logger.info(f"Interjection: {second_bot}")
                threading.Thread(target=send_bot_message, args=(second_bot, first_response, True, first_response)).start()
    
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)