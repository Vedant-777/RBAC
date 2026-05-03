import os
from dotenv import load_dotenv
load_dotenv()

from google import genai
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
try:
    response = client.models.generate_content(
        model='gemini-1.5-flash-8b',
        contents='Tell me a joke.'
    )
    print("gemini-1.5-flash-8b OK:", response.text)
except Exception as e:
    print("gemini-1.5-flash-8b Error:", e)

try:
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents='Tell me a joke.'
    )
    print("gemini-1.5-flash OK:", response.text)
except Exception as e:
    print("gemini-1.5-flash Error:", e)

try:
    response = client.models.generate_content(
        model='gemini-2.0-flash-exp',
        contents='Tell me a joke.'
    )
    print("gemini-2.0-flash-exp OK:", response.text)
except Exception as e:
    print("gemini-2.0-flash-exp Error:", e)
