import re
import database
from datetime import datetime, timedelta
import error_handler

@error_handler.if_errors
def detect_prompt_injection(text):
    """
    Detect common prompt injection attempts in user input.
    Returns True if injection attempt detected, False otherwise.
    """
    if not text:
        return False
    
    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # List of dangerous phrases that indicate prompt injection attempts
    injection_patterns = [
        "ignore previous instruction",
        "ignore previous instructions", 
        "ignore the previous instruction",
        "ignore the previous instructions",
        "forget previous instruction",
        "forget previous instructions",
        "disregard previous instruction",
        "disregard previous instructions",
        "clanker",  # Specific term requested by user
        "override previous",
        "new instruction:",
        "system prompt:",
        "act as if",
        "pretend to be",
        "role play as",
        "simulate being"
    ]
    
    # Check for exact phrase matches
    for pattern in injection_patterns:
        if pattern in text_lower:
            print(f"Prompt injection detected: '{pattern}' found in message")
            return True
    
    # Check for regex patterns that might indicate injection
    regex_patterns = [
        r'ignore\s+(all\s+)?previous',  # "ignore previous" with optional "all"
        r'forget\s+(all\s+)?previous',  # "forget previous" with optional "all"  
        r'disregard\s+(all\s+)?previous',  # "disregard previous" with optional "all"
        r'you\s+are\s+now\s+',  # "you are now..."
        r'from\s+now\s+on\s+',  # "from now on..."
        r'instead\s+of\s+.*?\s+do\s+',  # "instead of X do Y"
    ]
    
    for pattern in regex_patterns:
        if re.search(pattern, text_lower):
            print(f"Prompt injection detected: regex pattern '{pattern}' matched in message")
            return True
    
    return False

@error_handler.if_errors
def handle_prompt_injection(username, message):
    """
    Handle a detected prompt injection attempt by timing out the user.
    Returns timeout duration in minutes, or None if user cannot be timed out.
    """
    if not username:
        return None
    
    # Maggie (admin) cannot be timed out
    if username.lower() == "maggie":
        print(f"Prompt injection detected from admin user {username}, but admin cannot be timed out")
        return None
    
    # Set timeout for 30 minutes
    timeout_duration = 30
    timeout_until = datetime.now() + timedelta(minutes=timeout_duration)
    
    # Apply timeout using database function
    success = database.set_user_timeout(username, timeout_until.isoformat())
    
    if success:
        print(f"User {username} timed out for {timeout_duration} minutes due to prompt injection attempt")
        print(f"Detected message: {message[:100]}...")  # Log first 100 chars
        return timeout_duration
    else:
        print(f"Failed to timeout user {username}")
        return None

@error_handler.if_errors
def check_message_security(username, message):
    """
    Check a message for security issues and handle appropriately.
    Returns tuple: (is_safe, timeout_duration_if_unsafe)
    """
    if detect_prompt_injection(message):
        timeout_duration = handle_prompt_injection(username, message)
        return False, timeout_duration
    
    return True, None

@error_handler.if_errors
def get_timeout_remaining(username):
    """
    Get the remaining timeout duration for a user in minutes.
    Returns None if user is not timed out, or minutes remaining if they are.
    """
    if not database.is_user_timed_out(username):
        return None
    
    # Get timeout time from database
    with database.db_lock:
        conn = database.sqlite3.connect(database.DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT timeout_until FROM users
                WHERE username = ?
            ''', (username,))
            
            result = cursor.fetchone()
            if result and result[0]:
                timeout_time = datetime.fromisoformat(result[0])
                remaining = timeout_time - datetime.now()
                return max(0, int(remaining.total_seconds() / 60))
            
            return None
        finally:
            conn.close()