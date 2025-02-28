from flask import Flask, render_template, jsonify
from threading import Thread

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/bot_status')
def bot_status():
    features = {
        "Auto Mod": "🟢",  # เปิดใช้งานสมบูรณ์
        "Welcome System": "🟡",  # กำลังพัฒนา
        "Logging": "🟢",  # ปิดใช้งาน
        "Music Player": "🔴",  # เปิดใช้งานสมบูรณ์
        "AI Chatbot": "🟢",  # กำลังพัฒนา
        "หารูป": "🟢",  # เปิดใช้งานสมบูรณ์
        "ค้นหาข้อมูล": "🟢",  # กำลังพัฒนา
        "จดจำข้อมูล": "🟢",  # เปิดใช้งานสมบูรณ์
        "ออนไลน์ 24 ชม": "🟢",  # เปิดใช้งานสมบูรณ์
        "ป้องกันภาพ NSFW": "🟢"  # เปิดใช้งานสมบูรณ์
    }
    
    completed = sum(1 for status in features.values() if status == "🟢")
    total = len(features)
    percentage = round((completed / total) * 100, 1)

    data = {
        "status": "Online",  # สถานะบอท
        "activity": "Coding🧑‍💻",  # กิจกรรมปัจจุบันของบอท
        "latency": 20,  # Latency ของบอท (ms)
        "feature_completion": percentage,  # เปอร์เซ็นต์ความสมบูรณ์ของฟีเจอร์
        "other_features": features  # ฟีเจอร์ของบอทและสถานะ
    }
    return jsonify(data)

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
