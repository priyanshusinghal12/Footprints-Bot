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
        self.name_attempts = 0

        self.PROGRAMS = [
            ("pre school", "Pre-School"),
            ("preschool", "Pre-School"),
            ("day care", "Full Day Care"),
            ("full day care", "Full Day Care"),
            ("after school", "After School"),
            ("afterschool", "After School"),
        ]

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

    def is_footprints_related(self, user_input):
        """Check if the user input is related to Footprints or general queries we should handle."""
        user_lower = user_input.lower()

        # --- REFINED PROFANITY AND UNRELATED KEYWORD CHECK ---
        # Using regex for more robust matching of common profanities/unrelated terms,
        # including potential typos or variations.
        profane_patterns = [
            r'\bf+u+c+k+\b', # fuck, fuuck, fuk, etc.
            r'\bs+h+i+t+\b', # shit, shittt, etc.
            r'\bb+i+t+c+h+\b', # bitch, bittch, etc.
            r'\ba+s+s+h+o+l+e+\b', # asshole, etc.
            r'\bc+u+n+t+\b', # cunt
            r'\bd+a+m+n+\b', # damn
            r'\bl+m+a+o+\b', # lmao
            r'\bl+o+l+\b',   # lol
            r'\bw+t+f+\b',   # wtf
            r'\bur\b',      # ur
            r'\bu\b',       # u
            r'\by+ +r+ +u+\b', # y r u
            r'\br+ +u+\b',   # r u
            r'\bwho +are +you+\b', # who are you
            r'\bwhat +are +you+\b', # what are you
            r'\bn+i+g+g+a+\b', # nigga (added this)
            r'\bn+i+g+g+e+r+\b', # nigger (added this)
            r'\bd+i+c+k+\b', # dick (added this)
            r'\bp+u+s+s+y+\b', # pussy (added this)
            r'\bc+o+c+k+\b', # cock (added this)
            r'\bf+a+g+\b', # fag (added this)
            r'\bs+l+u+t+\b', # slut (added this)
            r'\bw+h+o+r+e+\b', # whore (added this)
            r'\bc+r+a+p+\b', # crap (added this, can be mild but better to filter)
            r'\bd+o+u+c+h+e+\b', # douche (added this)
            r'\bj+e+r+k+\b', # jerk (added this)
            r'\bi+d+i+o+t+\b', # idiot (added this)
            r'\bm+o+r+o+n+\b', # moron (added this)
            r'\bs+t+u+p+i+d+\b', # stupid (added this)
            r'\bw+e+i+r+d+\b', # weird (added this, depending on context it can be unrelated)
            r'\bc+r+a+z+y+\b', # crazy (added this, same as weird)
            r'\bg+a+y+\b', # gay (added this, though context is key, safer to filter if not expected)
            r'\bk+i+l+l+\b', # kill (added this)
            r'\bd+i+e+\b', # die (added this)
        ]

        for pattern in profane_patterns:
            if re.search(pattern, user_lower):
                return False # Immediately classify as unrelated if profanity/unrelated detected
        # --- END REFINED PROFANITY CHECK ---

        # If we're in the middle of a conversation flow, be more lenient for expected replies
        # This allows users to say "yes" or provide simple answers even if they aren't "keywords"
        if self.step in ["program", "city", "locality", "schedule"]:
            return True
            
        footprints_keywords = [
            'footprints', 'preschool', 'pre-school', 'daycare', 'day care', 'after school', 'afterschool',
            'admission', 'enroll', 'fee', 'curriculum', 'safety', 'cctv', 'center', 'centre', 'programme', 'program',
            'child', 'kid', 'age', 'visit', 'schedule', 'meal', 'teacher', 'highscope', 'city', 'locality',
            'refund', 'pause', 'app', 'payment', 'sector', 'colony', 'nagar', 'vihar', 'area', 'block'
        ]
        
        # Also check if it's a valid response to our questions (names, ages, yes/no, etc.)
        simple_responses = ['yes', 'no', 'ok', 'sure', 'maybe', 'thanks', 'thank you', 'bye', 'hello', 'hi', 
                            'skip', 'continue', 'next', 'move on', 'later', 'fine', 'alright']
        
        # Check if it's likely a name (single word, capitalized, common name patterns)
        # This needs to be lenient because "name" is the first step.
        if self.step == "name" and len(user_input.split()) <= 2 and user_input.strip().replace(' ', '').replace('-', '').isalpha():
            return True
            
        # Check if it contains numbers (could be sector, age, etc.)
        if any(char.isdigit() for char in user_input):
            return True
            
        # Check if it contains any Footprints-related keywords
        if any(keyword in user_lower for keyword in footprints_keywords + simple_responses):
            return True
            
        # Check if it's likely an age, city, or program (even if not explicitly keywords)
        if any(word in user_lower for word in ['year', 'old', 'months', 'delhi', 'noida', 'gurgaon', 'lucknow', 
                                                'mumbai', 'bangalore', 'pune', 'hyderabad', 'chennai']):
            return True
            
        # Check for common area/locality patterns
        locality_patterns = ['sector', 'phase', 'block', 'extension', 'market', 'nagar', 'colony', 'vihar', 'marg']
        if any(pattern in user_lower for pattern in locality_patterns):
            return True
            
        # If no positive match after initial profanity check, then it's not related
        return False

    def gpt_intent_prompt(self, step, user_input, collected):
        return f"""
You are a helpful assistant for Footprints Preschool admissions. Your job is to extract the required field for the current step, classify the intent, and normalize user input. Be flexible and human-like in your interpretation.

Current step: {step}
User input: "{user_input}"
Collected so far: {collected}

IMPORTANT:
1. When we're asking for a specific field (name, program, city, locality), prioritize recognizing direct answers to that field over FAQ classification. Only classify as FAQ if the user is clearly asking a question with question words or phrases like "what is", "tell me about", "how much", etc.
2. **ALWAYS extract ALL known relevant fields (name, program, city, locality) if they are present in the user's input, regardless of the current step or primary intent. This allows users to provide information for future steps early.**
3. For name: Recognize if the input is a likely child's name. Must be a real, proper name (not random letters, gibberish, or casual words like "ay o", "hwy", etc.). If user explicitly refuses/says no/skip, classify as "skip_field". If input is unclear/ambiguous (like "ok", "sure", "fine") or not a real name, classify as "clarify"
4. For program: Classify as one of Pre-School, Full Day Care, After School (normalize typos/variants). If user refuses/skips, classify as "skip_field". IMPORTANT: "full day care", "daycare", "preschool", "after school" should be classified as provide_program, NOT as FAQ.
5. For city/locality: Normalize and expand abbreviations (e.g., "nfc" → "New Friends Colony"). City cannot be skipped (it's essential). If user wants to change city, classify as "provide_city".
   - Example: "gurugram" should be normalized to "Gurgaon".
   - Example: "sohna road gurugram" should extract city "Gurgaon" and locality "Sohna Road".
   - Example: "I want center near sector 18 noida" should extract city "Noida" and locality "Sector 18".
- If user asks a question (FAQ), recognize and extract the question - but only if they're clearly asking with question words
- If user wants to change city/locality, extract new values
- If user provides multiple fields, extract all
- Be flexible - if user wants to skip a field or move to next topic, allow it (except city)
- If user says goodbye/end conversation, classify as "end_conversation"

Respond ONLY in JSON with keys for each field relevant to the step, plus "intent".
"""
    # The rest of the class methods (gpt_response_prompt, gpt_faq_prompt, etc., and handle_message)
    # remain exactly as provided in your last working code.
    # I am omitting them here for brevity to focus on the `is_footprints_related` change.

    def gpt_response_prompt(self, intent, step, user_input, collected, context=""):
        """Generate dynamic responses based on intent and context"""
        child_name = collected.get("name", "your child")
        
        step_descriptions = {
            "name": "child's name to personalize our conversation",
            "program": "which program you're interested in (Pre-School, Full Day Care, or After School)",
            "city": "which city you're looking for a center in",
            "locality": f"which locality in {collected.get('city', 'the city')}",
            "schedule": "if you'd like to schedule a visit"
        }
        
        current_field = step_descriptions.get(step, "the information")
        
        if intent == "skip_field":
            if step == "city":
                return f"""
Generate a brief, friendly response that explains city is essential to find the right center. Ask which city they're looking in. Keep it under 15 words and conversational.
"""
            else:
                return f"""
Generate a brief, friendly response that:
1. Accepts their preference to skip sharing {current_field}
2. Briefly mentions it would help personalize our chat
3. Asks if they'd like to share it or skip to the next step
4. Keep it under 25 words, conversational and warm (not formal)
5. End with something like "or shall we move on?"

Context: We're asking for {current_field}
"""
        
        elif intent == "clarify":
            # Modified prompt for clarify
            return f"""
Generate a brief, friendly response that:
1. Says "Sorry, I didn't understand" or similar.
2. Clearly re-asks for what you're looking for: {current_field}
3. Offers the option to skip if they prefer (except for city).
4. Keep it concise, under 20 words, and helpful.

Context: User said "{user_input}" when we asked for {current_field}
"""
        
        elif intent == "end_conversation":
            return f"""
Generate a warm, brief goodbye message that:
1. Thanks them for their time
2. Invites them back for Footprints questions
3. Keep it under 20 words and friendly

Context: User wants to end conversation
"""
        
        elif intent == "invalid":
            # Modified prompt for invalid
            return f"""
Generate a brief, helpful response that:
1. Says "Sorry, I didn't understand" or similar.
2. Politely asks for {current_field}
3. Gives a quick example if helpful.
4. Offers the option to skip (except for city).
5. Keep it concise, under 20 words, and patient.

Context: We need {current_field} but user response was unclear
"""
        
        return f"Generate an appropriate response for intent '{intent}' in step '{step}'"

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

    def generate_dynamic_response(self, intent, step, user_input, collected, context=""):
        """Generate dynamic response using GPT"""
        prompt = self.gpt_response_prompt(intent, step, user_input, collected, context)
        return self.ask_gpt(prompt, temperature=0.7)

    def normalize_program(self, text):
        text = text.lower().replace("-", " ").replace("_", " ")
        for key, val in self.PROGRAMS:
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
                extra = ""
                if self.fact_injected < 2 and self.step == "schedule":  # Only add facts after center recommendation
                    extra = f"\nBy the way, did you know? {self.random_fact()}"
                    self.fact_injected += 1
                
                # Only show the "anything else" question after center has been recommended
                ending = ""
                if self.step == "schedule":
                    ending = "\n\nIs there anything else I can help you with — like safety, curriculum, meals, or fees?"
                
                return f"{response}{extra}{ending}"
        
        ending = ""
        if self.step == "schedule":
            ending = "\nIs there anything else I can help you with — like safety, curriculum, meals, or fees?"
        
        return (
            "I'm not sure about that topic, but someone from our team will reach out to assist you shortly."
            + ending
        )

    def get_next_question(self):
        """Get the next logical question to ask based on what we have"""
        child_name = self.collected.get("name", "your child")
        
        # If program is not collected AND we are at the program step (or just started)
        if "name" not in self.collected and self.name_attempts < 2:
            return "May I know your child’s name? 👶" # Re-ask if not skipped twice
        elif self.collected.get("program") is None: # Program can be None if skipped
            return (
                f"Which program are you considering for {child_name}? We offer:\n"
                "- Pre-School (9:00 AM to 12:30 PM)\n"
                "- Full Day Care (Pre-School + Daycare, 9:00 AM to 6:30 PM)\n"
                "- After School (3:30 PM to 6:30 PM)\n"
                "All programs operate Monday to Friday at every center. 📚"
            )
        elif self.collected.get("city") is None:
            return "Which city are you looking for a center in?"
        elif self.collected.get("locality") is None:
            return f"Which locality in {self.collected['city']}?"
        else:
            return None

    def handle_message(self, user_input):
        user_input = user_input.strip()
        child_name = self.collected.get("name", "your child")

        # --- CRITICAL FIX: Check Footprints relevance FIRST and return immediately if unrelated ---
        if not self.is_footprints_related(user_input):
            return "I'm here to assist only with Footprints-related queries. 😊"
        # --- END CRITICAL FIX ---

        # If it's Footprints related, then proceed with GPT intent classification
        prompt = self.gpt_intent_prompt(self.step, user_input, self.collected)
        gpt_response = self.ask_gpt(prompt)
        print("DEBUG GPT RESPONSE:", gpt_response)
        try:
            result = json.loads(self.extract_json_from_response(gpt_response))
        except Exception:
            result = {"intent": "invalid"}

        intent = result.get("intent", "invalid")

        # Handle Global Intents (FAQ, End Conversation)
        if intent == "faq":
            topic = result.get("topic", "")
            return self.answer_faq(topic)

        if intent == "end_conversation":
            return self.generate_dynamic_response("end_conversation", self.step, user_input, self.collected)

        # Extract all provided fields immediately, regardless of current step
        if "name" in result and result["name"] and self.collected.get("name") is None:
            self.collected["name"] = result["name"]
        if "program" in result and result["program"] and self.collected.get("program") is None:
            self.collected["program"] = self.normalize_program(result["program"])
        if "city" in result and result["city"] and self.collected.get("city") is None:
            self.collected["city"] = result["city"]
        if "locality" in result and result["locality"] and self.collected.get("locality") is None:
            # If locality given but city missing in collected, it means GPT detected locality but not explicit city.
            # We'll rely on the self.step logic below to ensure city is asked if still missing.
            pass # Keep this for now, will be handled by step progression
            self.collected["locality"] = result["locality"]

        # Determine the logical next step based on ALL collected data
        # This order is crucial for prioritizing which piece of info to get next
        if self.collected.get("city") and self.collected.get("locality"):
            self.step = "recommend_center"
        elif self.collected.get("city"):
            self.step = "locality"
        elif self.collected.get("program") is not None: # Program is either provided or explicitly set to None (skipped)
            self.step = "city"
        elif self.collected.get("name") is not None or self.name_attempts >= 2: # Name is provided or skipped
            self.step = "program"
        else: # Default to name if nothing is collected and name wasn't skipped twice
            self.step = "name"
        

        # Handle specific step logic based on the *newly determined* self.step

        # Handle name step
        if self.step == "name":
            if intent == "skip_field":
                self.name_attempts += 1
                if self.name_attempts >= 2:
                    self.collected["name"] = None # Mark as explicitly skipped
                    self.step = "program" # Advance after exhausting name attempts
                    return f"That's perfectly fine! We can continue without the name. 😊\n{self.get_next_question()}"
                else:
                    return self.generate_dynamic_response("skip_field", "name", user_input, self.collected)
            elif intent in ["clarify", "invalid"]:
                self.name_attempts += 1
                if self.name_attempts >= 2:
                    self.collected["name"] = None
                    self.step = "program"
                    return f"No worries! We can continue without the name. 😊\n{self.get_next_question()}"
                else:
                    return self.generate_dynamic_response(intent, "name", user_input, self.collected)
            # If name was provided by user_input (caught by global extraction) or already collected
            elif self.collected.get("name"): 
                return f"Thanks {self.collected['name']}! {self.get_next_question() or ''}"
            # Fallback if input was valid but didn't match expected name intent (should be rare)
            return self.get_next_question()

        # Handle program step
        elif self.step == "program":
            if intent == "skip_field":
                self.collected["program"] = None # Mark as skipped
                self.step = "city" # Move to city
                return f"No problem! We can discuss programs later. 😊\n{self.get_next_question()}"
            # If program was provided by user_input (caught by global extraction) or already collected
            elif self.collected.get("program"): 
                return self.get_next_question() or f"Got it! Which city are you looking for a center in?"
            elif intent in ["clarify", "invalid"]:
                return self.generate_dynamic_response(intent, "program", user_input, self.collected)
            return self.get_next_question()

        # Handle city step (MANDATORY)
        elif self.step == "city":
            if intent == "skip_field" or intent in ["clarify", "invalid"]:
                # City cannot be skipped or unclear
                return "Sorry, I can't proceed without knowing the city you're interested in. Which city are you looking for a center in?"
            # If city was provided by user_input (caught by global extraction) or already collected
            elif self.collected.get("city"):
                city = self.collected["city"]
                city_centers = [c for c in self.CENTERS if c["city"].lower() == city.lower()]
                if not city_centers:
                    # If city is valid but no centers, inform user and keep step at city
                    self.collected.pop("city", None) # Clear invalid city so it can be asked again
                    self.step = "city" 
                    return f"Sorry, we don't have any centers in or near {city}.\nTry a different city like Noida, Delhi, or Lucknow?"
                return self.get_next_question() or "" # Will ask for locality if needed
            return self.get_next_question() # Should only be reached if city is still missing after extraction

        # Handle locality step
        elif self.step == "locality":
            if intent == "skip_field":
                # If locality is skipped, try to find a general center in the city
                center = self.find_center(self.collected["city"], self.collected["city"]) # Use city name as a broad locality hint
                if center:
                    self.step = "schedule" # Move to scheduling if center found
                    reply = f"No problem! Let me find a center in {self.collected['city']} for you.\n"
                    reply += f"The nearest Footprints center is:\n{self.print_center(center)}"
                    if self.fact_injected < 1:
                        reply += f"\n\nBy the way, did you know? {self.random_fact()}"
                        self.fact_injected += 1
                    reply += "\nWould you like to schedule a visit?"
                    return reply
                else:
                    return f"I need to know which area in {self.collected['city']} you're looking for to find the best center for you."
            # If locality was provided by user_input (caught by global extraction) or already collected
            elif self.collected.get("locality"): 
                self.step = "recommend_center" # Move to recommendation
                # Re-call handle_message to immediately process the recommend_center block
                return self.handle_message(user_input) 
            elif intent in ["clarify", "invalid"]:
                return self.generate_dynamic_response(intent, "locality", user_input, self.collected)
            return self.get_next_question()

        # Handle recommend center step
        elif self.step == "recommend_center":
            # Ensure we have city and locality before recommending (redundant check, but safe)
            if not self.collected.get("city"): # or not self.collected.get("locality"): (locality can be None if skipped)
                self.step = "city" # Go back to ensure city is there
                return self.get_next_question()
            
            # Use collected locality, or default to city if locality was skipped/not provided initially
            locality_for_search = self.collected.get("locality", self.collected["city"])
            center = self.find_center(self.collected["city"], locality_for_search)
            
            if not center:
                # If no center found even with city/locality, go back to ask for better locality
                self.collected.pop("locality", None) # Clear locality to re-ask
                self.step = "locality" 
                return f"Sorry, no centers found in {self.collected['city']} near {locality_for_search}. Can you provide a more specific locality or try a different one?"
            
            self.step = "schedule"
            reply = f"Great! The nearest Footprints center is:\n{self.print_center(center)}"
            if self.fact_injected < 1:
                reply += f"\n\nBy the way, did you know? {self.random_fact()}"
                self.fact_injected += 1
            reply += "\nWould you like to schedule a visit, or change city/locality?"
            return reply

        # Handle scheduling (final step)
        elif self.step == "schedule":
            if intent in ["schedule_visit", "yes"]:
                reply = (
                    "Your visit is scheduled! You can visit anytime Monday to Friday, 9:00 AM to 6:30 PM.\n"
                    "Is there anything else I can help you with — like safety, curriculum, meals, or fees?"
                )
                if self.fact_injected < 2:
                    reply += f"\nBy the way, did you know? {self.random_fact()}"
                    self.fact_injected += 1
                return reply
            else:
                # If city/locality were implicitly provided (e.g., changing mind about location)
                if "city" in result or "locality" in result:
                    self.step = "recommend_center" # Re-evaluate recommendation based on new info
                    return self.handle_message(user_input) # Re-process
                
                return "Would you like to schedule a visit, or change city/locality?"


        # Default fallback (should ideally not be reached if flow is well-defined)
        return self.get_next_question() if self.get_next_question() else "How else can I help you with Footprints?"


# Constants (unchanged)
FOOTPRINTS_FACTS = [
    "Footprints was founded by an IIT Delhi alumnus and has 170+ centers across India.",
    "90% of brain development happens by age 6, so early years matter most.",
    "We use the US-based HighScope curriculum, proven to encourage children to explore and learn on their own.",
    "We offer live CCTV feeds so you can watch your child anytime.",
    "All our staff (except guards) are women, with strict background checks and regular health checkups.",
    "We provide healthy, nutritious meals and do not serve junk food or processed snacks.",
    "Parents can pause services, request refunds, and move centers via our app.",
    "If you're not satisfied, you can request a refund for a day's childcare fees.",
]

FAQ_ANSWERS = {
    "age range": "We welcome little ones aged 12 months to 8 years — ensuring age-appropriate care and learning at every stage.",
    "operating hours": "Our centers are open Monday to Friday, from 9:00 AM to 6:30 PM. Some branches even offer early drop-offs or late pick-ups for added flexibility.",
    "curriculum": "We follow the US-based HighScope Curriculum — a research-backed approach that encourages children to explore, experiment, and learn through engaging, hands-on activities.",
    "teacher student ratio": "To give each child the attention they deserve, we maintain a low teacher-to-student ratio of 1:10.",
    "meals": "Yes! We provide healthy, freshly prepared meals and snacks — and we're happy to accommodate dietary preferences or restrictions.",
    "safety": "Safety is our top priority. Our centers feature soft flooring, rounded edges, live CCTV access, and are staffed entirely by trained women professionals (excluding security).",
    "cctv": "Absolutely — parents can watch their child live through our secure CCTV feed via the Footprints app, anytime during operating hours.",
    "payments": "We keep things flexible — parents can manage payments, pause services, or even request refunds directly through our app.",
    "development": "We focus on holistic development — helping children grow socially, emotionally, and cognitively through structured play, problem-solving, and interaction.",
    "updates": "Yes, you'll receive regular updates throughout the day — from what your child ate to nap times, activities, and more — all via the Footprints app.",
    "fee structure": "Here's a quick breakdown:\n• One-Time Charges: Admission Fee ₹16,000, Registration ₹7,000, Welcome Kit ₹7,500\n• Monthly Fee: Pre School ₹8,999, Daycare ₹15,999, After School ₹7,999.",
    "fee": "Sure! Here's the fee structure:\nOne-Time Charges:\n- Admission Fee: ₹16,000\n- Registration: ₹7,000\n- Welcome Kit: ₹7,500\nMonthly Fees:\n- Pre School: ₹8,999\n- Daycare: ₹15,999\n- After School: ₹7,999.",
    "refund": "We believe in complete satisfaction — if you're ever unhappy, you can request a refund for that day's childcare.",
    "pause": "Absolutely — we understand plans can change. You can pause services anytime by contacting your center or through our app.",
    "enroll": "Getting started is easy! Just fill out our admission form online or drop by your nearest Footprints center.",
    "sibling discount": "Yes, we offer sibling benefits! You can ask your local center for the latest details and offers.",
}