import json
import re
import random
from dataclasses import dataclass
from typing import Optional, Dict, List
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

@dataclass
class UserState:
    child_name: Optional[str] = None
    child_age: Optional[int] = None
    program: Optional[str] = None
    city: Optional[str] = None
    locality: Optional[str] = None
    phone_number: Optional[str] = None
    selected_center: Optional[str] = None

    def is_complete(self) -> bool:
        return all([self.child_name, self.program, self.city])

    def missing_info(self) -> List[str]:
        missing = []
        if not self.child_name or self.child_name.strip() == "":
            missing.append("child's name")
        if not self.program:
            missing.append("program preference")
        if not self.city:
            missing.append("city")
        return missing

class FootprintsBot:
    def __init__(self):
        self.llm = ChatOpenAI(temperature=0.3, model="gpt-4")
        with open("centers.json", "r") as f:
            self.centers = json.load(f)

        self.facts = [
            "By the way, did you know we offer Live CCTV access so you can check on your child anytime? 😊",
            "Fun fact: We use the HighScope curriculum — a US-based, research-backed learning method.",
            "Also, all our staff (except guards) are women, background-checked, and trained.",
            "Our meals are healthy, cooked fresh daily — no junk food is served.",
            "You receive daily updates via the Footprints App on naps, meals & activities.",
            "We offer flexible refunds, pause options, and a same-day satisfaction refund."
        ]

        self.fact_index = 0
        self.state = UserState()
        self.locality_asked = False
        self.centers_provided = False
        self.user_message_count = 0
        self.no_center_warned = False
        self.awaiting_final_confirmation = False
        self.chat_ended = False
        self.visit_scheduled = False

    def is_valid_name(self, name: str) -> bool:
        if not name or len(name) < 2:
            return False
        name_lower = name.strip().lower()
        forbidden = {
            "ok", "no", "yes", "test", "thanks", "thank you", "hello", "hi", "bye", "goodbye",
            "none", "parent", "child", "please", "help", "sure", "fine", "alright", "cool", "fuck",""
        }
        if name_lower in forbidden:
            return False
        # Only allow alphabetic names with optional hyphen/apostrophe/spaces
        if not re.match(r"^[a-zA-Z][a-zA-Z\s\-']+$", name):
            return False
        return True
    
    #no change

    def extract_information(self, user_input: str) -> Dict:
        city_list = list(self.centers.keys())
        all_localities = []
        for city in self.centers.values():
            all_localities.extend(city.keys())
        program_list = ["Pre-School", "Full Day Care", "Daycare", "After School"]

        prompt = f"""
    Extract as much information as possible from the following message for a preschool inquiry. 
    Only output a valid JSON object as described below. Do not include any explanation or extra text.

    Message: "{user_input}"

    Rules:
    - Only extract 'child_name' if it is a real human name (not a conversational phrase or random word).
    - For program, city, and locality, correct typos using the valid lists below.

    Valid cities: {', '.join(city_list)}
    Valid localities: {', '.join(all_localities)}
    Valid programs: {', '.join(program_list)}

    JSON format:
    {{
    "child_name": null or string (only if real name),
    "child_age": null or integer,
    "program": null or one of {program_list},
    "city": null or one of {city_list},
    "locality": null or one of the localities above,
    "phone_number": null or string,
    "new_locality": null or one of the localities above,
    "intent": null or one of ["schedule_visit", "change_locality", "faq", "provide_info", "none"],
    "faq_topics": list of strings (e.g. ["safety", "meals"])
    }}

    Only output the JSON object.
    """
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            info = json.loads(response.content)
            return info
        except Exception as e:
            print("EXTRACTION ERROR:", e)
            return {}


    def update_state(self, extracted: Dict):
        if extracted.get("child_name") is not None:
            name = extracted["child_name"].strip().title() if extracted["child_name"] else None
            if name:
                self.state.child_name = name
        if extracted.get("child_age") is not None:
            try:
                self.state.child_age = int(extracted["child_age"])
                if not self.state.program:
                    self.state.program = self._recommend_program()
            except Exception:
                pass
        if extracted.get("program") is not None:
            prog = extracted["program"].strip().title() if extracted["program"] else None
            if prog:
                self.state.program = prog
        if extracted.get("city") is not None:
            city = extracted["city"].strip().title() if extracted["city"] else None
            if city:
                self.state.city = city
        if extracted.get("locality") is not None:
            loc = extracted["locality"].strip().title() if extracted["locality"] else None
            if loc:
                self.state.locality = loc
        if extracted.get("phone_number") is not None:
            phone = extracted["phone_number"].strip() if extracted["phone_number"] else None
            if phone:
                self.state.phone_number = phone

    def _recommend_program(self) -> str:
        if not self.state.child_age:
            return ""
        age = self.state.child_age
        if age < 1: return "Daycare"
        if 1 <= age < 4: return "Pre-School"
        if 4 <= age <= 8: return "After School"
        return "Daycare"

    def generate_name_acknowledgment(self, child_name: str) -> str:
        prompt = (
            f"You are Arjun, a friendly and warm parent relations agent for Footprints Preschool. "
            f"A parent just told you their child's name is '{child_name}'. "
            f"Reply with a simple, short, and natural compliment about the name, like 'That's a lovely name!'. "
            f"Keep it casual and avoid flowery or elaborate phrases. Use an emoji. "
            f"Do not ask any follow-up questions, just acknowledge the name."
        )
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content.strip()
        except Exception:
            return f"That's a lovely name, {child_name}! 😊"

    def find_centers(self) -> Dict:
        if self.state.locality and re.search(r"\b(i don't know|idk|dont know|no idea|not sure)\b", self.state.locality, re.I):
            all_centers = []
            for city in self.centers.values():
                all_centers.extend(list(city.values()))
            random_centers = random.sample(all_centers, min(5, len(all_centers)))
            return {"found": True, "random": True, "centers": random_centers}

        if not self.state.city:
            return {"found": False}

        city_match = None
        for c in self.centers.keys():
            if self.state.city.lower() in c.lower() or c.lower() in self.state.city.lower():
                city_match = c
                break

        if not city_match:
            prompt = (
                f"You are a helpful assistant. The user asked for centers in '{self.state.city}'. "
                f"Here is a list of cities with Footprints centers: {', '.join(self.centers.keys())}. "
                f"Which city from this list is geographically closest to '{self.state.city}'? "
                f"Consider typos or misspellings. Reply with only the closest city name, or say 'none'."
            )
            try:
                response = self.llm.invoke([HumanMessage(content=prompt)])
                closest_city = response.content.strip()
                if closest_city.lower() != "none" and closest_city in self.centers:
                    return {
                        "found": False,
                        "message": f"We don't have centers in {self.state.city}, but our nearest city is {closest_city}. Would you like to see options there?"
                    }
            except Exception:
                pass
            return {
                "found": False,
                "message": "We currently don't have centers near your location. A team member will reach out soon. 😊"
            }

        centers = self.centers[city_match]
        if self.state.locality:
            for loc in centers.keys():
                if self.state.locality.lower() in loc.lower():
                    return {
                        "found": True,
                        "exact": True,
                        "address": centers[loc],
                        "city": city_match,
                        "locality": loc
                    }
            prompt = (
                f"You are a helpful assistant for Footprints Preschool. "
                f"The user asked for centers in locality '{self.state.locality}' in city '{city_match}'. "
                f"Here are the available localities: {', '.join(centers.keys())}. "
                f"Please identify the locality from this list that is geographically or numerically closest to '{self.state.locality}', "
                f"even if the user's input contains typos, misspellings, or a nearby sector number. "
                f"For example, if the user says 'Sector 50', and there is a 'Sector 51' in the list, return the closest one. "
                f"Reply with only the closest locality name from the list, or say 'none' if no reasonable match."
            )
            try:
                response = self.llm.invoke([HumanMessage(content=prompt)])
                closest_locality = response.content.strip()
                if closest_locality.lower() != "none" and closest_locality in centers:
                    return {
                        "found": True,
                        "exact": False,
                        "closest_locality": closest_locality,
                        "address": centers[closest_locality],
                        "city": city_match,
                        "requested_locality": self.state.locality
                    }
            except Exception:
                pass
            return {
                "found": False,
                "message": f"We don't have centers in {self.state.locality}, {city_match}. Would you like to see other localities in {city_match} or try a different city?"
            }

        return {
            "found": False,
            "message": "Could you share your locality/sector? This helps me find the nearest center! 📍"
        }

    def _handle_center_response(self) -> str:
        center_info = self.find_centers()

        if not center_info["found"]:
            self.awaiting_final_confirmation = True
            return center_info["message"]

        if center_info.get("random"):
            centers = "\n".join([f"📍 {c}" for c in center_info["centers"]])
            return f"Here are some centers you might like:\n{centers}\nLet me know if any work for you! 😊"

        if center_info.get("exact"):
            addr = center_info["address"]
            self.state.selected_center = addr
            return (
                f"Found a center near you! 🎉\n"
                f"📍 {addr}\n"
                f"Shall I connect you with the manager or schedule a visit? 😊"
            )

        if center_info.get("closest_locality"):
            addr = center_info["address"]
            self.state.selected_center = addr
            return (
                f"We don't have centers in {center_info['requested_locality']}, but our closest center is in {center_info['closest_locality']}:\n"
                f"📍 {addr}\n"
                f"Would you like to proceed with this center, or try another locality or city? 😊"
            )

        if center_info.get("centers"):
            centers = "\n".join([f"📍 {c}" for c in center_info["centers"]])
            return f"We have multiple centers in {center_info['city']}:\n{centers}\nWhich one works best for you? 😊"

    def generate_response(self, user_input: str) -> str:
        self.user_message_count += 1

        # Use GPT to extract all possible info (including robust name detection)
        extracted = self.extract_information(user_input)
        self.update_state(extracted)
        missing = self.state.missing_info()

        # If name was just provided in this message, acknowledge it warmly and continue
        if "child's name" not in missing and extracted.get("child_name"):
            ack = self.generate_name_acknowledgment(self.state.child_name)
            if self.state.child_age:
                prog_suggestion = f"Based on {self.state.child_name}'s age, our {self.state.program} program would be perfect! Should I proceed with this? 😊"
                return f"{ack}\n{prog_suggestion}"
            else:
                prog_prompt = (
                    "Which program are you considering? We offer:\n"
                    "- Pre-School (9:00 AM to 12:30 PM)\n"
                    "- Full Day Care (Pre-School + Daycare, 9:00 AM to 6:30 PM)\n"
                    "- After School (3:30 PM to 6:30 PM)\n"
                    "All programs operate Monday to Friday at every center. 📚"
                )
                return f"{ack}\n{prog_prompt}"

        # If name is missing or invalid (GPT couldn't extract a plausible name)
        if "child's name" in missing:
            return (
                "I didn't catch a valid name there. Could you please tell me your child's name? 👶"
            )

        valid_programs = [
            "Pre-School", "Full Day Care", "Daycare", "After School"
        ]
        program_input = (extracted.get("program") or "").strip().lower()
        valid_programs_lower = [p.lower() for p in valid_programs]

        if "program preference" in missing:
            # If user gave an unclear/irrelevant answer, clarify
            if user_input.strip() and (not program_input or program_input not in valid_programs_lower):
                return (
                    "I didn't quite understand that. Could you please clarify which program you want? These are the programs we offer:\n"
                    "- Pre-School (9:00 AM to 12:30 PM)\n"
                    "- Full Day Care (Pre-School + Daycare, 9:00 AM to 6:30 PM)\n"
                    "- After School (3:30 PM to 6:30 PM)\n"
                    "Please reply with the program name or number. 📚"
                )
            return (
                "Which program are you considering? We offer:\n"
                "- Pre-School (9:00 AM to 12:30 PM)\n"
                "- Full Day Care (Pre-School + Daycare, 9:00 AM to 6:30 PM)\n"
                "- After School (3:30 PM to 6:30 PM)\n"
                "All programs operate Monday to Friday at every center. 📚"
            )

        # Robust city prompt
        if "city" in missing:
            return (
                "I didn't quite get the city name. Could you please tell me which city you're located in? 🏙️"
            )

        # Robust locality/sector prompt
        if self.state.city and not self.state.locality and not self.locality_asked:
            self.locality_asked = True
            return (
                "I didn't catch your locality or sector. Could you please share it? This helps me find the nearest center! 📍"
            )

        # If user says "I don't know" or similar for locality, recommend random centers
        if (self.state.locality and re.search(r"\b(i don't know|idk|dont know|no idea|not sure)\b", self.state.locality, re.I)) and not self.centers_provided:
            self.centers_provided = True
            return self._handle_center_response()

        # If both city and locality are provided, recommend the best/nearest center
        if self.state.city and self.state.locality and not self.centers_provided:
            self.centers_provided = True
            return self._handle_center_response()

        # For any other unclear/irrelevant answer, clarify
        return (
            "I didn't quite understand that. Could you please rephrase or clarify your response? 😊"
        )



    def _inject_fact(self) -> Optional[str]:
        if self.user_message_count % 3 == 0:
            fact = self.facts[self.fact_index]
            self.fact_index = (self.fact_index + 1) % len(self.facts)
            return fact
        return None

    def _get_program_timings(self, program: str) -> str:
        if program == "Pre-School":
            return "9:00 AM to 12:30 PM"
        elif program == "Daycare":
            return "9:00 AM to 6:30 PM (Full Day Care)"
        elif program == "After School":
            return "3:30 PM to 6:30 PM"
        return ""

    def _get_fee_structure(self, program: str) -> str:
        if program == "Pre-School":
            monthly = "₹8,999"
        elif program == "Daycare":
            monthly = "₹15,999"
        elif program == "After School":
            monthly = "₹7,999"
        else:
            monthly = "—"
        return f"""
One-Time Charges:
- Admission Fee: ₹16,000
- Registration: ₹7,000
- Welcome Kit: ₹7,500

Monthly Fee for {program}: {monthly}
"""

    def handle_message(self, user_input: str) -> str:
        # Extract info and lowercase input for intent checks
        extracted = self.extract_information(user_input)
        user_lower = user_input.strip().lower()

        # End chat if user says no/thanks/bye at any point
        if re.search(r'\b(no( thank you| thanks)?|nothing|nope|nah|bye|exit|quit|thank you)\b', user_lower):
            self.chat_ended = True
            return "Thank you for chatting with Footprints Preschool! If you have any more questions, feel free to reach out. Have a wonderful day! 🌟"

        # End chat if user says goodbye after no centers found
        if self.awaiting_final_confirmation:
            if re.search(r'\b(no|nothing|nope|nah|bye|exit|quit)\b', user_lower):
                self.chat_ended = True
                self.awaiting_final_confirmation = False
                return "Thank you for chatting with Footprints Preschool! Have a wonderful day! 🌟"
            else:
                self.awaiting_final_confirmation = False

        if self.chat_ended:
            return "Thank you for your interest! Our team will be in touch soon. If you have any other questions, feel free to ask."

        # Handle changing city/locality/program at any time
        update_needed = False
        new_locality = extracted.get("new_locality") or extracted.get("locality")
        new_city = extracted.get("city")
        new_program = extracted.get("program")
        if new_city and (not self.state.city or new_city.strip().lower() != self.state.city.lower()):
            self.state.city = new_city.strip().title()
            update_needed = True
        if new_locality and (not self.state.locality or new_locality.strip().lower() != self.state.locality.lower()):
            self.state.locality = new_locality.strip().title()
            update_needed = True
        if new_program and (not self.state.program or new_program.strip().lower() != self.state.program.lower()):
            self.state.program = new_program.strip().title()
            update_needed = True
        if update_needed:
            self.centers_provided = False
            self.visit_scheduled = False
            return self._handle_center_response()

        # If user provides a new locality directly (even without "try" etc.), update and rerun center search
        if self.state.city and extracted.get("locality"):
            if extracted["locality"].strip().lower() != (self.state.locality or "").lower():
                self.state.locality = extracted["locality"].strip().title()
                self.centers_provided = False
                self.visit_scheduled = False
                return self._handle_center_response()

        # Always schedule a visit if requested and a center is selected
        if self.state.selected_center and re.search(r'\b(schedule|visit|yes|book|arrange|proceed|ok|sure|go ahead|let\'s do it|confirm)\b', user_lower):
            self.visit_scheduled = True
            timings = self._get_program_timings(self.state.program)
            include_fees = re.search(r'\b(fee|fees|charges|payment|cost|price)\b', user_lower)
            response = (
                f"Thank you, {self.state.child_name}'s parent! Your visit to {self.state.selected_center} has been scheduled.\n"
                f"Program: {self.state.program}\n"
                f"Timings: {timings} (Monday to Friday)\n\n"
            )
            if include_fees:
                fees = self._get_fee_structure(self.state.program)
                response += f"Fee Structure:\n{fees}\n\n"
            response += (
                "You can visit us anytime between Monday to Friday, 9:30 AM to 6:30 PM.\n"
                "Would you like to know more about our safety, curriculum, or anything else? 😊"
            )
            return response

        # Handle visit time question after scheduling
        if self.visit_scheduled and re.search(r'\b(time|timing|when|visit|appointment)\b', user_lower):
            return "Your visit can be scheduled anytime between Monday to Friday, 9:30 AM to 6:30 PM. Is there anything else I can help you with?"

        # Multi-topic FAQ handling (human-like, covers all Footprints topics)
        if self.centers_provided and self.state.selected_center:
            faq_responses = []
            faq_topics = extracted.get("faq_topics", [])
            if 'safety' in faq_topics or re.search(r'\b(safety|secure|hygiene|cctv|security)\b', user_lower):
                faq_responses.append(
                    "Safety is our top priority! 🌟\n"
                    "- Live CCTV access for parents\n"
                    "- All-women staff (except guards)\n"
                    "- Secure entry with biometric access\n"
                    "- Regular health and background checks\n"
                    "- Soft flooring, cushioned walls, and child-safe infrastructure"
                )
            if 'meals' in faq_topics or re.search(r'\b(meal|food|nutrition|lunch|snack|diet)\b', user_lower):
                faq_responses.append(
                    "Our meals are healthy, cooked fresh daily, and designed by nutritionists. We serve a balanced diet with no junk food, and you get daily meal updates via the Footprints app."
                )
            if 'curriculum' in faq_topics or re.search(r'\b(curriculum|learning|education)\b', user_lower):
                faq_responses.append(
                    "We use the HighScope curriculum, a US-based, research-backed method that makes learning fun and engaging. It encourages children to explore, experiment, and learn on their own."
                )
            if 'why_footprints' in faq_topics or re.search(r'\b(why footprints|about footprints|what makes footprints|special about footprints|choose footprints|usp|unique)\b', user_lower):
                faq_responses.append(
                    "Footprints is trusted by thousands of parents for our transparent, research-backed approach to childcare. We offer:\n"
                    "- Live CCTV access\n"
                    "- All-women staff\n"
                    "- US-based HighScope curriculum\n"
                    "- Daily updates via app\n"
                    "- Flexible refunds and satisfaction guarantees\n"
                    "We believe in nurturing every child's unique potential in a safe, loving environment."
                )
            if faq_responses:
                return "\n\n".join(faq_responses) + "\nWould you like to know anything else?"

        # Handle FAQs and program details (fees, timings, etc.)
        if re.search(r'\b(fee|fees|charges|payment|cost|price)\b', user_lower):
            fees = self._get_fee_structure(self.state.program if self.state.program else "Pre-School")
            return f"Here are our fee details:\n{fees}\nWould you like to know anything else?"

        if re.search(r'\b(timing|time|schedule|hours)\b', user_lower):
            timings = self._get_program_timings(self.state.program if self.state.program else "Pre-School")
            return f"Our {self.state.program if self.state.program else 'Pre-School'} timings are {timings}. Would you like details for another program?"

        if re.search(r'\b(phone|number|contact)\b', user_input, re.I):
            return "Could you share your phone number? We'll have our team contact you! 📱"

        # Center selection logic (user mentions a center by name/address)
        if self.centers_provided and not self.state.selected_center:
            selected_center = None
            selected_address = None
            for city, centers in self.centers.items():
                for center_name, address in centers.items():
                    if center_name.lower() in user_lower or address.lower() in user_lower:
                        selected_center = center_name
                        selected_address = address
                        break
                if selected_center:
                    break
            if selected_center:
                self.state.selected_center = selected_address
                return (
                    f"Great choice, {self.state.child_name if self.state.child_name else 'your'} parent! "
                    f"Would you like to schedule a visit at our {selected_center} center or speak with our center manager? 😊"
                )

        # Standard flow for anything else (including initial info collection, fallback)
        response = self.generate_response(user_input)
        fact = self._inject_fact()
        if fact and not self.visit_scheduled and "Live CCTV access for parents" not in response:
            return f"{response}\n\n{fact}"
        else:
            return response


if __name__ == "__main__":
    print("Welcome to Footprints Preschool!")
    first_question = "May I know your child's name? 👶"
    print("\nArjun:", first_question)

    bot = FootprintsBot()

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "bye"]:
            print("Thank you for chatting! Have a great day! 🌟")
            break

        response = bot.handle_message(user_input)
        print("\nArjun:", response)

        if bot.chat_ended:
            break
