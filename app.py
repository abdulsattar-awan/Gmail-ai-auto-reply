from flask import Flask, request, jsonify
import google.generativeai as genai
from dotenv import load_dotenv
import os

app = Flask(__name__)

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-3.6-flash")

@app.route("/")
def home():
    return "Hello! Mera Flask server chal raha hai."
@app.route("/generate-reply", methods=["POST"])
def generate_reply():
    data = request.get_json()
    email_text = data.get("email_text", "")

    response = model.generate_content(
        "Tum ek professional customer support assistant ho. Is email ka professional jawab likho: " + email_text
    )

    return jsonify({"reply": response.text})

if __name__ == "__main__":
    app.run(debug=True)