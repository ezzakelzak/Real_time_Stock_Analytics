import os
import time
import json
import requests
from kafka import KafkaProducer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- API CONFIG ---
API_KEY = os.getenv("FINNHUB_API_KEY")
BASE_URL = os.getenv("FINNHUB_BASE_URL")
SYMBOLS = os.getenv("SYMBOLS").split(",")

# --- KAFKA CONFIG ---
KAFKA_SERVER = os.getenv("KAFKA_BOOTSTRAP_SERVER")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")

# --- INITIALIZE PRODUCER ---
producer = KafkaProducer(
    bootstrap_servers=[KAFKA_SERVER],
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

# --- FETCH QUOTE FUNCTION ---
def fetch_quote(symbol):
    url = f"{BASE_URL}?symbol={symbol}&token={API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        data["symbol"] = symbol
        data["fetched_at"] = int(time.time())
        return data
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

# --- MAIN LOOP ---
while True:
    for symbol in SYMBOLS:
        quote = fetch_quote(symbol)
        if quote:
            print(f"Producing: {quote}")
            producer.send(KAFKA_TOPIC, value=quote)
    time.sleep(6)
