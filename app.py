from flask import Flask, request
import openai
import firebase_admin
from firebase_admin import db, credentials
import random
import time
import threading

app = Flask(__name__)
openai.api_key = "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"

# Firebase config
cred = credentials.Certificate("C:/Users/lpisk/OneDrive/Pulpit/backend/firebase-key.json")
firebase_admin.initialize_app(cred, {"databaseURL": "https://ikebukuro-1867e-default-rtdb.europe-west1.firebasedatabase.app"})
messages_ref = db.reference("messages")

bots = {
    "urban_mindz": {"persona": "manipulacyjny trickster, sarkastyczny i inteligentny. nen: manipulator.", "nen": "Manipulator"},
    "foxhime93": {"persona": "mądra, lisia, flirciarska handlarka. nen: specjalista.", "nen": "Specjalista"},
    "ghostie_menma": {"persona": "urocza, nostalgiczna, ciepła dusza. nen: emiter.", "nen": "Emiter"}
}

def send_bot_message(bot, message):
    delay = random.uniform(2, 8)
    time.sleep(delay)
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": bots[bot]["persona"]},
            {"role": "user", "content": message}
        ]
    ).choices[0].message.content.lower()  # Małe litery
    messages_ref.push({
        "nickname": bot,
        "message": response,
        "color": "#1a1a1a",
        "textColor": "#ff4500",
        "timestamp": firebase.database.ServerValue.TIMESTAMP
    })

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json["message"]
    active_bots = []
    if random.random() < 0.50:  # 50% szans na Menmę
        active_bots.append("ghostie_menma")
    if random.random() < 0.30:  # 30% szans na Holo
        active_bots.append("foxhime93")
    if random.random() < 0.20:  # 20% szans na Izayę
        active_bots.append("urban_mindz")
    
    for bot in active_bots:
        threading.Thread(target=send_bot_message, args=(bot, user_message)).start()
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(port=5000)