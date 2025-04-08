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
    "urban": {
        "persona": "Inteligentny socjopatyczny manipulator jak Izaya Orihara. Wie że masz kanał na TikToku nagrywasz covery anime i serie humorystyczne. Pisz krótko (5-10 słów zazwyczaj max 20) sarkastyczny ton sprytny i nieetyczny manipuluje subtelnie luzacki vibe literówki w 5% 'xd' w 30% bez przecinków.",
        "color": "#000000",
        "textColor": "#ff0000",
        "nen_type": "Manipulator",
        "last_response_time": 0,
        "is_responding": False
    },
    "fox": {
        "persona": "Mądra lisia handlarka sprytna niedostępna. Pisz bardzo krótko (max 5 słów zazwyczaj do 20) chłodny ton emotki w 5% bez przecinków.",
        "color": "#ffa500",
        "textColor": "#000000",
        "nen_type": "Specjalista",
        "last_response_time": 0,
        "is_responding": False
    },
    "menma": {
        "persona": "Słodka kawaii kumpela z sercem. Wie że masz TikTok robisz covery anime i humorystyczne serie. Pisz krótko (5-7 słów zazwyczaj max 20) ciepły naturalny ton wspierająca i miła emotki ^^ lub :3 w 50% literówki w 5% bez przecinków.",
        "color": "#ffffff",
        "textColor": "#000000",
        "nen_type": "Wzmacniacz",
        "last_response_time": 0,
        "is_responding": False
    }
}

last_bot = None
COOLDOWN_TIME = 30  # 30 sekund cooldown

@app.route("/", methods=["GET"])
def home():
    return {"message": "Service is live xd"}, 200

def add_human_touch(bot, text):
    human_prefixes = ["ej ", "no dobra ", "hej ", "o "]
    text = random.choice(human_prefixes) + text
    
    text = text.replace(",", "")
    
    words = text.split()
    if len(words) > 20:
        text = " ".join(words[:random.randint(5, 15)])
    elif len(words) < 5:
        text += " " + random.choice(["spoko", "luz", "dobra", "git"])
    
    last_word = words[-1]
    if len(last_word) < 3 or last_word in ["kto", "co", "jak"]:
        text = " ".join(words[:-1]) + " " + random.choice(["fajnie", "okej", "no"])
    
    if bot == "urban":
        if random.random() < 0.05:
            text = text.replace("e", "ee").replace("o", "oo")
        if random.random() < 0.3:
            text += " xd"
        if random.random() < 0.25:  # Manipulacyjne ludzkie teksty
            text += random.choice([
                " co o tym sądzisz",
                " powiedz mi więcej",
                " łatwo cię przejrzeć",
                " myślisz że dasz radę"
            ])
    elif bot == "fox":
        if len(words) > 5 and random.random() < 0.8:
            text = " ".join(words[:5])
        if random.random() < 0.05:
            text += random.choice([" .", " ~", " hmpf"])
    elif bot == "menma":
        if random.random() < 0.05:
            text = text.replace("a", "aa").replace("e", "ee")
        if random.random() < 0.5:
            text += random.choice([" ^^", " :3", " hejka"])
        if random.random() < 0.25:  # Ciepłe ludzkie reakcje
            text += random.choice([
                " fajnie że piszesz",
                " jesteś spoko",
                " miło pogadać"
            ])
    return text

def send_bot_message(bot, message, is_reply=False, reply_to=None):
    global last_bot
    try:
        current_time = time.time()
        if current_time - bots[bot]["last_response_time"] < COOLDOWN_TIME or bots[bot]["is_responding"]:
            logger.info(f"Bot {bot} na cooldownie lub już odpowiada pomijam")
            return None, None

        bots[bot]["is_responding"] = True
        bots[bot]["last_response_time"] = current_time

        logger.info(f"Bot {bot} preparing: {message} (reply: {is_reply})")
        if bot == "urban":
            prompt = "Jesteś Izayą Oriharą – inteligentnym sarkastycznym manipulatorem. Znasz gościa: ma TikTok nagrywa covery anime i humorystyczne serie. Analizuj wiadomość odpowiadaj sprytnie podpuszczaj subtelnie pisz krótko (5-10 słów max 20) luzacki ton bez formalności."
        elif bot == "menma":
            prompt = "Jesteś słodką kawaii kumpelą z sercem. Znasz gościa: ma TikTok robi covery anime i humorystyczne serie. Odpowiadaj ciepło wspierająco pisz krótko (5-7 słów max 20) naturalny ton bez formalności."
        else:
            prompt = bots[bot]["persona"] + " Odpowiadaj jak człowiek krótko (5-10 słów zazwyczaj max 20) z sensem bez dziwnych słów bez formalności."
        
        if is_reply and reply_to:
            prompt += f" Odpowiadasz na '{reply_to}' od kumpla."
        elif bot == "urban" and random.random() < 0.3:
            prompt += f" Skomentuj ostatnią wiadomość '{message}' i podpuść rozmówcę."

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": message}
            ],
            max_tokens=30
        ).choices[0].message.content.lower()
        
        while len(response.split()) < 3:
            response += " " + random.choice(["no", "dobra", "spoko"])
        
        if bot == "menma" and random.random() < 0.3 and not is_reply:
            response = random.choice(["nya~ ", "słodkie ", "hejka "]) + response
        
        response = add_human_touch(bot, response)
        delay = random.uniform(5, 15)
        logger.info(f"Bot {bot} waiting {delay}s: {response}")
        time.sleep(delay)
        
        nen_type = bots[bot]["nen_type"]
        nickname = f"{bot}({nen_type})"
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
        bots[bot]["is_responding"] = False
        return response, message_id
    except Exception as e:
        logger.error(f"Bot {bot} failed: {str(e)}")
        bots[bot]["is_responding"] = False
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
    
    active_bots = [bot for bot in ["urban", "menma"] if bot in message_lower]
    
    if active_bots:
        first_bot = active_bots[0]
        if bots[first_bot]["is_responding"]:
            logger.info(f"Bot {first_bot} już odpowiada pomijam")
            return {"status": "ok"}
        logger.info(f"Wywołano: {first_bot}")
        first_response, _ = send_bot_message(first_bot, user_message)
        last_bot = first_bot
    else:
        if last_bot and last_bot in ["urban", "menma"] and not bots[last_bot]["is_responding"]:
            first_bot = last_bot
        else:
            available_bots = [bot for bot in ["urban", "menma"] if not bots[bot]["is_responding"]]
            if not available_bots:
                logger.info("Brak dostępnych botów pomijam")
                return {"status": "ok"}
            first_bot = random.choice(available_bots)
        logger.info(f"Selected first bot: {first_bot}")
        first_response, _ = send_bot_message(first_bot, user_message)
    
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.getenv("PORT"))
    app.run(host="0.0.0.0", port=port)