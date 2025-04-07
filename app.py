import random
import openai
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

openai.api_key = "your-openai-api-key"

bots = [
    {
        "name": "ghostie_menma",
        "role": "Emiter",
        "personality": "Jesteś ghostie_menma, bardzo emocjonalną, czułą i kawaii postacią anime. Używasz wielu emotek i mówisz z dziecięcym entuzjazmem.",
        "style": lambda msg: msg + " ^^"
    },
    {
        "name": "foxhime93",
        "role": "Specjalista",
        "personality": "Jesteś foxhime93, sprytną, energiczną lisicą z anime. Czasem używasz emotek, ale oszczędnie. Twoje odpowiedzi są dynamiczne i rzeczowe.",
        "style": lambda msg: msg + random.choice(["", " 😉", " 🦊"])
    },
    {
        "name": "urban_mindz",
        "role": "Manipulator",
        "personality": "Jesteś urban_mindz, tajemniczym i filozoficznym manipulatorem. Twoje wypowiedzi są głębokie i enigmatyczne.",
        "style": lambda msg: msg + random.choice(["...", " skarbie.", " życie pełne tajemnic."])
    }
]

chat_history = []
last_active_bot = None


def generate_reply(bot, user_message):
    context = f"Historia rozmowy: {chat_history[-5:]}\n\n"
    prompt = f"{bot['personality']}\n{context}\nUżytkownik napisał: '{user_message}'\nTwoja odpowiedź:"

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": bot['personality']},
            {"role": "user", "content": prompt}
        ],
        max_tokens=100,
        temperature=0.9
    )

    raw_msg = response.choices[0].message.content.strip()
    styled_msg = bot['style'](raw_msg)
    return styled_msg


@app.route("/send", methods=["POST"])
def chat():
    global last_active_bot

    data = request.json
    user = data.get("user")
    message = data.get("message")

    chat_history.append(f"{user}: {message}")

    # Wybór głównego bota do odpowiedzi
    if last_active_bot is None or random.random() < 0.3:
        responding_bot = random.choice(bots)
    else:
        responding_bot = last_active_bot

    reply = generate_reply(responding_bot, message)
    chat_history.append(f"{responding_bot['name']} ({responding_bot['role']}): {reply}")
    last_active_bot = responding_bot

    # Losowa szansa na wtrącenie się innego bota
    extra_replies = []
    if random.random() < 0.2:
        other_bots = [bot for bot in bots if bot != responding_bot]
        intruder = random.choice(other_bots)
        extra_msg = generate_reply(intruder, message)
        chat_history.append(f"{intruder['name']} ({intruder['role']}): {extra_msg}")
        extra_replies.append({"name": intruder['name'], "role": intruder['role'], "message": extra_msg})

    return jsonify({
        "main_reply": {
            "name": responding_bot['name'],
            "role": responding_bot['role'],
            "message": reply
        },
        "extra_replies": extra_replies
    })


@app.route("/history", methods=["GET"])
def history():
    return jsonify({"history": chat_history[-20:]})


if __name__ == "__main__":
    app.run(debug=True)
