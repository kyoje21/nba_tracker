import google.generativeai as genai

# Setup
genai.configure(api_key="YOUR_GOOGLE_API_KEY")
model = genai.GenerativeModel('gemini-1.5-flash')

# The Test
response = model.generate_content("Rate the sentiment of this NBA fan comment from -1 to 1: 'Pistons basketball is painful right now.'")

print(f"Sentiment Score: {response.text.strip()}")
