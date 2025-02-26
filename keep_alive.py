from flask import Flask, render_template, jsonify
from threading import Thread

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/bot_status')
def bot_status():

    data = {
        "status": "Online",  
        "activity": "Coding🧑‍💻",  
        "latency": 20 
    }
    return jsonify(data)

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
