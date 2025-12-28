from flask import Flask
from threading import Thread
from datetime import datetime
import config

app = Flask(__name__)

@app.route('/')
def home():
    now = datetime.now()
    return f"I'm alive. Ping from {config.PORT}. Time: {now}"

def run():
    # Run on 0.0.0.0 to be accessible
    app.run(host='0.0.0.0', port=config.PORT)

def keep_alive():
    t = Thread(target=run)
    t.start()
