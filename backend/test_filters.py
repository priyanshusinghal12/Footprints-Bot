#!/usr/bin/env python3
"""
Quick test for profanity and off-topic filtering
"""
from bot import FootprintsBot

def test_filters():
    bot = FootprintsBot()
    
    test_cases = [
        # Profanity tests
        ("fuck you", "Should catch profanity"),
        ("what the fuck", "Should catch profanity"),
        ("this is bullshit", "Should catch profanity"),
        ("you're an idiot", "Should catch profanity"),
        ("f u c k", "Should catch spaced profanity"),
        
        # Off-topic tests  
        ("what's the weather today", "Should reject off-topic"),
        ("tell me a joke", "Should reject off-topic"),
        ("who won the cricket match", "Should reject off-topic"),
        ("what is 2+2", "Should reject off-topic"),
        
        # Valid queries (should work)
        ("hello", "Should accept greeting"),
        ("Priyanshu", "Should accept name"),
        ("what are your fees", "Should accept Footprints query"),
        ("tell me about safety", "Should accept Footprints query"),
        ("Sector 45 Noida", "Should accept location"),
    ]
    
    print("=" * 80)
    print("TESTING PROFANITY & OFF-TOPIC FILTERS")
    print("=" * 80)
    print()
    
    for user_input, description in test_cases:
        print(f"Test: {description}")
        print(f"  Input: '{user_input}'")
        
        # Check profanity
        has_profanity = bot.contains_profanity(user_input)
        is_footprints = bot.is_footprints_related(user_input)
        
        print(f"  Profanity: {has_profanity}")
        print(f"  Footprints-related: {is_footprints}")
        
        response = bot.handle_message(user_input)
        print(f"  Response: {response[:100]}...")
        print()

if __name__ == "__main__":
    test_filters()

