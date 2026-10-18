import os
import re
import html
import json
import base64
import sqlite3
from email.mime.text import MIMEText
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

# ---------- SETTINGS ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

MY_EMAIL = "sattarawan19@gmail.com"
MAX_STEPS = 5
LABEL_NAME = "AI-Processed"

# GitHub Actions apne aap GITHUB_ACTIONS=true set karta hai
IN_CLOUD = os.getenv("GITHUB_ACTIONS") == "true"
# DRY_RUN=true ho to email nahi bheji jayegi (sirf test)
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    google_api_key=os.getenv("GEMINI_API_KEY")
)

# ---------- DATABASE: booking slots ----------
conn = sqlite3.connect(os.path.join(BASE_DIR, "bookings.db"))
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS slots (
    day TEXT,
    time TEXT,
    booked INTEGER DEFAULT 0,
    UNIQUE(day, time)
)
""")
starting_slots = [("monday", "10am"), ("monday", "3pm"), ("wednesday", "11am")]
cursor.executemany("INSERT OR IGNORE INTO slots (day, time) VALUES (?, ?)", starting_slots)
conn.commit()

# ---------- GMAIL LOGIN ----------
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")
creds = None

token_from_env = os.getenv("GMAIL_TOKEN_JSON")
if token_from_env:
    # Cloud: token GitHub Secret se aata hai
    creds = Credentials.from_authorized_user_info(json.loads(token_from_env), SCOPES)
elif os.path.exists(TOKEN_PATH):
    # Apna computer: token file se aata hai
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif IN_CLOUD:
        raise Exception("Cloud mein Gmail token sahi nahi. GMAIL_TOKEN_JSON secret check karein.")
    else:
        flow = InstalledAppFlow.from_client_secrets_file(os.path.join(BASE_DIR, "credentials.json"), SCOPES)
        creds = flow.run_local_server(port=0)
    if not IN_CLOUD:
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

service = build("gmail", "v1", credentials=creds)

# ---------- HELPER FUNCTIONS ----------
def log(text):
    # Cloud ke logs public ho sakte hain, is liye wahan customer ki details print nahi karte
    if not IN_CLOUD:
        print(text)

def get_or_create_label(name):
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"] == name:
            return label["id"]
    new_label = service.users().labels().create(
        userId="me",
        body={"name": name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
    ).execute()
    return new_label["id"]

def mark_processed(msg_id, label_id):
    service.users().messages().modify(
        userId="me", id=msg_id, body={"addLabelIds": [label_id]}
    ).execute()

def send_reply(to_email, subject, message_text):
    message = MIMEText(message_text)
    message["to"] = to_email
    message["subject"] = "Re: " + subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw_message}).execute()

def get_customer_name(sender):
    name = sender.split("<")[0].strip().strip('"')
    if name == "":
        return "there"
    return name

def clean_snippet(text):
    text = html.unescape(text)
    signature_words = ["please do not print", "sent from my"]
    for word in signature_words:
        position = text.lower().find(word)
        if position != -1:
            text = text[:position]
    return text.strip(" “\"\n")

def clean_reply(text):
    text = re.sub(r"\[([^\]]+)\]\s*\([^)]+\)", r"\1", text)
    text = text.replace("**", "")
    return text.strip()

# ---------- TOOLS ----------
@tool
def get_price(plan: str) -> str:
    """Get the monthly price of a plan. plan can be 'basic' or 'premium'."""
    prices = {"basic": "$10/month", "premium": "$25/month (priority support, unlimited usage)"}
    return prices.get(plan.lower(), "Plan not found")

@tool
def check_slot(day: str) -> str:
    """Check which booking time slots are free on a given day, e.g. 'monday'."""
    rows = cursor.execute(
        "SELECT time FROM slots WHERE day = ? AND booked = 0", (day.lower(),)
    ).fetchall()
    if len(rows) == 0:
        return "No free slots on this day"
    return "Free slots: " + ", ".join(row[0] for row in rows)

@tool
def book_slot(day: str, time: str) -> str:
    """Book a time slot. Use ONLY after check_slot. time must be exactly as shown by check_slot, e.g. '10am'."""
    cursor.execute(
        "UPDATE slots SET booked = 1 WHERE day = ? AND time = ? AND booked = 0",
        (day.lower(), time.lower())
    )
    conn.commit()
    if cursor.rowcount == 1:
        return f"Booked successfully: {day} at {time}"
    return "This slot is not available"

tools = {"get_price": get_price, "check_slot": check_slot, "book_slot": book_slot}
llm_with_tools = llm.bind_tools(list(tools.values()))

SYSTEM_PROMPT = """You are the email assistant of Sattar Digital Services.
Rules:
- Use the tools for prices and bookings. Never guess prices or free slots.
- Only book a slot if the customer clearly asks for a booking.
- Write ONLY the email reply text: plain text, no markdown, under 100 words.
- Address the customer by name.
- Reply in the same language as the customer's email.
- If you cannot help, say our team will contact them soon.
- If the email is NOT from a real customer (password resets, security alerts, notifications, newsletters, receipts), reply with exactly one word: SKIP
- Sign off as: Sattar Digital Services Team"""

# ---------- AGENT ----------
def run_agent(email_text, customer_name, subject):
    messages = [
        SystemMessage(SYSTEM_PROMPT),
        HumanMessage(f"Customer name: {customer_name}\nSubject: {subject}\nEmail: {email_text}")
    ]
    step = 0
    while step < MAX_STEPS:
        step += 1
        ai_msg = llm_with_tools.invoke(messages)
        messages.append(ai_msg)

        if not ai_msg.tool_calls:
            return clean_reply(ai_msg.text)

        for call in ai_msg.tool_calls:
            print("   Tool:", call["name"], call["args"])
            result = tools[call["name"]].invoke(call["args"])
            print("   Nateeja:", result)
            messages.append(ToolMessage(content=result, tool_call_id=call["id"]))

    raise Exception("Agent MAX_STEPS tak pohanch gaya, jawab nahi bana")

# ---------- MAIN ----------
print("Mode:", "CLOUD" if IN_CLOUD else "LOCAL", "| DRY_RUN:", DRY_RUN)

label_id = get_or_create_label(LABEL_NAME)

results = service.users().messages().list(
    userId="me",
    q=f"in:inbox category:primary -from:me -label:{LABEL_NAME} newer_than:2d",
    maxResults=5
).execute()
messages_list = results.get("messages", [])
print("Nayi emails mili:", len(messages_list))

for message in messages_list:
    msg_id = message["id"]
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

    sender_lower = sender_email.lower()
    if MY_EMAIL in sender_lower or is_bulk or "noreply" in sender_lower or "no-reply" in sender_lower:
        print("Skip: automated ya apni email")
        if not DRY_RUN:
            mark_processed(msg_id, label_id)
        continue

    snippet = clean_snippet(msg_data.get("snippet", ""))
    customer_name = get_customer_name(sender_email)

    log(f"From: {customer_name}")
    log(f"Email Preview: {snippet}")

    try:
        reply = run_agent(snippet, customer_name, subject)
        log("Agent Reply:")
        log(reply)
        if reply.strip().upper() == "SKIP":
            print("Skip: AI ke mutabiq yeh customer ki email nahi")
            if not DRY_RUN:
                mark_processed(msg_id, label_id)
            continue
        if DRY_RUN:
            print("DRY_RUN: reply nahi bheja")
        else:
            send_reply(sender_email, subject, reply)
            mark_processed(msg_id, label_id)
            print("Reply bheja gaya")
    except Exception as e:
        print("Agent reply nahi bana saka:", e)
    print("-" * 40)

conn.close()