"""
Gmail API Service for extracting bank transaction emails.
Handles OAuth2 authentication and email message retrieval.
"""

import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables from .env file
load_dotenv()

# Import LLM filtering (optional - falls back gracefully)
try:
    from spendlens.services.email_extraction import filter_senders_with_llm
    LLM_FILTER_AVAILABLE = True
except ImportError:
    LLM_FILTER_AVAILABLE = False

# Gmail API scope for read-only access to emails
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def _get_last_year_date_query():
    """Generate Gmail query string for emails from last 1 year to today."""
    one_year_ago = datetime.now() - timedelta(days=365)
    # Gmail date format: YYYY/MM/DD
    after_date = one_year_ago.strftime('%Y/%m/%d')
    return f"after:{after_date}"

# Store credentials in workspace root (configurable via env var)
CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
TOKEN_FILE = os.getenv("GMAIL_TOKEN_FILE", "token.json")


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
            # Run local server on port 8080 for OAuth callback
            # Use redirect_uri_trailing_slash=False to avoid trailing slash
            creds = flow.run_local_server(
                port=8080, 
                open_browser=True,
                redirect_uri_trailing_slash=False
            )
        
        # Save token for future use
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)


# Common bank and financial institution domain patterns
BANK_DOMAINS = {
    # Indian Banks
    'hdfcbank.com', 'icicibank.com', 'sbi.co.in', 'axisbank.com', 
    'kotak.com', 'yesbank.in', 'idfcfirstbank.com', 'indusind.com',
    'bob.com', 'bankofbaroda.com', 'canarabank.com', 'unionbankofindia.com',
    'pnb.co.in', 'centralbankofindia.co.in', 'iob.in', 'ucobank.com',
    'bankofindia.co.in', 'indianbank.in', 'federalbank.co.in',
    'southindianbank.com', 'rblbank.com', 'bandhanbank.com',
    # International/Investment
    'paypal.com', 'paytm.com', 'phonepe.com', 'googlepay.com',
    'amazonpay.com', ' Razorpay.com', 'stripe.com',
    # Credit Cards
    'amex.com', 'americanexpress.com', 'mastercard.com', 'visa.com',
    # Insurance/Investment
    'licindia.in', 'maxlifeinsurance.com', 'hdfclife.com', 'iciciprulife.com',
    'mutualfund', 'amc', 'nseindia.com', 'bseindia.com', 'nsdl.co.in',
    # UPI/Wallet
    'upi', 'npci.org.in',
}

# Non-bank domains to explicitly exclude
EXCLUDED_DOMAINS = {
    'facebook.com', 'instagram.com', 'twitter.com', 'x.com', 'linkedin.com',
    'google.com', 'gmail.com', 'youtube.com', 'microsoft.com', 'apple.com',
    'amazon.com', 'flipkart.com', 'myntra.com', 'swiggy.com', 'zomato.com',
    'uber.com', 'ola.com', 'spotify.com', 'netflix.com', 'hotstar.com',
    'newsletter', 'marketing', 'noreply', 'no-reply', 'support', 'help',
    'promotions', 'offers', 'deals', 'campaign', 'mailchimp.com', 'sendgrid.net',
}

# Transaction-specific keywords in subject lines
TRANSACTION_KEYWORDS = {
    'debit', 'credit', 'withdrawal', 'deposit', 'transfer', 'payment',
    'spent', 'received', 'upi', 'neft', 'rtgs', 'imps', 'ach',
    'purchase', 'transaction', 'alert', 'notification', 'statement',
    'balance', 'mini statement', 'account activity', 'funds',
    'rs.', '₹', 'inr', 'amount', 'debited', 'credited',
}


def _is_likely_bank_sender(sender_email: str, sender_name: str = "", subject: str = "") -> bool:
    """
    Determine if a sender is likely a real bank/financial institution.
    Uses domain matching and transaction keyword analysis.
    """
    sender_lower = sender_email.lower()
    name_lower = sender_name.lower()
    subject_lower = subject.lower()
    
    # Extract domain from email
    if '@' in sender_email:
        domain = sender_email.split('@')[1].lower()
    else:
        return False
    
    # Check for excluded domains first
    for excluded in EXCLUDED_DOMAINS:
        if excluded in domain or excluded in name_lower:
            return False
    
    # Check if domain matches known bank patterns
    is_known_bank = any(bank_domain in domain for bank_domain in BANK_DOMAINS)
    
    # Check for transaction keywords in subject
    has_transaction_keywords = any(
        keyword in subject_lower for keyword in TRANSACTION_KEYWORDS
    )
    
    # Additional patterns that indicate banking emails
    banking_indicators = [
        'bank' in domain or 'bank' in name_lower,
        'credit' in domain or 'credit' in name_lower,
        'fin' in domain or 'finance' in name_lower,
        'pay' in domain and not any(x in domain for x in ['play', 'spay']),
    ]
    
    # Score the sender
    score = 0
    if is_known_bank:
        score += 3
    if has_transaction_keywords:
        score += 2
    if any(banking_indicators):
        score += 1
    
    # Require at least 3 points to be considered a bank
    # OR be a known bank domain with transaction keywords
    return score >= 3 or (is_known_bank and has_transaction_keywords)


def list_potential_banks(service):
    """
    Search for emails with transaction keywords and extract unique bank senders.
    Uses strict filtering to exclude ads, newsletters, and non-bank emails.
    Fetches last 1 year of emails by default.
    Returns list of sender email addresses that are verified banks.
    """
    date_query = _get_last_year_date_query()
    
    # Build a more specific query targeting transaction notifications
    transaction_patterns = [
        'subject:debit', 'subject:credit', 'subject:transaction',
        'subject:UPI', 'subject:payment', 'subject:spent',
        'subject:alert', 'subject:statement',
    ]
    
    # Search with multiple queries for better coverage
    all_senders = {}  # email -> {name, subjects: [], count}
    
    for pattern in transaction_patterns[:4]:  # Limit to avoid rate limits
        query = f'{pattern} {date_query}'
        
        try:
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=100
            ).execute()
            
            messages = results.get('messages', [])
            
            for msg in messages:
                try:
                    m = service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='metadata'
                    ).execute()
                    
                    headers = m.get('payload', {}).get('headers', [])
                    sender_email = None
                    sender_name = ""
                    subject = ""
                    
                    for h in headers:
                        if h['name'] == 'From':
                            sender_email = h['value']
                            # Parse "Name <email@domain.com>" format
                            if '<' in sender_email and '>' in sender_email:
                                sender_name = sender_email.split('<')[0].strip().strip('"')
                                sender_email = sender_email.split('<')[1].split('>')[0]
                        elif h['name'] == 'Subject':
                            subject = h['value']
                    
                    if sender_email:
                        if sender_email not in all_senders:
                            all_senders[sender_email] = {
                                'name': sender_name,
                                'subjects': [],
                                'count': 0
                            }
                        all_senders[sender_email]['subjects'].append(subject)
                        all_senders[sender_email]['count'] += 1
                        
                except HttpError as e:
                    print(f"Error fetching message {msg['id']}: {e}")
                    continue
                    
        except HttpError as error:
            print(f"Query error for '{pattern}': {error}")
            continue
    
    # Filter to only verified bank senders using rules-based filtering first
    rule_filtered = []
    for email, data in all_senders.items():
        # Check if sender appears in multiple transaction emails
        is_recurring = data['count'] >= 2
        
        # Check subjects for transaction patterns
        has_valid_subjects = any(
            _is_likely_bank_sender(email, data['name'], subject)
            for subject in data['subjects'][:3]  # Check first 3 subjects
        )
        
        if (is_recurring or has_valid_subjects) and _is_likely_bank_sender(email, data['name'], data['subjects'][0] if data['subjects'] else ""):
            rule_filtered.append({
                'email': email,
                'name': data['name'],
                'subjects': data['subjects'],
                'count': data['count']
            })
    
    # Further refine with LLM if available
    if LLM_FILTER_AVAILABLE and len(rule_filtered) > 0:
        print(f"🤖 Using LLM to filter {len(rule_filtered)} potential senders...")
        llm_filtered = filter_senders_with_llm(rule_filtered)
        return sorted(llm_filtered)
    
    # Fallback to rule-based only
    return sorted([s['email'] for s in rule_filtered])


def get_emails_from_sender(service, sender_email: str, max_results: int = 500, last_year_only: bool = True):
    """
    Fetch all emails from a specific sender.
    By default, fetches last 1 year of emails.
    Returns list of email IDs and snippets.
    """
    try:
        # Build query with date filter
        query = f'from:{sender_email}'
        if last_year_only:
            date_query = _get_last_year_date_query()
            query = f'{query} {date_query}'
        
        results = service.users().messages().list(
            userId='me',
            q=query,
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
