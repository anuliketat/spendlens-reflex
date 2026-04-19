"""
Gmail API Service for extracting bank transaction emails.
Handles OAuth2 authentication and email message retrieval.
"""

import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Gmail API scope for read-only access to emails
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Store credentials in workspace root
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def get_gmail_service():
    """
    Authenticate with Gmail API and return service instance.
    Uses OAuth2 flow if credentials don't exist.
    """
    creds = None
    
    # Load existing token if available
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    # If no valid credentials, perform OAuth2 flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"{CREDENTIALS_FILE} not found. "
                    "Download it from Google Cloud Console and place in workspace root."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save token for future use
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)


def list_potential_banks(service):
    """
    Search for emails with transaction keywords and extract unique senders.
    Returns list of (sender_name, sender_email) tuples.
    """
    # Query for common transaction-related keywords
    query = 'debit OR credit OR UPI OR "money transfer" OR investment OR "spent on" OR transaction'
    
    try:
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=100
        ).execute()
        
        messages = results.get('messages', [])
        senders = set()
        
        for msg in messages:
            try:
                m = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata'
                ).execute()
                
                headers = m.get('payload', {}).get('headers', [])
                for h in headers:
                    if h['name'] == 'From':
                        senders.add(h['value'])
                        break
            except HttpError as e:
                print(f"Error fetching message {msg['id']}: {e}")
                continue
        
        return list(senders)
    
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


def get_emails_from_sender(service, sender_email: str, max_results: int = 50):
    """
    Fetch all emails from a specific sender.
    Returns list of email IDs and snippets.
    """
    try:
        results = service.users().messages().list(
            userId='me',
            q=f'from:{sender_email}',
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        email_data = []
        
        for msg in messages:
            try:
                m = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()
                
                headers = m.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                
                # Get email body (prefer plain text)
                body = _get_email_body(m)
                
                email_data.append({
                    'id': msg['id'],
                    'sender': sender_email,
                    'subject': subject,
                    'date': date,
                    'snippet': m['snippet'],
                    'body': body
                })
            except HttpError as e:
                print(f"Error fetching email {msg['id']}: {e}")
                continue
        
        return email_data
    
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


def _get_email_body(message):
    """
    Extract email body from message payload.
    Handles both plain text and HTML parts.
    """
    try:
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        import base64
                        return base64.urlsafe_b64decode(data).decode('utf-8')
        else:
            data = message['payload']['body'].get('data', '')
            if data:
                import base64
                return base64.urlsafe_b64decode(data).decode('utf-8')
    except Exception as e:
        print(f"Error extracting body: {e}")
    
    return message.get('snippet', '')
