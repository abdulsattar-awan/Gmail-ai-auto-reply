import re
import html
import time
import sqlite3
import os.path
import base64
from email.mime.text import MIMEText
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = "gemini-3.5-flash-lite"


conn = sqlite3.connect("emails.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS emails (
    id TEXT PRIMARY KEY,
    sender TEXT,
    subject TEXT,
    category TEXT,
    reply TEXT
)
""")
conn.commit()
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

BUSINESS_INFO = """
Business name: Sattar Digital Services
Basic package: $10/month
Premium package: $25/month (priority support, unlimited usage)
Booking link: www.sattardigital.com/book
"""

def get_category(text):
    text = text.lower()
    if "booking" in text or "book" in text:
        return "Booking"
    elif "price" in text or "pricing" in text:
        return "Pricing"
    elif "complaint" in text or "problem" in text:
        return "Complaint"
    else:
        return "General"

def get_customer_name(sender):
    name = sender.split("<")[0].strip().strip('"')
    if name == "":
        return "there"
    return name


def clean_reply(text):
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("**", "")
   
   def clean_snippet(text):
    text = html.unescape(text)
    signature_words = ["please do not print", "sent from my"]
    for word in signature_words:
        position = text.lower().find(word)
        if position != -1:
            text = text[:position]
    return text.strip(" “\"\n")
    return text.strip()



def generate_reply(email_text, customer_name, category):
    prompt = f"""You are a polite customer support assistant for Sattar Digital Services.
Use ONLY this business information:
{BUSINESS_INFO}

Rules:
- Write ONLY the email reply text, nothing else. No subject line, no notes, no options.
- Address the customer by name: {customer_name}
- Never use placeholders like [Name] or [Price]
- If information is not available, say our team will contact them soon
- Keep the reply short (under 100 words)
- Write in plain text only, no markdown, no ** or [ ]
- Reply in the same language as the customer's email
- Sign off as: Sattar Digital Services Team

Email category: {category}
Customer email:
{email_text}"""

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )
        
            
            return clean_reply(response.text)
        except Exception as e:
            print(f"Koshish {attempt + 1} nakam: {e}")
            if "429" in str(e):
                raise Exception("Aaj ka AI quota khatam ho gaya, kal dobara chalayein")
            if attempt < 2:
                time.sleep(10)

    raise Exception("AI 3 koshishon ke baad bhi jawab nahi de saka")

results = service.users().messages().list(
    userId="me",
    q="in:inbox category:primary -from:me",
    maxResults=5
).execute()
messages = results.get("messages", [])

cursor.execute("SELECT id FROM emails")
processed_ids = [row[0] for row in cursor.fetchall()]

for message in messages:
    msg_id = message["id"]
    if msg_id in processed_ids:
        continue

    msg_data = service.users().messages().get(userId="me", id=msg_id).execute()
    headers = msg_data["payload"]["headers"]

    sender_email = ""
    subject = ""
    is_bulk = False

    for header in headers:
        if header["name"] == "From":
            sender_email = header["value"]
        if header["name"] == "Subject":
            subject = header["value"]
        if header["name"].lower() == "list-unsubscribe":
            is_bulk = True

    if "sattarawan19@gmail.com" in sender_email:
        continue

    sender_lower = sender_email.lower()
    if is_bulk or "noreply" in sender_lower or "no-reply" in sender_lower:
        print("Skip (automated email):", sender_email)
        continue

    snippet = msg_data.get("snippet", "")
    snippet = clean_snippet(snippet)
    category = get_category(subject + " " + snippet)
    customer_name = get_customer_name(sender_email)

    print("From:", customer_name)
    print("Category:", category)
    print("Email Preview:", snippet)

    try:
        reply = generate_reply(snippet, customer_name, category)
        print("AI Reply:")
        print(reply)
       # send_reply(sender_email, subject, reply)
        cursor.execute("""
        INSERT INTO emails (id, sender, subject, category, reply)
        VALUES (?, ?, ?, ?, ?)
        """, (msg_id, sender_email, subject, category, reply))
        conn.commit()
    except Exception as e:
        print("AI reply generate nahi ho saka:", e)