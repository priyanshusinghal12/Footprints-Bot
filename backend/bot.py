import os
import json
import re
import random
from dotenv import load_dotenv
from openai import OpenAI

class FootprintsBot:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not api_key.startswith("sk-"):
            raise ValueError("OPENAI_API_KEY missing or invalid in .env file.")
        self.client = OpenAI(api_key=api_key)

        with open("centers.json", "r", encoding="utf-8") as f:
            raw_centers = json.load(f)
        self.CENTERS = self.flatten_centers(raw_centers)

        self.collected = {}
        self.step = "name"
        self.fact_injected = 0

    def flatten_centers(self, center_dict):
        flat_list = []
        for city, localities in center_dict.items():
            for locality, address in localities.items():
                flat_list.append({
                    "city": city,
                    "locality": locality,
                    "address": address,
                    "name": address.split(",")[0]
                })
        return flat_list

    def extract_json_from_response(self, response):
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return response.strip()

    def gpt_intent_prompt(self, step, user_input, collected):
        return f"""
You are a helpful assistant for Footprints Preschool admissions. Your job is to extract the required field for the current step, classify the intent, and normalize user input. If the user provides more than one field, extract all relevant ones. If the input is ambiguous, irrelevant, or not matching the expected field, return "invalid".

Current step: {step}
User input: "{user_input}"
Collected so far: {collected}

Instructions:
- For name: Recognize if the input is a likely child's name (not "ok", "maybe", etc.).
- For program: Classify as one of Pre-School, Full Day Care, After School (normalize typos/variants).
- For city/locality: Normalize and expand abbreviations (e.g., "nfc" → "New Friends Colony").
- If user asks a question (FAQ), recognize and extract the question.
- If user wants to change city/locality, extract new values.
- If user provides multiple fields, extract all.
- If input is not relevant, output "invalid".

Examples:
User: "Raj" → {"intent": "provide_name", "name": "Raj"}
User: "Aarav" → {"intent": "provide_name", "name": "Aarav"}
User: "My name is Meera" → {"intent": "provide_name", "name": "Meera"}
User: "This is Kabir" → {"intent": "provide_name", "name": "Kabir"}
User: "It’s Rhea" → {"intent": "provide_name", "name": "Rhea"}
User: "My daughter's name is Anaya" → {"intent": "provide_name", "name": "Anaya"}
User: "Priyanshu" → {"intent": "provide_name", "name": "Priyanshu"}
User: "what's your name?" → {"intent": "invalid"}
User: "hmm" → {"intent": "invalid"}
User: "ok" → {"intent": "invalid"}

User: "I want full day care" → {"intent": "provide_program", "program": "Full Day Care"}
User: "after school" → {"intent": "provide_program", "program": "After School"}
User: "Pre-school please" → {"intent": "provide_program", "program": "Pre-School"}
User: "preschool" → {"intent": "provide_program", "program": "Pre-School"}
User: "daycare" → {"intent": "provide_program", "program": "Full Day Care"}

User: "Delhi" → {"intent": "provide_city", "city": "Delhi"}
User: "Looking in Noida" → {"intent": "provide_city", "city": "Noida"}
User: "Gurgaon" → {"intent": "provide_city", "city": "Gurgaon"}
User: "Change city to Lucknow" → {"intent": "change_city", "city": "Lucknow"}
User: "Can we do Aliganj Lucknow?" → {"intent": "change_city", "city": "Lucknow", "locality": "Aliganj"}

User: "sector 62" → {"intent": "provide_locality", "locality": "Sector 62"}
User: "New Friends Colony" → {"intent": "provide_locality", "locality": "New Friends Colony"}
User: "Change to NFC" → {"intent": "change_locality", "locality": "New Friends Colony"}
User: "no, try sector 104" → {"intent": "change_locality", "locality": "Sector 104"}

User: "Can we do sector 50?" → {"intent": "change_locality", "locality": "Sector 50"}
User: "Actually, Noida sector 50 please" → {"intent": "change_locality", "locality": "Sector 50"}
User: "I want sector 62" → {"intent": "change_locality", "locality": "Sector 62"}

User: "what is the fee?" → {"intent": "faq", "topic": "fee"}
User: "what's the curriculum?" → {"intent": "faq", "topic": "curriculum"}
User: "do you provide meals?" → {"intent": "faq", "topic": "meals"}
User: "how about safety?" → {"intent": "faq", "topic": "safety"}
User: "what are the hours?" → {"intent": "faq", "topic": "operating hours"}

User: "yes" → {"intent": "schedule_visit"}
User: "schedule a visit" → {"intent": "schedule_visit"}
User: "I'd like to come tomorrow" → {"intent": "schedule_visit"}

User: "no thank you" → {"intent": "end_conversation"}
User: "no, I'm good" → {"intent": "end_conversation"}
User: "that's all" → {"intent": "end_conversation"}
User: "bye" → {"intent": "end_conversation"}
User: "nothing else" → {"intent": "end_conversation"}
User: "exit" → {"intent": "end_conversation"}
User: "stop" → {"intent": "end_conversation"}


Respond ONLY in JSON with keys for each field relevant to the step, plus "intent".
"""

    def gpt_faq_prompt(self, user_input):
        return f"""
You are a helpful assistant for Footprints Preschool. The user asked: "{user_input}"
Is this a frequently asked question about preschool services, safety, meals, curriculum, fees, etc.? If so, extract the main topic (e.g., "fees", "safety", "curriculum").
If not, return "not_faq".
Respond with a single word for the topic, or "not_faq".
"""

    def gpt_recommend_center_prompt(self, city, user_locality, centers_in_city):
        center_list = "\n".join(
            [f"- {c['locality']}: {c['address']}" for c in centers_in_city]
        )
        return f"""
You are a helpful assistant for Footprints Preschool admissions.

The user is interested in a center in {city}, specifically near "{user_locality}".

Here are all the available Footprints centers in {city}:
{center_list}

Based on your knowledge of {city}'s geography, which center is closest to or most convenient for someone in or near "{user_locality}"? Respond ONLY with the locality name from the list above.
"""

    def ask_gpt(self, prompt, temperature=0):
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}],
            temperature=temperature,
            max_tokens=256,
        )
        return response.choices[0].message.content.strip()

    def normalize_program(self, text):
        text = text.lower().replace("-", " ").replace("_", " ")
        for key, val in PROGRAMS:
            if key in text:
                return val
        return None

    def random_fact(self):
        return random.choice(FOOTPRINTS_FACTS)

    def find_center(self, city, locality):
        for center in self.CENTERS:
            if center["city"].lower() == city.lower() and center["locality"].lower() == locality.lower():
                return center
        centers_in_city = [c for c in self.CENTERS if c["city"].lower() == city.lower()]
        if not centers_in_city:
            return None
        prompt = self.gpt_recommend_center_prompt(city, locality, centers_in_city)
        gpt_response = self.ask_gpt(prompt)
        print("DEBUG GPT RECOMMEND RESPONSE:", gpt_response)
        for center in centers_in_city:
            if gpt_response.strip().lower() in center["locality"].lower():
                return center
        return centers_in_city[0]

    def print_center(self, center):
        return f"{center['name']} at {center['address']}, {center['city']} ({center['locality']})"

    def answer_faq(self, topic):
        for keyword, response in FAQ_ANSWERS.items():
            if keyword in topic.lower():
                return f"{response}\n\nIs there anything else you'd like to know — like safety, curriculum, or fees?"
        return "I'm not sure about that topic. You can ask me about meals, safety, curriculum, fees, and more!"

    def handle_message(self, user_input):
        faq_topic = self.ask_gpt(self.gpt_faq_prompt(user_input))
        if faq_topic != "not_faq":
            return self.answer_faq(faq_topic)

        prompt = self.gpt_intent_prompt(self.step, user_input, self.collected)
        gpt_response = self.ask_gpt(prompt)
        print("DEBUG GPT RESPONSE:", gpt_response)
        try:
            result = json.loads(self.extract_json_from_response(gpt_response))
        except Exception:
            result = {"intent": "invalid"}

        intent = result.get("intent", "invalid")

        if intent == "end_conversation":
            return "Alright! Feel free to come back anytime. Have a great day!"

        if intent == "invalid":
            return "Sorry, I didn't catch that. Could you please try again?"

        if self.step == "name" and "name" in result:
            self.collected["name"] = result["name"]
            if "program" in result:
                self.collected["program"] = self.normalize_program(result["program"])
            if "city" in result:
                self.collected["city"] = result["city"]
            if "locality" in result:
                self.collected["locality"] = result["locality"]
            self.step = "program" if "program" not in self.collected else "city"
            return f"Thanks {self.collected['name']}! Which program are you interested in?"
        
        if self.step == "program" and "program" in result:
            self.collected["program"] = self.normalize_program(result["program"])
            if "city" in result:
                self.collected["city"] = result["city"]
            if "locality" in result:
                self.collected["locality"] = result["locality"]
            self.step = "city" if "city" not in self.collected else "locality"
            return "Got it! Which city are you looking for a center in?"

        if self.step == "city" and "city" in result:
            city = result["city"]
            city_centers = [c for c in self.CENTERS if c["city"].lower() == city.lower()]
            if not city_centers:
                self.step = "city"
                return f"Sorry, we don't have any centers in or near {city}.\nTry a different city like Noida, Delhi, or Lucknow?"
            self.collected["city"] = city
            if "locality" in result:
                self.collected["locality"] = result["locality"]
            self.step = "locality" if "locality" not in self.collected else "recommend_center"
            return "Thanks! Which locality in the city?"

        if self.step == "locality" and "locality" in result:
            self.collected["locality"] = result["locality"]
            self.step = "recommend_center"

        if self.step == "recommend_center":
            center = self.find_center(self.collected["city"], self.collected["locality"])
            if not center:
                return f"Sorry, no centers found in {self.collected['city']}."
            self.step = "schedule"
            reply = f"Great! The nearest Footprints center is:\n{self.print_center(center)}"
            if self.fact_injected < 1:
                reply += f"\n\nBy the way, did you know? {self.random_fact()}"
                self.fact_injected += 1
            reply += "\nWould you like to schedule a visit, or change city/locality?"
            return reply

        if self.step == "schedule":
            if intent in ["schedule_visit", "yes"]:
                reply = (
                    "Your visit is scheduled! You can visit anytime Monday to Friday, 9:00 AM to 6:30 PM.\n"
                    "Is there anything else I can help you with — like safety, curriculum, meals, or fees?"
                )
                if self.fact_injected < 2:
                    reply += f"\nBy the way, did you know? {self.random_fact()}"
                    self.fact_injected += 1
                return reply
            elif "city" in result or "locality" in result:
                if "city" in result:
                    self.collected["city"] = result["city"]
                if "locality" in result:
                    self.collected["locality"] = result["locality"]
                center = self.find_center(self.collected["city"], self.collected["locality"])
                self.step = "schedule"
                reply = f"\nGot it! The updated nearest Footprints center is:\n{self.print_center(center)}"
                if self.fact_injected < 2:
                    reply += f"\nBy the way, did you know? {self.random_fact()}"
                    self.fact_injected += 1
                reply += "\nWould you like to schedule a visit, or change city/locality?"
                return reply
            else:
                return "Sorry, I didn't catch that. Would you like to schedule a visit or change city/locality?"

        return "Let me know how I can help!"

# Static data kept at bottom
FOOTPRINTS_FACTS = [
    "Footprints was founded by an IIT Delhi alumnus and has 170+ centers across India.",
    "90% of brain development happens by age 6, so early years matter most.",
    "We use the US-based HighScope curriculum, proven to encourage children to explore and learn on their own.",
    "We offer live CCTV feeds so you can watch your child anytime.",
    "All our staff (except guards) are women, with strict background checks and regular health checkups.",
    "We provide healthy, nutritious meals and do not serve junk food or processed snacks.",
    "Parents can pause services, request refunds, and move centers via our app.",
    "If you’re not satisfied, you can request a refund for a day's childcare fees.",
]

FAQ_ANSWERS = {
    "age range": "Our preschool welcomes children aged 12 months to 8 years.",
    "operating hours": "We are open Monday to Friday, 9:00 AM to 6:30 PM. Early/late hours are available at select branches.",
    "curriculum": "We follow the US-based HighScope Curriculum, which encourages social, emotional, and cognitive development through interactive activities.",
    "teacher student ratio": "We maintain a 1:10 teacher-to-student ratio for personalized attention.",
    "meals": "We provide healthy snacks and meals, and accommodate dietary restrictions as needed.",
    "safety": "Footprints prioritizes safety with soft flooring, covered edges, all-women staff, and live CCTV feeds.",
    "cctv": "Parents can watch their child anytime via live CCTV feed on their mobile.",
    "payments": "We offer flexible payment, pause, and refund policies through our app.",
    "development": "Children learn through hands-on experiences guided by qualified staff. Our curriculum emphasizes social and problem-solving skills.",
    "updates": "Parents get regular updates via our app, including meals, activities, and nap times.",
    "fee": "One-Time Charges: Admission Fee ₹16,000, Registration ₹7,000, Welcome Kit ₹7,500. Monthly Fee: Pre School ₹8,999, Daycare ₹15,999, After School ₹7,999.",
    "refund": "We offer a satisfaction guarantee—refunds are available if you’re not satisfied.",
    "pause": "You can pause services if needed—just speak to the center administration.",
    "enroll": "Enroll by filling the admission form on our website or visiting your nearest center.",
    "sibling discount": "Yes, we offer sibling benefits. Please ask at your local center.",
}
