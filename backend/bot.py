import os
import json
import re
import random
from dotenv import load_dotenv
from openai import OpenAI

# --- Utility to clean JSON from Markdown code blocks ---
def extract_json_from_response(response):
    """
    Extract JSON object from a GPT response that may be wrapped in markdown code block.
    """
    # Match triple backticks with optional 'json' and capture the content inside
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return response.strip()

# --- Flatten centers.json ---
def flatten_centers(center_dict):
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

# --- Load environment and OpenAI client ---
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key or not api_key.startswith("sk-"):
    raise ValueError("OPENAI_API_KEY missing or invalid in .env file.")

client = OpenAI(api_key=api_key)

# --- Load and flatten center data ---
with open("centers.json", "r", encoding="utf-8") as f:
    raw_centers = json.load(f)
CENTERS = flatten_centers(raw_centers)

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

FAQS = {
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
    "fee structure": "One-Time Charges: Admission Fee ₹16,000, Registration ₹7,000, Welcome Kit ₹7,500. Monthly Fee: Pre School ₹8,999, Daycare ₹15,999, After School ₹7,999.",
    "refund": "We offer a satisfaction guarantee—refunds are available if you’re not satisfied.",
    "pause": "You can pause services if needed—just speak to the center administration.",
    "enroll": "Enroll by filling the admission form on our website or visiting your nearest center.",
    "sibling discount": "Yes, we offer sibling benefits. Please ask at your local center.",
}

PROGRAMS = [
    ("pre school", "Pre-School"),
    ("preschool", "Pre-School"),
    ("day care", "Full Day Care"),
    ("full day care", "Full Day Care"),
    ("after school", "After School"),
    ("afterschool", "After School"),
]

def gpt_intent_prompt(step, user_input, collected):
    base = f"""
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
User: "Can we do sector 50?" → {{"intent": "change_locality", "locality": "Sector 50"}}
User: "Actually, Noida sector 50 please" → {{"intent": "change_locality", "locality": "Sector 50"}}
User: "Change city to Lucknow" → {{"intent": "change_city", "city": "Lucknow"}}
User: "Can we do Aliganj Lucknow?" → {{"intent": "change_city", "city": "Lucknow", "locality": "Aliganj"}}
User: "yes" → {{"intent": "schedule_visit"}}
User: "schedule a visit" → {{"intent": "schedule_visit"}}
User: "no, try sector 104" → {{"intent": "change_locality", "locality": "Sector 104"}}
User: "I want sector 62" → {{"intent": "change_locality", "locality": "Sector 62"}}
User: "what is the fee?" → {{"intent": "faq", "topic": "fee"}}
User: "ok" → {{"intent": "invalid"}}
User: "no thank you" → {{"intent": "end_conversation"}}
User: "no, I'm good" → {{"intent": "end_conversation"}}
User: "that's all" → {{"intent": "end_conversation"}}
User: "bye" → {{"intent": "end_conversation"}}

Respond ONLY in JSON with keys for each field relevant to the step, plus "intent" (e.g., "provide_name", "faq", "change_city", "change_locality", "invalid", etc.).
"""
    return base


def gpt_faq_prompt(user_input):
    return f"""
You are a helpful assistant for Footprints Preschool. The user asked: "{user_input}"
Is this a frequently asked question about preschool services, safety, meals, curriculum, fees, etc.? If so, extract the main topic (e.g., "fees", "safety", "curriculum").
If not, return "not_faq".
Respond with a single word for the topic, or "not_faq".
"""

def gpt_recommend_center_prompt(city, user_locality, centers_in_city):
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

def ask_gpt(prompt, temperature=0):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt}],
        temperature=temperature,
        max_tokens=256,
    )
    return response.choices[0].message.content.strip()

def random_fact():
    return random.choice(FOOTPRINTS_FACTS)

def normalize_program(text):
    text = text.lower().replace("-", " ").replace("_", " ")
    for key, val in PROGRAMS:
        if key in text:
            return val
    return None

def find_center(city, locality):
    # Try exact match first
    for center in CENTERS:
        if center["city"].lower() == city.lower() and center["locality"].lower() == locality.lower():
            return center

    # Gather all centers in the city
    centers_in_city = [c for c in CENTERS if c["city"].lower() == city.lower()]
    if not centers_in_city:
        return None

    # Use GPT to recommend the best one
    prompt = gpt_recommend_center_prompt(city, locality, centers_in_city)
    gpt_response = ask_gpt(prompt)
    print("DEBUG GPT RECOMMEND RESPONSE:", gpt_response)

    # Try to find the center whose locality matches GPT's response
    for center in centers_in_city:
        if gpt_response.strip().lower() in center["locality"].lower():
            return center

    # Fallback: return the first center in the city
    return centers_in_city[0]

def print_center(center):
    return f"{center['name']} at {center['address']}, {center['city']} ({center['locality']})"

def answer_faq(topic):
    detailed_answers = {
        "meals": (
            "We provide healthy, home-cooked meals and snacks throughout the day. "
            "We also accommodate dietary restrictions and never serve junk food or processed items. "
            "Your child’s nutrition and safety are top priorities for us."
        ),
        "safety": (
            "Safety is at the core of everything we do. Our centers have soft flooring, covered edges, "
            "all-women staff, and strict background checks. You can also watch your child via live CCTV feed anytime."
        ),
        "curriculum": (
            "We follow the US-based HighScope Curriculum, which emphasizes active learning through exploration. "
            "This helps build social, emotional, and cognitive skills in a fun and engaging way."
        ),
        "fee": (
            "Our fees include one-time charges like Admission Fee ₹16,000, Registration ₹7,000, and a Welcome Kit for ₹7,500. "
            "Monthly fees vary by program: ₹8,999 for Pre-School, ₹15,999 for Full Day Care, and ₹7,999 for After School."
        ),
        "teacher student ratio": (
            "We maintain a 1:10 teacher-to-student ratio, ensuring each child gets personal attention and care."
        ),
        "cctv": (
            "Absolutely! Parents can view live CCTV feeds of their child from anywhere using our mobile app — anytime during center hours."
        ),
        "pause": (
            "Yes, you can pause services anytime via our app or by speaking to the center administration. We aim to stay flexible for families."
        ),
        "refund": (
            "We offer a satisfaction guarantee. If you're not happy with the service, you can request a refund for that day’s childcare."
        ),
        "development": (
            "Our program focuses on hands-on experiences, guided by trained educators. Kids develop social, cognitive, and motor skills "
            "in a structured yet fun environment."
        ),
        "updates": (
            "You'll receive regular updates about your child's day — including meals, naps, and activities — directly through our app."
        ),
        "enroll": (
            "You can enroll by visiting the nearest center or filling out the admission form on our website. We're here to assist every step of the way!"
        ),
        "operating hours": (
            "We're open Monday to Friday, from 9:00 AM to 6:30 PM. Some branches also offer early drop-offs and late pickups."
        ),
        "sibling discount": (
            "Yes, we do offer sibling benefits. Please check with your local center for exact details and eligibility."
        ),
        "age range": (
            "We welcome children aged 12 months to 8 years in our preschool and daycare programs."
        )
    }

    for keyword, response in detailed_answers.items():
        if keyword in topic.lower():
            return f"{response}\n\nIs there anything else you'd like to know — like safety, curriculum, or fees?"

    return "I'm not sure about that topic. You can ask me about meals, safety, curriculum, fees, and more!"


def main():
    print("👋 Hello! Welcome to Footprints Preschool Admissions.")
    collected = {}
    step = "name"
    fact_injected = 0  # Track how many times a fact has been printed (max 2)

    while True:
        if step == "name":
            print("\nMay I know your child's name?")
        elif step == "program":
            print("\nWhich program are you interested in? (Pre-School, Full Day Care, After School)")
        elif step == "city":
            print("\nWhich city are you looking for a center in?")
        elif step == "locality":
            print("\nWhich locality in the city?")

        user_input = input("> ").strip()

        # FAQ/Interrupt Handling
        faq_topic = ask_gpt(gpt_faq_prompt(user_input))
        if faq_topic != "not_faq":
            print(answer_faq(faq_topic))
            # Only inject a fact if we're in a scheduling/recommendation step
            if step in ["recommend_center", "schedule"] and fact_injected < 2:
                print(f"By the way, did you know? {random_fact()}")
                fact_injected += 1
            continue

        prompt = gpt_intent_prompt(step, user_input, collected)
        gpt_response = ask_gpt(prompt)
        print("DEBUG GPT RESPONSE:", gpt_response)
        clean_response = extract_json_from_response(gpt_response)
        try:
            result = json.loads(clean_response)
        except Exception:
            result = {"intent": "invalid"}

        intent = result.get("intent", "invalid")

        # 🔹 Handle polite conversation ending
        if intent == "end_conversation":
            print("Alright! Feel free to come back anytime. Have a great day!")
            break

        if intent == "invalid":
            print("Sorry, I didn't catch that. Could you please try again?")
            continue


        # Collect data based on intent and step
        if step == "name" and "name" in result and result["name"]:
            collected["name"] = result["name"]
            if "program" in result:
                collected["program"] = normalize_program(result["program"])
            if "city" in result:
                collected["city"] = result["city"]
            if "locality" in result:
                collected["locality"] = result["locality"]
            step = "program" if "program" not in collected else "city"
            continue
        elif step == "program" and "program" in result and result["program"]:
            collected["program"] = normalize_program(result["program"])
            if not collected["program"]:
                print("Could you clarify if you're looking for Pre-School, Full Day Care, or After School?")
                continue
            if "city" in result:
                collected["city"] = result["city"]
            if "locality" in result:
                collected["locality"] = result["locality"]
            step = "city" if "city" not in collected else "locality"
            continue
        elif step == "city" and "city" in result and result["city"]:
            city = result["city"]
            city_centers = [c for c in CENTERS if c["city"].lower() == city.lower()]
            
            if not city_centers:
                print(f"Sorry, we don't have any centers in or near {city}.")
                print("We currently operate in cities like Noida, Delhi, Gurgaon, and Lucknow.")
                print("Would you like to try a different city?")
                step = "city"
                continue

            collected["city"] = city
            if "locality" in result:
                collected["locality"] = result["locality"]
            step = "locality" if "locality" not in collected else "recommend_center"
            continue

        elif step == "locality" and "locality" in result and result["locality"]:
            collected["locality"] = result["locality"]
            step = "recommend_center"

        # Center recommendation and scheduling loop
        if step == "recommend_center":
            city_centers = [c for c in CENTERS if c["city"].lower() == collected["city"].lower()]
            if not city_centers:
                print(f"Sorry, we don't have any centers in or near {collected['city']}.")
                print("Would you like to try a different city?")
                step = "city"
                continue
            center = find_center(collected["city"], collected["locality"])
            if center:
                print(f"\nGreat! The nearest Footprints center is:\n{print_center(center)}")
                print("Would you like to schedule a visit, or change city/locality?")
                if fact_injected < 1:
                    print(f"By the way, did you know? {random_fact()}")
                    fact_injected += 1
                # Now handle scheduling or locality/city change
                while True:
                    user_input = input("> ").strip()
                    faq_topic = ask_gpt(gpt_faq_prompt(user_input))
                    if faq_topic != "not_faq":
                        print(answer_faq(faq_topic))
                        if fact_injected < 2:
                            print(f"By the way, did you know? {random_fact()}")
                            fact_injected += 1
                        continue
                    prompt = gpt_intent_prompt("schedule", user_input, collected)
                    gpt_response = ask_gpt(prompt)
                    print("DEBUG GPT RESPONSE:", gpt_response)
                    clean_response = extract_json_from_response(gpt_response)
                    try:
                        result = json.loads(clean_response)
                    except Exception:
                        result = {"intent": "invalid"}
                    intent = result.get("intent", "invalid")
                    if intent == "end_conversation":
                        print("Alright! Feel free to come back anytime. Have a great day!")
                        break
                    # If the user wants to schedule a visit (and hasn't changed city/locality)
                    if intent in ["schedule_visit", "yes"]:
                        print("Your visit is scheduled! You can visit anytime Monday to Friday, 9:00 AM to 6:30 PM.")
                        print("Is there anything else I can help you with — like safety, curriculum, meals, or fees?")
                        if fact_injected < 2:
                            print(f"By the way, did you know? {random_fact()}")
                            fact_injected += 1
                        step = "schedule"  # keep user in the loop
                        continue  # continue interaction
                    # If the user wants to change city/locality, break out and re-run recommendation
                    elif "city" in result or "locality" in result:
                        if "city" in result:
                            collected["city"] = result["city"]
                        if "locality" in result:
                            collected["locality"] = result["locality"]
                        
                        # Instantly re-run recommendation logic
                        center = find_center(collected["city"], collected["locality"])
                        if center:
                            print(f"\nGot it! The updated nearest Footprints center is:\n{print_center(center)}")
                            print("Would you like to schedule a visit, or change city/locality?")
                            if fact_injected < 2:
                                print(f"By the way, did you know? {random_fact()}")
                                fact_injected += 1
                        continue  # Restart inner loop with updated recommendation
                    else:
                        print("Sorry, I didn't catch that. Would you like to schedule a visit or change city/locality?")
                    # continue inner loop for more input
                continue  # Go back to main while loop to re-run recommendation

if __name__ == "__main__":
    main()
