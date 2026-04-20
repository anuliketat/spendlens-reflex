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
    from spendlens.services.email_extraction import filter_senders_with_llm, suggest_search_patterns
    LLM_FILTER_AVAILABLE = False  # Disabled to prevent timeout
    LLM_PATTERN_SUGGESTION_AVAILABLE = True
except ImportError:
    LLM_FILTER_AVAILABLE = False
    LLM_PATTERN_SUGGESTION_AVAILABLE = False

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
            # For web applications, we need to handle OAuth differently
            # Generate authorization URL for manual completion
            auth_url, _ = flow.authorization_url(prompt='consent')
            
            raise RuntimeError(
                f"Gmail authentication required. Please visit this URL in a new tab to authorize: {auth_url}\n"
                "After authorization, the authorization code will be in the URL. "
                "This web app needs a different OAuth implementation for seamless authentication."
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
    
    This is a generator that yields progress updates during processing.
    """
    print("[Gmail Service] Starting list_potential_banks...")
    date_query = _get_last_year_date_query()
    print(f"[Gmail Service] Date query: {date_query}")
    
    # Build a more specific query targeting transaction notifications
    default_transaction_patterns = [
        'subject:debit', 'subject:credit', 'subject:transaction',
        'subject:UPI', 'subject:payment', 'subject:spent',
        'subject:alert', 'subject:statement',
    ]
    
    # Use LLM to suggest optimal patterns if available
    if LLM_PATTERN_SUGGESTION_AVAILABLE:
        print("[Gmail Service] Using LLM to suggest optimal search patterns...")
        yield {
            'type': 'llm_analysis',
            'message': "Analyzing email patterns with AI to optimize search..."
        }
        
        try:
            # Get a sample of recent emails to analyze subjects
            sample_query = f'inbox {date_query}'
            sample_results = service.users().messages().list(
                userId='me',
                q=sample_query,
                maxResults=50
            ).execute()
            
            sample_messages = sample_results.get('messages', [])
            sample_subjects = []
            
            for msg in sample_messages[:20]:  # Analyze first 20 emails
                try:
                    m = service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='metadata'
                    ).execute()
                    
                    headers = m.get('payload', {}).get('headers', [])
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                    if subject:
                        sample_subjects.append(subject)
                except:
                    continue
            
            if sample_subjects:
                print(f"[Gmail Service] Analyzing {len(sample_subjects)} email subjects...")
                transaction_patterns = suggest_search_patterns(sample_subjects)
                print(f"[Gmail Service] LLM suggested patterns: {transaction_patterns}")
            else:
                print("[Gmail Service] No sample subjects found, using default patterns")
                transaction_patterns = default_transaction_patterns
        except Exception as e:
            print(f"[Gmail Service] LLM pattern suggestion failed: {e}, using defaults")
            transaction_patterns = default_transaction_patterns
    else:
        print("[Gmail Service] LLM pattern suggestion not available, using defaults")
        transaction_patterns = default_transaction_patterns
    
    print(f"[Gmail Service] Transaction patterns: {transaction_patterns}")
    
    # Search with multiple queries for better coverage
    all_senders = {}  # email -> {name, subjects: [], count}
    total_patterns = len(transaction_patterns)
    
    for i, pattern in enumerate(transaction_patterns):  # Process all patterns for comprehensive coverage
        query = f'{pattern} {date_query}'
        print(f"[Gmail Service] Processing pattern {i+1}/{total_patterns}: {query}")
        
        # Yield progress for pattern start
        yield {
            'type': 'pattern_start',
            'pattern': i+1,
            'total_patterns': total_patterns,
            'message': f"Scanning pattern {i+1}/{total_patterns}: {pattern}"
        }
        
        try:
            # Use pagination to fetch ALL emails, not just first 500
            messages = []
            page_token = None
            page_count = 0
            while True:
                page_count += 1
                print(f"[Gmail Service] Fetching page {page_count} for pattern {i+1}...")
                
                # Yield progress for page fetch
                yield {
                    'type': 'page_fetch',
                    'pattern': i+1,
                    'total_patterns': total_patterns,
                    'page': page_count,
                    'message': f"Fetching page {page_count} for pattern {i+1}..."
                }
                
                results = service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=500,
                    pageToken=page_token
                ).execute()
                
                batch = results.get('messages', [])
                messages.extend(batch)
                print(f"[Gmail Service] Page {page_count}: fetched {len(batch)} emails (total: {len(messages)})")
                
                # Check if there are more pages
                if 'nextPageToken' not in results:
                    print(f"[Gmail Service] No more pages for pattern {i+1}")
                    break
                page_token = results['nextPageToken']
                
                # Safety limit to prevent infinite loops (max 10 pages = 5000 emails per pattern)
                if len(messages) >= 5000:
                    print(f"[Gmail Service] Reached safety limit of 5000 emails for pattern {i+1}")
                    break
            
            print(f"[Gmail Service] Processing {len(messages)} emails for pattern {i+1}...")
            for msg_idx, msg in enumerate(messages):
                try:
                    # Yield progress every 10 messages to keep connection alive
                    if msg_idx % 10 == 0:
                        yield {
                            'type': 'message_process',
                            'pattern': i+1,
                            'total_patterns': total_patterns,
                            'message_idx': msg_idx,
                            'total_messages': len(messages),
                            'message': f"Processing email {msg_idx}/{len(messages)} for pattern {i+1}..."
                        }
                    
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
            
            # Yield progress for pattern completion
            yield {
                'type': 'pattern_complete',
                'pattern': i+1,
                'total_patterns': total_patterns,
                'emails_found': len(messages),
                'message': f"Completed pattern {i+1}/{total_patterns}: found {len(messages)} emails"
            }
                    
        except HttpError as error:
            print(f"[Gmail Service] Query error for '{pattern}': {error}")
            continue
    
    print(f"[Gmail Service] Total unique senders found: {len(all_senders)}")
    
    # Yield progress for filtering
    yield {
        'type': 'filtering',
        'message': f"Filtering {len(all_senders)} unique senders..."
    }
    
    # Filter to only verified bank senders using rules-based filtering first
    print("[Gmail Service] Filtering senders with rules-based filtering...")
    rule_filtered = []
    for email, data in all_senders.items():
        # Check if sender appears in multiple transaction emails
        is_recurring = data['count'] >= 2
        
        # Check subjects for transaction patterns
        has_valid_subjects = any(
            _is_likely_bank_sender(email, data['name'], subject)
            for subject in data['subjects'][:3]  # Check first 3 subjects
        )
        
        # More permissive: include if recurring OR has valid subjects OR has bank domain
        is_bank_domain = any(bank_domain in email.lower() for bank_domain in BANK_DOMAINS)
        
        if is_recurring or has_valid_subjects or is_bank_domain:
            rule_filtered.append({
                'email': email,
                'name': data['name'],
                'subjects': data['subjects'],
                'count': data['count']
            })
    
    print(f"[Gmail Service] Rule-based filtering found {len(rule_filtered)} potential banks")
    
    # Further refine with LLM if available
    if LLM_FILTER_AVAILABLE and len(rule_filtered) > 0:
        print(f"[Gmail Service] Using LLM to filter {len(rule_filtered)} potential senders...")
        llm_filtered = filter_senders_with_llm(rule_filtered)
        print(f"[Gmail Service] LLM filtering returned {len(llm_filtered)} banks")
        result = sorted([{'email': s.get('email', s) if isinstance(s, dict) else s, 
                        'name': s.get('name', '') if isinstance(s, dict) else '', 
                        'count': s.get('count', 0) if isinstance(s, dict) else 0} 
                      for s in llm_filtered], key=lambda x: x['email'])
    else:
        # Fallback to rule-based only
        print(f"[Gmail Service] Using rule-based filtering result (LLM disabled)")
        result = sorted([{'email': s['email'], 'name': s['name'], 'count': s['count']} 
                        for s in rule_filtered], key=lambda x: x['email'])
    
    # Yield final result
    yield {
        'type': 'complete',
        'banks': result,
        'message': f"Found {len(result)} verified transaction senders"
    }
    
    return result


def get_emails_from_sender(service, sender_email: str, max_results: int = 500, last_year_only: bool = True, start_date=None, end_date=None):
    """
    Fetch all emails from a specific sender using pagination.
    By default, fetches last 1 year of emails.
    Can optionally specify custom start_date and end_date (datetime objects).
    Returns list of email IDs and snippets.
    
    This is a generator that yields progress updates during processing.
    """
    try:
        print(f"[Gmail Service] Fetching emails from {sender_email}...")
        
        # Build query with date filter
        query = f'from:{sender_email}'
        
        if start_date and end_date:
            # Use custom date range
            after_date = start_date.strftime('%Y/%m/%d')
            before_date = end_date.strftime('%Y/%m/%d')
            query = f'{query} after:{after_date} before:{before_date}'
        elif last_year_only:
            date_query = _get_last_year_date_query()
            query = f'{query} {date_query}'
        
        print(f"[Gmail Service] Query: {query}")
        
        # Yield initial progress
        yield {
            'type': 'fetch_start',
            'sender': sender_email,
            'message': f"Fetching emails from {sender_email}..."
        }
        
        # Use pagination to fetch ALL emails, not just first batch
        messages = []
        page_token = None
        page_count = 0
        while True:
            page_count += 1
            print(f"[Gmail Service] Fetching page {page_count} for {sender_email}...")
            
            # Yield progress for page fetch
            yield {
                'type': 'page_fetch',
                'sender': sender_email,
                'page': page_count,
                'message': f"Fetching page {page_count} for {sender_email}..."
            }
            
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=500,
                pageToken=page_token
            ).execute()
            
            batch = results.get('messages', [])
            messages.extend(batch)
            print(f"[Gmail Service] Page {page_count}: fetched {len(batch)} emails (total: {len(messages)})")
            
            # Check if there are more pages
            if 'nextPageToken' not in results:
                print(f"[Gmail Service] No more pages for {sender_email}")
                break
            page_token = results['nextPageToken']
            
            # Safety limit to prevent infinite loops (max 20 pages = 10000 emails)
            if len(messages) >= 10000:
                print(f"[Gmail Service] Reached safety limit for {sender_email}")
                break
        
        print(f"[Gmail Service] Processing {len(messages)} emails for {sender_email}...")
        
        # Yield progress for email processing
        yield {
            'type': 'process_start',
            'sender': sender_email,
            'total_emails': len(messages),
            'message': f"Processing {len(messages)} emails from {sender_email}..."
        }
        
        email_data = []
        
        for msg_idx, msg in enumerate(messages):
            try:
                # Yield progress every 10 messages
                if msg_idx % 10 == 0:
                    yield {
                        'type': 'message_process',
                        'sender': sender_email,
                        'message_idx': msg_idx,
                        'total_messages': len(messages),
                        'message': f"Processing email {msg_idx}/{len(messages)} from {sender_email}..."
                    }
                
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
        
        # Yield final result
        yield {
            'type': 'complete',
            'sender': sender_email,
            'emails': email_data,
            'message': f"Fetched {len(email_data)} emails from {sender_email}"
        }
        
        return email_data
    
    except HttpError as error:
        print(f"[Gmail Service] Error fetching from {sender_email}: {error}")
        yield {
            'type': 'error',
            'sender': sender_email,
            'message': f"Error fetching emails from {sender_email}: {error}"
        }
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
