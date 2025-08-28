
import os
import json
from datetime import datetime, timedelta
import glob


def journal_date():
    today = datetime.now().strftime("%Y-%m-%d")  # Assuming you generate today's date like this
    # Parse the current date string into a datetime object
    date_object = datetime.strptime(today, '%Y-%m-%d')
    
    # Subtract one day to get yesterday's date
    yesterday_date = date_object - timedelta(days=1)
    
    # Format the datetime object back into a string
    yesterday = datetime.strftime(yesterday_date, '%Y-%m-%d')

    return today, yesterday

# --- Configuration ---
JOURNAL_DIR = "JournalEntries"  # Using forward slashes for better path compatibility
SOC_DIR = "SOC"
USER_SPECIFIED_CURRENT_DATE_STR, YESTERDAY_DATE_STR = journal_date()
CURRENT_DATETIME = datetime.strptime(USER_SPECIFIED_CURRENT_DATE_STR, "%Y-%m-%d")
YESTERDAY_DATETIME = CURRENT_DATETIME - timedelta(days=1)
YESTERDAY_DATE_STR = YESTERDAY_DATETIME.strftime("%Y-%m-%d")

# --- Internal Helper Functions ---
def _get_latest_journal_file_path():
    """
    Finds the most recently modified JSON file in the journal directory.
    Returns the file path or None if no JSON files are found.
    """
    # Ensure the directory exists to prevent glob errors if it's missing
    if not os.path.isdir(JOURNAL_DIR):
        print(f"Error: Journal directory not found: {JOURNAL_DIR}")
        return None
    
    list_of_files = glob.glob(os.path.join(JOURNAL_DIR, '*.json'))
    if not list_of_files:
        return None
    
    try:
        latest_file = max(list_of_files, key=os.path.getmtime)
        return latest_file
    except FileNotFoundError:
        # This can happen in a rare race condition if a file is deleted between glob and getmtime
        print(f"Error: A file listed by glob was not found during mtime check in {JOURNAL_DIR}")
        return None

# --- Main Journal Data Function ---
def get_journal_data_from_latest_file():
    """
    Retrieves and parses JSON data from Harry's latest journal entry file.
    If no file is found or an error occurs, it returns a default structure.
    """
    latest_file_path = _get_latest_journal_file_path()

    if not latest_file_path:
        print(f"No journal files found in {JOURNAL_DIR}. Returning default structure for 'yesterday'.")
        return {
            "date": YESTERDAY_DATE_STR,
            "sentiment": "N/A",
            "mood": "N/A",
            "tags": [],
            "journal_entry": f"There was no journal entry for {YESTERDAY_DATE_STR} (no file found).",
            "long_term_goal": "N/A"
        }

    try:
        with open(latest_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # It's good practice to ensure the 'date' field exists,
        # even if we primarily rely on the file being the "latest".
        if "date" not in data:
            print(f"Warning: Journal file {latest_file_path} is missing the 'date' field. Using 'unknown date'.")
            data["date"] = "unknown date" # Ensure key exists for downstream functions
        return data
    except FileNotFoundError:
        # This case should ideally be caught by _get_latest_journal_file_path returning None,
        # but kept for robustness.
        print(f"Error: Journal file {latest_file_path} not found unexpectedly.")
        return {
            "date": YESTERDAY_DATE_STR,
            "journal_entry": f"Error: File {latest_file_path} not found.",
            "long_term_goal": "Error: File not found."
        }
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {latest_file_path}.")
        return {
            "date": YESTERDAY_DATE_STR, # Or attempt to get date from filename if possible
            "journal_entry": f"Error: Invalid JSON in {latest_file_path}.",
            "long_term_goal": "Error: Invalid JSON."
        }
    except Exception as e:
        print(f"An unexpected error occurred while reading journal file {latest_file_path}: {e}")
        return {
            "date": YESTERDAY_DATE_STR,
            "journal_entry": f"Error reading journal: {e}",
            "long_term_goal": f"Error reading journal: {e}"
        }

# --- Functions for Extracting Specific Data from Journal ---

def get_journal_entry_text(journal_data: dict) -> str:
    """Returns the journal_entry string from the provided journal data."""
    return journal_data.get("journal_entry", f"Journal entry not found for date {journal_data.get('date', 'unknown')}.")

def get_long_term_goal_text(journal_data: dict) -> str:
    """Returns the long_term_goal string from the provided journal data."""
    return journal_data.get("long_term_goal", f"Long term goal not found for date {journal_data.get('date', 'unknown')}.")

# --- Functions for Age-Related Statements ---

def get_journal_age_statement(journal_data: dict) -> str:
    """
    Determines how many days ago the journal entry is from (relative to USER_SPECIFIED_CURRENT_DATE_STR)
    and returns an appropriate statement.
    """
    journal_date_str = journal_data.get("date")
    if not journal_date_str or journal_date_str == "unknown date":
        return "My journal entry from an unknown date:"

    try:
        journal_date_obj = datetime.strptime(journal_date_str, "%Y-%m-%d")
    except ValueError:
        return f"My journal entry from a date with an invalid format ({journal_date_str}):"

    # Calculate days ago from the user-specified current date (May 29th, 2025)
    actual_days_ago = (CURRENT_DATETIME - journal_date_obj).days

    if actual_days_ago == 1:  # Entry is from May 28th (yesterday relative to May 29th)
        return "My journal entry from yesterday:"
    elif actual_days_ago == 0: # Entry is from "today" (May 29th)
        return "My journal entry from today:"
    elif actual_days_ago < 0: # Entry is from the future
        return f"My journal entry from {-actual_days_ago} days in the future (relative to {USER_SPECIFIED_CURRENT_DATE_STR}):"
    else:  # actual_days_ago > 1 or other cases
        return f"My journal entry from {actual_days_ago} days ago:"

def get_long_term_goal_age_statement(journal_data: dict) -> str:
    """
    Determines how many days ago the journal entry (and its LTA) is from
    and returns an appropriate statement for the long term goal.
    """
    journal_date_str = journal_data.get("date")
    if not journal_date_str or journal_date_str == "unknown date":
        return "My long term goal from an unknown date:"

    try:
        journal_date_obj = datetime.strptime(journal_date_str, "%Y-%m-%d")
    except ValueError:
        return f"My long term goal from a date with an invalid format ({journal_date_str}):"

    actual_days_ago = (CURRENT_DATETIME - journal_date_obj).days

    if actual_days_ago == 1:  # Entry is from May 28th
        return "My long term goal from yesterday:"
    elif actual_days_ago == 0: # Entry is from "today" (May 29th)
        return "My long term goal from today:"
    elif actual_days_ago < 0:
        return f"My long term goal from {-actual_days_ago} days in the future (relative to {USER_SPECIFIED_CURRENT_DATE_STR}):"
    else:  # actual_days_ago > 1
        return f"My long term goal from {actual_days_ago} days ago:"

# --- SOC File Check Function ---
def check_soc_file_size() -> bool:
    """
    Checks today's SOC file (YYYY-MM-DD.txt in SOC, based on USER_SPECIFIED_CURRENT_DATE_STR).
    Returns True if file size > 1600 KB.
    Returns False otherwise (covering cases <= 1600 KB, which also means it handles the
    user's secondary condition "if less than 2500 KB, return False" for those smaller files).
    """
    today_date_str_for_soc = CURRENT_DATETIME.strftime("%Y-%m-%d")
    soc_file_name = f"{today_date_str_for_soc}.txt"
    soc_file_path = os.path.join(SOC_DIR, soc_file_name)

    if not os.path.exists(soc_file_path):
        print(f"SOC file {soc_file_path} for {today_date_str_for_soc} not found.")
        return False # Default if file doesn't exist to check

    try:
        file_size_bytes = os.path.getsize(soc_file_path)
        file_size_kb = file_size_bytes / 1024.0  # Use float division for precision

        if file_size_kb > 1600:
            return True
        else:
            # If file_size_kb <= 1600 KB, it is inherently < 2500 KB.
            # So, this 'else' correctly implements the outcome for both:
            # - Not being > 1600 KB
            # - Being < 2500 KB (as a consequence of being <= 1600 KB)
            return False
            
    except FileNotFoundError: # Should be caught by os.path.exists, but robust
        print(f"Error: SOC file {soc_file_path} disappeared before size check.")
        return False
    except Exception as e:
        print(f"An error occurred checking SOC file {soc_file_path}: {e}")
        return False # Default to False on error

# Example of how you might call these functions:
if __name__ == "__main__":
    print(f"Operating based on user-specified current date: {USER_SPECIFIED_CURRENT_DATE_STR}\n")

    # 1. Get data from the latest journal entry
    harrys_latest_journal_data = get_journal_data_from_latest_file()
    print(f"Fetched latest journal data (assumed yesterday's):")
    # print(json.dumps(harrys_latest_journal_data, indent=4)) # Pretty print the dict
    
    # 2. Use the helper functions
    if harrys_latest_journal_data and harrys_latest_journal_data.get("journal_entry", "").startswith("Error:") is False :
        entry_text = get_journal_entry_text(harrys_latest_journal_data)
        goal_text = get_long_term_goal_text(harrys_latest_journal_data)
        journal_age_stmt = get_journal_age_statement(harrys_latest_journal_data)
        goal_age_stmt = get_long_term_goal_age_statement(harrys_latest_journal_data)

        print(f"\n--- Journal Details ---")
        print(f"{journal_age_stmt} {entry_text}")
        print(f"{goal_age_stmt} {goal_text}")
    else:
        print("\nCould not retrieve valid journal data to process further details.")
        if harrys_latest_journal_data:
             print(f"Content: {harrys_latest_journal_data.get('journal_entry')}")


    # 3. Check SOC file size
    print(f"\n--- SOC File Check for {CURRENT_DATETIME.strftime('%Y-%m-%d')} ---")
    
    # General call (will look for actual file or print not found)
    soc_status = check_soc_file_size()
    print(f"Result of check_soc_file_size(): {soc_status}")
    if soc_status:
        print("The SOC file is larger than 1600 KB.")
    else:
        print("The SOC file is not larger than 1600 KB (or not found/error).")
