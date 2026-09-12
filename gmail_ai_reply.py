import os.path
import base64
from email.mime.text import MIMEText
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-3.6-flash")

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
creds = None

if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)

    with open("token.json", "w") as token:
        token.write(creds.to_json())

service = build("gmail", "v1", credentials=creds)

def send_reply(to_email, subject, message_text):
            
    message = MIMEText(message_text)
    message["to"] = to_email
    message["subject"] = "Re: " + subject

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    send_body = {"raw": raw_message}
    service.users().messages().send(userId="me", body=send_body).execute()
    print("Reply bheja gaya:", to_email)

results = service.users().messages().list(userId="me", maxResults=5).execute()
messages = results.get("messages", [])
processed_ids = []

if os.path.exists("processed_ids.txt"):
    with open("processed_ids.txt", "r") as f:
        processed_ids = f.read().splitlines()
for message in messages:
    msg_id = message["id"]
    if msg_id in processed_ids:
        continue
    msg_data = service.users().messages().get(userId="me", id=msg_id).execute()

    headers = msg_data["payload"]["headers"]
    sender_email = ""
    subject = ""

    for header in headers:
        if header["name"] == "From":
            sender_email = header["value"]
        if header["name"] == "Subject":
            subject = header["value"]
    if "sattarawan19@gmail.com" in sender_email:
        continue

    snippet = msg_data.get("snippet", "")
    if "booking" in snippet.lower():
        category = "Booking"
    elif "price" in snippet.lower() or "pricing" in snippet.lower():
        category = "Pricing"
    elif "complaint" in snippet.lower() or "problem" in snippet.lower():
        category = "Complaint"
    else:
        category = "General"
    print("Email Preview:", snippet)

    try:
        response = model.generate_content(
            "Tum ek professional customer support assistant ho. Category: " + category + ". Is email ka professional jawab likho: " + snippet
        )
        print("AI Reply:")
        print(response.text)
        send_reply(sender_email, subject, response.text)
        with open("processed_ids.txt", "a") as f:
            f.write(msg_id + "\n")
    except Exception as e:
        print("AI reply generate nahi ho saka:", e)