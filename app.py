from flask import Flask, request, jsonify, render_template
import requests, urllib.parse, json, os, re
from datetime import datetime

app = Flask(__name__)

# --- memory.json yükle ---
MEMORY_PATH = "memory.json"
if os.path.exists(MEMORY_PATH):
    with open(MEMORY_PATH, "r", encoding="utf-8") as f:
        memory = json.load(f)
else:
    memory = {}

# Ana sayfa
@app.route("/")
def home():
    return render_template("index.html")

#  Bugün Ne Oldu (Wikipedia'dan gerçek verileri alır)
@app.route("/today", methods=["GET"])
def today():
    now = datetime.now()
    month = now.month
    day = now.day
    headers = {"User-Agent": "MyHistoryBot/1.0"}

    try:
        ev_url = f"https://tr.wikipedia.org/api/rest_v1/feed/onthisday/events/{month}/{day}"
        ev_res = requests.get(ev_url, headers=headers, timeout=8)
        events, births = [], []

        if ev_res.status_code == 200:
            for ev in ev_res.json().get("events", [])[:8]:
                events.append({"year": ev.get("year"), "text": ev.get("text")})

        b_url = f"https://tr.wikipedia.org/api/rest_v1/feed/onthisday/births/{month}/{day}"
        b_res = requests.get(b_url, headers=headers, timeout=8)
        if b_res.status_code == 200:
            for b in b_res.json().get("births", [])[:6]:
                births.append({"year": b.get("year"), "text": b.get("text")})

        return jsonify({"events": events, "births": births})
    except Exception as e:
        return jsonify({"events": [], "births": [], "error": str(e)}), 200


#  Chat endpointi
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()
    user_message_lower = user_message.lower()

    normalized_memory = {k.lower(): v for k, v in memory.items()}

    aliases = {
        "habip": "habib",
        "habib": "habib",
        "feyza": "feyza",
        "alper": "alper",
        "sibel": "sibel",
        "kıraç": "kıraç",
        "furkan": "furkan",
        "beyza": "beyza",
        "elif": "elif",
        "yusuf": "yusuf",
        "adem": "adem dayım",
        "atatürk": "atatürk"
    }

    #  Basit matematik işlemleri (örnek: 2+2, 3*5, (5+2)/3)
    if re.match(r"^[\d\s\+\-\*\/\.\(\)]+$", user_message_lower):
        try:
            result = eval(user_message_lower)
            return jsonify({"reply": f"🧮 Sonuç: {result}"})
        except:
            pass  # diğer işlemlere geç

    #  "kimdir" sorgusu
    if "kimdir" in user_message_lower or re.search(r"\bkim\b", user_message_lower):
        name = user_message_lower.replace("kimdir", "").strip()
        name = aliases.get(name, name)
        if name in normalized_memory:
            info = normalized_memory[name]["info"]
            return jsonify({"reply": f"{normalized_memory[name]['name']} hakkında: {info}"})
        else:
            return jsonify({"reply": f"'{name}' hakkında kayıtlı bilgi bulunamadı 😕"})

    #  Doğum tarihi sorgusu
    date_pattern = r"(\d{1,2}\s*(ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık)\s*\d{0,4})"
    date_match = re.search(date_pattern, user_message_lower, re.IGNORECASE)
    if date_match:
        searched_date = date_match.group(1).replace(".", " ").replace("/", " ").strip().lower()
        for k, v in normalized_memory.items():
            info_lower = v["info"].lower()
            if all(part in info_lower for part in searched_date.split()):
                return jsonify({"reply": f"{v['name']} doğdu ({v['info']})"})
        return jsonify({"reply": "Bu tarihte doğan bir kişi bulunamadı 😕"})

    #  Wikipedia fallback
    query = urllib.parse.quote(user_message)
    search_url = f"https://tr.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&utf8=&format=json&origin=*"

    try:
        res = requests.get(search_url, timeout=5, headers={"User-Agent": "Chatbot/1.0"})
        if res.status_code != 200 or not res.text.strip():
            return jsonify({"reply": "Wikipedia’dan geçerli bir yanıt alınamadı 😕"})

        data = res.json()
        if "query" not in data or not data["query"]["search"]:
            return jsonify({"reply": "Üzgünüm, bu konuda bilgi bulamadım 😕"})

        title = data["query"]["search"][0]["title"]
        detail_url = f"https://tr.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
        detail_res = requests.get(detail_url, timeout=5, headers={"User-Agent": "Chatbot/1.0"})

        if detail_res.status_code != 200:
            return jsonify({"reply": f"{title} hakkında özet bulunamadı 😕"})

        summary = detail_res.json().get("extract", "Özet bulunamadı 😕")
        return jsonify({"reply": f"📘 {title} hakkında:\n{summary}"})

    except Exception as e:
        return jsonify({"reply": f"Bir hata oluştu: {str(e)}"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
