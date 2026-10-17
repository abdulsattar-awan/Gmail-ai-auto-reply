import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    google_api_key=os.getenv("GEMINI_API_KEY")
)

@tool
def get_price(plan: str) -> str:
    """Get the monthly price of a plan. plan can be 'basic' or 'premium'."""
    prices = {"basic": "$10/month", "premium": "$25/month"}
    return prices.get(plan.lower(), "Plan not found")

llm_with_tools = llm.bind_tools([get_price])

response = llm_with_tools.invoke("Hello, how are you?")
print("AI ka faisla:", response.tool_calls)