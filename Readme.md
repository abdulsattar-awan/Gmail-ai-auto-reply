# Gmail AI Auto-Reply

An end-to-end automation script that reads emails from a Gmail inbox, classifies them, generates a professional reply using Google's Gemini AI, and sends the reply automatically.

## Features

- Gmail Integration — Authenticates with the Gmail API to read and send emails.
- AI-Generated Replies — Uses Google's Gemini AI to draft professional responses.
- Email Categorization — Classifies emails into Booking, Pricing, Complaint, or General.
- Duplicate Prevention — Tracks processed email IDs to avoid replying twice.
- Self-Reply Protection — Skips emails sent from the user's own address.
- Error Handling — Uses try/except so the script doesn't crash on errors.

## Tech Stack

- Python 3
- Google Gmail API
- Google Generative AI (Gemini)
- OAuth 2.0

## Setup

1. Clone this repository.
2. Install dependencies: pip install google-generativeai python-dotenv google-auth-oauthlib google-api-python-client
3. Create a .env file with your Gemini API key.
4. Add your Google Cloud credentials.json file.
5. Run: python gmail_ai_reply.py

## Security Note

This repository does not include any credentials, API keys, or tokens. Sensitive files are excluded via .gitignore.

## Project Background

This project was built as a hands-on learning exercise, progressing from Python fundamentals to a fully working AI-powered email automation system.