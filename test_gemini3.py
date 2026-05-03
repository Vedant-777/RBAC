import os
from dotenv import load_dotenv
load_dotenv()

from google import genai
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
try:
    response = client.models.generate_content(
        model='gemini-3.1-pro-preview',
        contents='Tell me a joke.'
    )
    print("gemini-3.1-pro-preview OK:", response.text)
except Exception as e:
    print("gemini-3.1-pro-preview Error:", e)

try:
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents='Tell me a joke.'
    )
    print("gemini-2.5-flash OK:", response.text)
except Exception as e:
    print("gemini-2.5-flash Error:", e)
