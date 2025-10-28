# backend/db.py
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

# Make MongoDB optional - if not configured, just skip logging
if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI)
        db = client["footprints_chat"]
        collection = db["conversations"]
        print("[DB] MongoDB connected successfully")
    except Exception as e:
        print(f"[DB WARNING] Failed to connect to MongoDB: {e}")
        collection = None
else:
    print("[DB] MONGO_URI not set - conversation logging disabled")
    collection = None

# Optional: Create index if you plan to support querying history
# collection.create_index([("session_id", 1), ("timestamp", 1)])

def save_message(sender: str, message: str, session_id: str):
    if collection is None:
        return  # Skip if database is not configured
    
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
