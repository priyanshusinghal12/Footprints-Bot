# backend/db.py
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["footprints_chat"]
collection = db["conversations"]

def save_message(sender: str, message: str, session_id: str):
    doc = {
        "session_id": session_id,
        "sender": sender,
        "message": message,
        "timestamp": datetime.utcnow()
    }
    collection.insert_one(doc)
