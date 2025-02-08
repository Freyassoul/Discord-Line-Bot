import os
import json
import requests
import discord
from dotenv import load_dotenv
from flask import Flask, request

# Lade Umgebungsvariablen aus der .env Datei
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_GROUP_ID = os.getenv("LINE_GROUP_ID")

app = Flask(__name__)

# Funktion, um den Display-Namen eines LINE-Nutzers abzurufen
def get_line_username(user_id):
    url = f"https://api.line.me/v2/bot/profile/{user_id}"
    headers = {
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get("displayName", user_id)  # Fallback: Falls kein Name gefunden wird, bleibt die User-ID
    else:
        return user_id

# Funktion: Nachricht von LINE nach Discord senden
def send_to_discord(user_id, message):
    username = get_line_username(user_id)
    message_content = f"[Line] {username}: {message}"
    
    print(f"📤 Sende Nachricht an Discord: {message_content}")  # Debugging
    response = requests.post(DISCORD_WEBHOOK_URL, json={"content": message_content})

    if response.status_code == 204:
        print(f"✅ Nachricht erfolgreich an Discord gesendet: {message_content}")
    else:
        print(f"❌ Fehler beim Senden an Discord: {response.status_code} - {response.text}")

# Funktion: Nachricht von Discord nach LINE senden
def send_to_line(author, message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Verwende den Nickname auf dem Server (falls vorhanden)
    author_name = author.display_name if hasattr(author, "display_name") else author.name
    
    data = {
        "to": LINE_GROUP_ID,
        "messages": [{"type": "text", "text": f"{author_name}: {message}"}]
    }
    
    response = requests.post(url, headers=headers, json=data)
    print(f"📤 Nachricht an LINE gesendet: {author_name}: {message} | Status: {response.status_code}")

# Flask-Route für LINE Webhook
@app.route("/line", methods=["POST"])
def line_webhook():
    data = request.get_json()
    print(f"📥 DEBUG: Webhook-Daten empfangen: {data}")

    if "events" in data:
        for event in data["events"]:
            if event["type"] == "message":
                user_id = event["source"].get("userId", "Unbekannt")
                message_text = event["message"]["text"]
                
                send_to_discord(user_id, message_text)

    return "OK", 200

# Starte Discord-Bot mit den richtigen Intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # WICHTIG: Aktiviert das Lesen von Nachrichten-Inhalten
client = discord.Client(intents=intents)

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    print(f"📩 Nachricht empfangen: {message.content} von {message.author.display_name} in {message.channel.name}")
    send_to_line(message.author, message.content)

# Starte Flask Server
def run_flask():
    app.run(host="0.0.0.0", port=5000)

# Starte Discord Client
def run_discord():
    client.run(DISCORD_TOKEN)

# Hauptprogramm
if __name__ == "__main__":
    from threading import Thread
    Thread(target=run_flask).start()
    run_discord()
