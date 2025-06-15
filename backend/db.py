# backend/db.py
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI not found in environment variables.")

client = MongoClient(MONGO_URI)
db = client["footprints_chat"]
collection = db["conversations"]

# Optional: Create index if you plan to support querying history
# collection.create_index([("session_id", 1), ("timestamp", 1)])

def save_message(sender: str, message: str, session_id: str):
    doc = {
        "session_id": session_id,
        "sender": sender,
        "message": message,
        "timestamp": datetime.utcnow()
    }
    try:
        collection.insert_one(doc)
    except Exception as e:
        print(f"[DB ERROR] Failed to save message: {e}")
