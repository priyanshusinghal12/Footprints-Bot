import json
import openai
import difflib
from dotenv import load_dotenv

client = openai.OpenAI()

# Load center data
with open("centers.json", "r") as f:
    raw_centers = json.load(f)

# Convert nested dict into list of center entries
def flatten_centers(center_dict):
    flat_list = []
    for city, localities in center_dict.items():
        for locality, address in localities.items():
            flat_list.append({
                "city": city,
                "locality": locality,
                "address": address
            })
    return flat_list

centers = flatten_centers(raw_centers)

# Simulated GPT-based field extraction (replace with OpenAI call if needed)
def get_intent_and_entity(user_input, expected_type=None):
    user_input = user_input.strip().lower()

    if expected_type == "name":
        if user_input in ["ok", "maybe", "idk", "yes", "no"]:
            return {"intent": "invalid", "value": None}
        return {"intent": "name", "value": user_input.title()}

    elif expected_type == "program":
        keywords = {
            "pre": "Pre-School",
            "day": "Full Day Care",
            "after": "After School",
            "school": "After School"
        }
        for k, v in keywords.items():
            if k in user_input:
                return {"intent": "program", "value": v}
        return {"intent": "invalid", "value": None}

    elif expected_type == "city":
        city_names = list(raw_centers.keys())
        match = difflib.get_close_matches(user_input.title(), city_names, n=1, cutoff=0.6)
        if match:
            return {"intent": "city", "value": match[0]}
        return {"intent": "invalid", "value": None}

    elif expected_type == "locality":
        all_localities = [c["locality"] for c in centers]
        match = difflib.get_close_matches(user_input.title(), all_localities, n=1, cutoff=0.6)
        if match:
            return {"intent": "locality", "value": match[0]}
        return {"intent": "invalid", "value": None}

    elif expected_type == "faq":
        if any(x in user_input for x in ["fee", "price", "cost"]):
            return {"intent": "faq", "value": "fee"}
        if "safety" in user_input:
            return {"intent": "faq", "value": "safety"}
        if any(x in user_input for x in ["meal", "food"]):
            return {"intent": "faq", "value": "meals"}
    return {"intent": "unknown", "value": None}

def faq_answer(topic):
    if topic == "fee":
        return ("📌 One-Time Charges:\n- Admission Fee: ₹16,000\n- Registration: ₹7,000\n- Welcome Kit: ₹7,500\n\n"
                "📌 Monthly Fees:\n- Pre-School: ₹8,999\n- Daycare: ₹15,999\n- After School: ₹7,999")
    elif topic == "safety":
        return ("We prioritize your child’s safety with Live CCTV access, all-women staff, biometric entry, and cushioned infrastructure.")
    elif topic == "meals":
        return ("We serve nutritious, home-cooked meals with no junk food. Special diets can be accommodated.")

def recommend_center(city, locality):
    for center in centers:
        if center["city"].lower() == city.lower() and locality.lower() in center["locality"].lower():
            return center
    for center in centers:
        if center["city"].lower() == city.lower():
            return center
    return None

# Chatbot flow
def chatbot():
    print("👋 Hi! I'm your assistant from Footprints Preschool. Let’s find the best program for your child.")

    while True:
        name_input = input("What’s your child's name?\n> ")
        result = get_intent_and_entity(name_input, "name")
        if result["intent"] == "name":
            child_name = result["value"]
            break
        print("I didn’t catch that. Could you please share your child's name again?")

    while True:
        program_input = input(f"What program are you looking for {child_name}? (Pre-School / Daycare / After School)\n> ")
        result = get_intent_and_entity(program_input, "program")
        if result["intent"] == "program":
            program = result["value"]
            break
        print("Please clarify if you want Pre-School, Full Day Care, or After School.")

    while True:
        city_input = input("Which city are you in?\n> ")
        result = get_intent_and_entity(city_input, "city")
        if result["intent"] == "city":
            city = result["value"]
            break
        print("Sorry, I didn’t recognize that city. Could you try again?")

    while True:
        locality_input = input(f"Which locality in {city}?\n> ")
        result = get_intent_and_entity(locality_input, "locality")
        if result["intent"] == "locality":
            locality = result["value"]
            break
        print("Hmm, could you please retype the locality name?")

    center = recommend_center(city, locality)
    if center:
        print(f"✅ The closest center is:\n📍 {center['address']}")
        print("Fun fact: Footprints was founded by an IIT Delhi alumnus and has 170+ centers across India!")
    else:
        print("😕 Sorry, we couldn’t find an exact match. Want to try another locality or city?")

    while True:
        next_input = input("Would you like to schedule a visit, or try a different city/locality?\n> ")
        if "schedule" in next_input.lower():
            print("✅ Your visit is scheduled! You can visit anytime Monday to Friday, 9:00 AM to 6:30 PM.")
            break

        faq_check = get_intent_and_entity(next_input, "faq")
        if faq_check["intent"] == "faq":
            print(faq_answer(faq_check["value"]))
            continue

        city_check = get_intent_and_entity(next_input, "city")
        if city_check["intent"] == "city":
            city = city_check["value"]
            locality_input = input(f"Which locality in {city}?\n> ")
            locality_check = get_intent_and_entity(locality_input, "locality")
            if locality_check["intent"] == "locality":
                locality = locality_check["value"]
                center = recommend_center(city, locality)
                if center:
                    print(f"✅ Updated! Nearest center is:\n📍 {center['address']}")
                    continue
        print("Let me know if you want to schedule a visit or ask something else!")

    print("Any other questions I can help with? 😊")

# Run
if __name__ == "__main__":
    chatbot()
