import openai
import os
from dotenv import load_dotenv

load_dotenv()

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

try:
    response = client.models.list()
    print("✅ API key works. Response models:")
    for model in response.data:
        print(model.id)
except openai.AuthenticationError as e:
    print("❌ Authentication error:", e)
except openai.RateLimitError as e:
    print("🚫 Rate limit error (likely org mismatch or inactive key):", e)
except Exception as e:
    print("Unhandled error:", e)
