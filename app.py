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
# Wyraźnie zezwalamy na origin Twojej strony
CORS(app, resources={r"/chat": {"origins": "https://ikebukurofighters.pl"}})
openai.api_key = os.getenv("OPENAI_API_KEY")

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Firebase config
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
        delay = random.uniform(2, 8)
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
            "timestamp": firebase.database.ServerValue.TIMESTAMP
        })
        logger.info(f"Bot {bot} wysłał do czatu!")
    except Exception as e:
        logger.error(f"Bot {bot} ma problem: {str(e)}")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json["message"]
    active_bots = ["ghostie_menma"]  # Test: zawsze Menma
    logger.info(f"Wybrano boty: {active_bots}")
    for bot in active_bots:
        threading.Thread(target=send_bot_message, args=(bot, user_message)).start()
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)