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
cred = credentials.Certificate(json.loads(os.getenv("FIREBASE_CREDENTIALS")))
firebase_admin.initialize_app(cred, {"databaseURL": "https://ikebukuro-1867e-default-rtdb.europe-west1.firebasedatabase.app"})
messages_ref = db.reference("messages")

bots = {
    "urban_mindz": {"persona": "manipulacyjny trickster, sarkastyczny i inteligentny. nen: manipulator.", "nen": "Manipulator"},
    "foxhime93": {"persona": "mądra, lisia, flirciarska handlarka. nen: specjalista.", "nen": "Specjalista"},
    "ghostie_menma": {"persona": "urocza, nostalgiczna, ciepła dusza. nen: emiter.", "nen": "Emiter"}
}

def send_bot_message(bot, message):
    try:
        delay = random.uniform(6, 15)  # Opóźnienie 6-15 sekund
        time.sleep(delay)
        logger.info(f"Bot {bot} próbuje odpisać na: {message}")
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": bots[bot]["persona"]},
                {"role": "user", "content": message}
            ]
        ).choices[0].message.content.lower()
        logger.info(f"Bot {bot} napisał: {response}")
        messages_ref.push({
            "nickname": bot,
            "message": response,
            "color": "#1a1a1a",
            "textColor": "#ff4500",
            "timestamp": db.ServerValue.TIMESTAMP  # Poprawny Firebase
        })
        logger.info(f"Bot {bot} wysłał do czatu!")
    except Exception as e:
        logger.error(f"Bot {bot} ma problem: {str(e)}")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json["message"]
    active_bots = []
    
    # Losowanie botów: Menma 50%, Holo 30%, Izaya 20%
    if random.random() < 0.50:
        active_bots.append("ghostie_menma")
    if random.random() < 0.30:
        active_bots.append("foxhime93")
    if random.random() < 0.20:
        active_bots.append("urban_mindz")
    
    # Zazwyczaj 1 bot, czasem 2, rzadko 3
    if len(active_bots) > 1:
        # 70% szans na tylko 1 bota, jeśli wylosowano więcej
        if random.random() < 0.70:
            active_bots = [random.choice(active_bots)]
        # 25% szans na 2 boty, jeśli więcej niż 1
        elif len(active_bots) > 2 and random.random() < 0.75:
            active_bots = random.sample(active_bots, 2)
    
    logger.info(f"Wybrano boty: {active_bots}")
    for bot in active_bots:
        threading.Thread(target=send_bot_message, args=(bot, user_message)).start()
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)