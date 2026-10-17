from flask import Flask, request, jsonify
from google import genai
from dotenv import load_dotenv
import os
import re

app = Flask(__name__)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = "gemini-3.5-flash-lite"

BUSINESS_INFO = """
Business name: Sattar Digital Services
Basic package: $10/month
Premium package: $25/month (priority support, unlimited usage)
Booking link: www.sattardigital.com/book
"""

def clean_reply(text):
    text = re.sub(r"\[([^\]]+)\]\s*\([^)]+\)", r"\1", text)
    text = text.replace("**", "")
    return text.strip()

@app.route("/")
def home():
    return "Hello! Mera Flask server chal raha hai."

@app.route("/generate-reply", methods=["POST"])
def generate_reply():
    data = request.get_json()
    email_text = data.get("email_text", "").strip()

    if email_text == "":
        return jsonify({"error": "email_text khaali hai"}), 400

    prompt = f"""You are a polite customer support assistant for Sattar Digital Services.
Use ONLY this business information:
{BUSINESS_INFO}

Rules:
- Write ONLY the email reply text, nothing else. No subject line, no notes, no options.
- Never use placeholders like [Name] or [Price]
- If information is not available, say our team will contact them soon
- Keep the reply short (under 100 words)
- Write in plain text only, no markdown
- Reply in the same language as the customer's email
- Sign off as: Sattar Digital Services Team

Customer email:
{email_text}"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return jsonify({"reply": clean_reply(response.text)})

if __name__ == "__main__":
    app.run(debug=True)