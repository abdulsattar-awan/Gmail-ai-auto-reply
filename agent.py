import os
import sqlite3
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    google_api_key=os.getenv("GEMINI_API_KEY")
)

# ---------- DATABASE ----------
conn = sqlite3.connect("bookings.db")
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

# ---------- TOOLS ----------
@tool
def get_price(plan: str) -> str:
    """Get the monthly price of a plan. plan can be 'basic' or 'premium'."""
    prices = {"basic": "$10/month", "premium": "$25/month"}
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

# ---------- AGENT LOOP ----------
question = "If Monday has a free slot, please book the earliest one for me."
messages = [HumanMessage(question)]

MAX_STEPS = 5
step = 0

while step < MAX_STEPS:
    step += 1
    print(f"--- Round {step} ---")

    ai_msg = llm_with_tools.invoke(messages)
    messages.append(ai_msg)

    if not ai_msg.tool_calls:
        break

    for call in ai_msg.tool_calls:
        print("Tool chal raha hai:", call["name"], call["args"])
        result = tools[call["name"]].invoke(call["args"])
        print("Nateeja:", result)
        messages.append(ToolMessage(content=result, tool_call_id=call["id"]))

print()
print("AI ka aakhri jawab:")
print(ai_msg.text)
print()
print("Database:", cursor.execute("SELECT * FROM slots").fetchall())