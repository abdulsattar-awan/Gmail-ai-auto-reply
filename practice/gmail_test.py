import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

creds = None

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
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
        from googleapiclient.discovery import build

service = build("gmail", "v1", credentials=creds)
results = service.users().messages().list(userId="me", maxResults=1).execute()
messages = results.get("messages", [])

print(messages)
if messages:
    msg_id = messages[0]["id"]
    msg_data = service.users().messages().get(userId="me", id=msg_id).execute()

    print(msg_data.get("snippet", ""))