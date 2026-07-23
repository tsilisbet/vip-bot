import requests
import re
import time
import threading
import json 
import os
from flask import Flask 

# --- ΡΥΘΜΙΣΕΙΣ ---
TELEGRAM_TOKEN = "8759490328:AAEs5kEP5sAGbppX-3pqw3c2LgFNq2Bd6zQ"
CHAT_IDS = ["5221368333", "-5184281314"] 
CHECK_INTERVAL = 20  

TIPSTERS = {
    "Karaoulanis": "https://paiktarades.com/wp-json/api/v1/feed?limit=5&tipster=118205"
}

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Active!"

def run_web():
    app.run(host="0.0.0.0", port=8080)

# --- ΑΠΟΣΤΟΛΗ ΜΗΝΥΜΑΤΟΣ ---
def send_telegram_message(message):
    for chat_id in CHAT_IDS:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        try:
            # Στέλνει το μήνυμα αμέσως και στα δύο chats
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"Error for {chat_id}: {e}")

def load_last_ids():
    if os.path.exists("last_bet_ids.json"):
        try:
            with open("last_bet_ids.json", "r") as file:
                return json.load(file)
        except:
            return {}
    return {}

def save_last_ids(data):
    with open("last_bet_ids.json", "w") as file:
        json.dump(data, file)

def check_for_new_bets():
    headers = {"User-Agent": "Mozilla/5.0"}
    last_ids = load_last_ids()
    ids_changed = False

    for tipster_name, target_url in TIPSTERS.items():
        try:
            response = requests.get(target_url, headers=headers, timeout=15)
            json_resp = response.json()
            
            # Διόρθωση για τη νέα μορφή JSON (dictionary με "items" vs σκέτο list)
            if isinstance(json_resp, dict) and "items" in json_resp:
                data = json_resp["items"]
            elif isinstance(json_resp, list):
                data = json_resp
            else:
                data = []
        except:
            continue

        current_last_id = last_ids.get(tipster_name, 0)
        
        # Αν είναι η πρώτη φορά που τρέχει (δεν έχει ID), 
        # παίρνουμε το ID του 5ου στοιχείου για να στείλει μόνο τα 5 τελευταία.
        if current_last_id == 0 and len(data) > 0:
            # Αν υπάρχουν λιγότερα από 5, στέλνει όσα υπάρχουν
            idx = min(5, len(data))
            current_last_id = data[idx-1].get("id", 0) - 1

        temp_highest_id = current_last_id

        for item in reversed(data):
            bet_id = item.get("id", 0)
            html_content = item.get("html", "")
            
            if bet_id > current_last_id and "<pre>Array" in html_content:
                # 1. Extract system_type to detect Bet Builders
                sys_match = re.search(r'\[system_type\] => (.*)', html_content, re.IGNORECASE)
                system_type = sys_match.group(1).strip().lower() if sys_match else "single"

                matches = re.findall(r'\[match_label\] => (.*)', html_content)
                picks = re.findall(r'\[pick_label\] => (.*)', html_content)
                all_odds = re.findall(r'\[odds\] => (.*)', html_content)
                
                bookie_match = re.search(r'\[(?:book|bookmaker_label|bookmaker|bookie)\] => (.*)', html_content, re.IGNORECASE)
                bookie = bookie_match.group(1).strip() if bookie_match else "N/A"
                
                units_match = re.search(r'\[(?:units|stake)\] => (.*)', html_content, re.IGNORECASE)
                units = units_match.group(1).strip() if units_match else "N/A"
                
                if matches and picks:
                    message = f"🚨 <b>NEW BET FROM {tipster_name.upper()}</b> 🚨\n\n"
                    
                    # --- BET BUILDER FORMATTING ---
                    if system_type == "betbuilder":
                        m_name = matches[0].strip()
                        message += f"🛠 <b>BET BUILDER: {m_name}</b>\n"
                        for pick in picks:
                            message += f" 🔹 {pick.strip()}\n"
                        message += "\n"
                        
                    # --- STANDARD FORMATTING ---
                    else:
                        for i in range(len(matches)):
                            m_name = matches[i].strip()
                            p_name = picks[i].strip()
                            m_odd = all_odds[i+1].strip() if len(all_odds) > i+1 else "N/A"
                            message += f"- <b>{m_name}</b>\n🎯 {p_name} @ <b>{m_odd}</b>\n\n"
                    
                    total_odds = all_odds[0].strip() if all_odds else "N/A"
                    message += f"📊 <b>Total Odds:</b> {total_odds}\n"
                    message += f"🏦 <b>Bookmaker:</b> {bookie}\n"
                    message += f"💵 <b>Units/Stake:</b> {units}\n"
                    
                    # Αποστολή και στα δύο chat πριν συνεχίσει
                    send_telegram_message(message)
                    
                    temp_highest_id = max(temp_highest_id, bet_id)
                    ids_changed = True

        last_ids[tipster_name] = temp_highest_id

    if ids_changed:
        save_last_ids(last_ids)

def bot_loop():
    # Μήνυμα επιβεβαίωσης ότι το bot ακούει και τα δύο chats
    send_telegram_message("✅ Bot Active: Monitoring Dogass & Karaoulanis (Last 5)")
    while True:
        check_for_new_bets()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    threading.Thread(target=bot_loop, daemon=True).start()
    run_web()
