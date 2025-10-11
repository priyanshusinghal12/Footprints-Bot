from bot import FootprintsBot  # assuming your class is saved in footprints_bot.py

bot = FootprintsBot()

print("Hi! 👋 Welcome to Footprints Preschool. I’m Arjun, your assistant. May I know your child’s name? 👶")
while True:
    user_input = input("> ")
    response = bot.handle_message(user_input)
    print(response)
    if "great day" in response.lower() or "bye" in user_input.lower():
        break 