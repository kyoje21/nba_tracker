import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ No API key found in .env")
    exit(1)

genai.configure(api_key=api_key)

# Test each model
models_to_test = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash-lite",
    "gemini-1.5-flash",
]

for model_name in models_to_test:
    try:
        print(f"\n🔍 Testing {model_name}...")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("What is 2+2? Reply with ONLY a number.")
        print(f"   ✅ {model_name} WORKS!")
        print(f"   Response: {response.text[:50]}")
        break  # Stop on first success
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            print(f"   ❌ {model_name} - Not found (404)")
        elif "permission" in error_msg.lower():
            print(f"   ❌ {model_name} - Permission denied")
        else:
            print(f"   ❌ {model_name} - {error_msg[:60]}")

print("\n" + "="*50)
print("Test complete. Use the WORKING model in app.py")
