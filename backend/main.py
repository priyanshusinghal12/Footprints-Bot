from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bot import FootprintsBot
from db import save_message

app = FastAPI()
bot = FootprintsBot()

# CORS setup for local dev (Vite), Vercel (frontend), and Render (backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: str  # For tracking user sessions

@app.get("/")
async def root():
    return {"message": "Footprints backend is running!"}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        user_input = request.message
        session_id = request.session_id

        save_message("user", user_input, session_id)
        reply = bot.handle_message(user_input)
        save_message("bot", reply, session_id)

        return {"response": reply}
    except Exception as e:
        return {"response": "Something went wrong. Please try again later."}

