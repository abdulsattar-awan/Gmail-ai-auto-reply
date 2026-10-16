import os.path
import base64
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-3.6-flash")
creds = None
if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json.json", SCOPES)
        creds = flow.run_local_server(port=0)
    with open("token.json", "w") as token:
        token.write(creds.to_json())

service = build("gmail", "v1", credentials=creds)


def classify_email(text):
    text = text.lower()
    if "booking" in text or "book" in text:
        return "Booking Request"
    elif "pricing" in text or "price" in text:
        return "Pricing Inquiry"
    else:
        return "Unknown Category"
results = service.users().messages().list(userId="me", maxResults=1).execute()
messages = results.get("messages", [])
def send_reply(to_email, subject, reply_text):
    try:
        message = MIMEText(reply_text)
        message["to"] = to_email
        message["subject"] = "Re: " + subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        print("EMAIL SENT SUCCESSFULLY, ID:", sent["id"])
        return sent
    except Exception as e:
        print("SEND ERROR:", e)
        return None

for msg in messages:
    msg_data = service.users().messages().get(userId="me", id=msg["id"]).execute()
    headers = msg_data["payload"]["headers"]

    subject = ""
    sender_email = ""
    for header in headers:
        if header["name"] == "Subject":
            subject = header["value"]
        if header["name"] == "From":
            sender_email = header["value"]

    snippet = msg_data.get("snippet", "")
    category = classify_email(snippet)

    print("From:", sender_email)
    print("Subject:", subject)
    print("Category:", category)

    ai_response = model.generate_content(
        "Tum ek professional customer support assistant ho. Category: " + category +
        ". Is email ka professional reply likho: " + snippet
    )

    print("AI Reply:", ai_response.text)

    send_reply(sender_email, subject, ai_response.text)
 