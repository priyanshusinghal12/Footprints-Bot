from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bot import FootprintsBot

app = FastAPI()
bot = FootprintsBot()

# Allow frontend requests from localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "https://footprints-bot.vercel.app"
],

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.get("/")
async def root():
    return {"message": "Footprints backend is running!"}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    reply = bot.handle_message(request.message)
    return {"response": reply}
