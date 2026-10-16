# Gmail AI Auto-Reply

An end-to-end automation script that reads customer emails from Gmail, classifies them, generates a professional reply with Google's Gemini AI, and sends it automatically.

## How It Works

1. Fetches new emails from the Gmail **Primary** inbox
2. Filters out newsletters, marketing and `noreply` emails
3. Classifies each email: Booking, Pricing, Complaint, or General
4. Generates a reply with Gemini AI using real business information
5. Cleans the AI output and sends the reply
6. Saves every processed email in a SQLite database

## Features

- **Gmail Integration** — OAuth 2.0 authentication to read and send emails
- **Smart Filtering (two layers)** — Gmail search query (`in:inbox category:primary -from:me`) plus detection of `List-Unsubscribe` headers and `noreply` senders, so automated emails never get a reply
- **Prompt Engineering** — The AI uses only provided business data, addresses the customer by name, and never uses placeholders like `[Name]` or `[Price]`
- **Hallucination Protection** — If information is not available, the AI says the team will follow up instead of inventing an answer
- **Output Guardrails** — AI output is cleaned in code (markdown links and formatting removed) before sending
- **Retry Logic** — Temporary errors (503) are retried with a delay; daily quota errors (429) stop immediately
- **Duplicate Prevention** — Processed email IDs are stored in SQLite to avoid replying twice
- **Self-Reply Protection** — Skips emails sent from the user's own address
- **Flask API** — `app.py` exposes a `/generate-reply` endpoint (deployed on PythonAnywhere)

## Tech Stack

- Python 3
- Google Gmail API (OAuth 2.0)
- Google Gemini AI (`google-genai` SDK)
- SQLite
- Flask

## Setup

1. Clone this repository
2. Install dependencies: