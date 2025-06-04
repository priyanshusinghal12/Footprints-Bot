from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bot import FootprintsBot

app = FastAPI()
bot = FootprintsBot()

# Define request schema
class ChatRequest(BaseModel):
    message: str

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with actual domain in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define /chat POST endpoint
@app.post("/chat")
async def chat(req: ChatRequest):
    user_input = req.message
    response = bot.handle_message(user_input)
    return {"response": response}
