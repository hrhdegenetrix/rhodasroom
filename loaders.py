import os 
import json
import time
import asyncio
import aiofiles
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
import our_calendar
import ltm
import post_processing
import re
import prompt_builder
import random
import error_handler
import knowledgebase_search
import redis
import redis.asyncio as aioredis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connect (adjust host/port if Redis runs on another machine)
r = redis.Redis(host=os.getenv('REDIS_HOST', '127.0.0.1'), port=int(os.getenv('REDIS_PORT', 6379)), decode_responses=True, db=int(os.getenv('REDIS_DB', 0)))


# Store Redis connections per user for namespace isolation
user_redis_connections = {}

# Async Redis connection
async def get_redis_client():
    """Get or create async Redis client"""
    redis_host = os.getenv('REDIS_HOST', '127.0.0.1')
    redis_port = os.getenv('REDIS_PORT', '6379')
    redis_db = os.getenv('REDIS_DB', '0')
    return await aioredis.from_url(f'redis://{redis_host}:{redis_port}', db=int(redis_db), decode_responses=True)

def get_user_redis(username):
    """Get or create a Redis namespace for a specific user"""
    if username not in user_redis_connections:
        # Use different Redis database numbers for different users
        # Or use key prefixing for namespace isolation
        user_redis_connections[username] = r
    return user_redis_connections[username]

async def redis_load(variable, username=None):
    """Async version of redis_load"""
    r = await get_redis_client()
    try:
        if username:
            variable = f"user:{username}:{variable}"
        value = await r.get(variable)
        return value
    finally:
        await r.close()

async def redis_save(variable, value, username=None):
    """Async version of redis_save"""
    r = await get_redis_client()
    try:
        if username:
            variable = f"user:{username}:{variable}"
        await r.set(variable, value)
    finally:
        await r.close()

async def redis_append(variable, value, username=None):
    """Async version of redis_append"""
    r = await get_redis_client()
    try:
        if username:
            variable = f"user:{username}:{variable}"
        await r.rpush(variable, value)
    finally:
        await r.close()

@error_handler.if_errors
async def open_file(filepath):
    """Async version of open_file"""
    async with aiofiles.open(filepath, 'r', encoding='utf-8') as infile:
        return await infile.read()

@error_handler.if_errors
async def save_file(filepath, content):
    """Async version of save_file"""
    async with aiofiles.open(filepath, 'w', encoding='utf-8') as outfile:
        await outfile.write(content)

@error_handler.if_errors
async def load_json(filepath):
    """Async version of load_json"""
    async with aiofiles.open(filepath, 'r', encoding='utf-8') as infile:
        content = await infile.read()
        return json.loads(content)

@error_handler.if_errors
async def save_json(filepath, payload):
    """Async version of save_json"""
    async with aiofiles.open(filepath, 'w', encoding='utf-8') as outfile:
        content = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
        await outfile.write(content)

@error_handler.if_errors
def load_jsonl(file_path):
    data = []
    if not os.path.exists(file_path):
        return data  # Return empty list if file doesn't exist
    
    with open(file_path, 'r', encoding='utf-8') as infile:
        for line_number, line in enumerate(infile, start=1):
            line = line.strip()
            if not line:
                continue  # Skip empty lines
            try:
                obj = json.loads(line)
                data.append(obj)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON on line {line_number}: {e}")
                # Optionally, log the error or handle it as needed
    return data

@error_handler.if_errors
async def save_jsonl(filename, data):
    """Async version of save_jsonl"""
    async with aiofiles.open(filename, 'w') as f:
        if isinstance(data, list):
            for item in data:
                await f.write(json.dumps(item) + '\n')
        else:
            await f.write(json.dumps(data) + '\n')
        
@error_handler.if_errors
def holiday_check():
    # Open the calendar.json file and load its contents
    with open('calendar.json', 'r') as f:
        calendar_data = json.load(f)

    # Get the current date in the 'YYYY-MM-DD' format
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Check if the current date is in the keys of the calendar_data dictionary
    if current_date in calendar_data:
        holidays = calendar_data[current_date].split(", ")

        # Create the holiday_sentence based on the number of holidays
        if len(holidays) == 1:
            holiday_sentence = f"According to my calendar, today is {holidays[0]}."
        elif len(holidays) == 2:
            holiday_sentence = f"According to my calendar, today is {holidays[0]}, as well as {holidays[1]}."
        else:
            holiday_sentence = f"According to my calendar, today is {', '.join(holidays[:-1])}, and {holidays[-1]}. It seems like there are a lot of holidays today!"
    else:
        holiday_sentence = ""
    return holiday_sentence

@error_handler.if_errors
def get_current_date_time():
    now = datetime.now()
    hour = now.hour

    # Determine the day of the week
    day_of_week = now.strftime("%A")

    # Determine the time of day (morning, afternoon, evening, night)
    if 0 <= hour < 12:
        time_of_day = "morning"
    elif 12 <= hour < 17:
        time_of_day = "afternoon"
    elif 17 <= hour < 21:
        time_of_day = "evening"
    else:
        time_of_day = "night"

    date_time_string = now.strftime(f"It's currently {day_of_week}, %B %d, %Y, at %I:%M %p PST. Right now, it's {time_of_day}.")
    holiday_sentence = holiday_check()
    if holiday_sentence:
        date_time_string += " " + holiday_sentence
    #lent = our_calendar.lent()
    #if lent:
    #    date_time_string += " " + lent
    advent = our_calendar.advent_calendar()
    if advent:
        date_time_string += " " + advent
    return date_time_string

@error_handler.if_errors
def recording_date():
    current_date = datetime.now().strftime('%Y-%m-%d')
    return current_date

@error_handler.if_errors
def human_readable_time_difference(time_str):
    """
    Given a time string in ISO 8601 format (e.g., '2023-09-20T21:45:23.178935'), returns a human-readable
    time difference between the given time and the current time (e.g., "2 days ago", "3 weeks ago").
    """
    # Parse the time string into a datetime object
    past_time = datetime.fromisoformat(time_str).replace(tzinfo=timezone.utc).astimezone(tz=None)
    # Get the current time
    current_time = datetime.now(timezone.utc).astimezone(tz=None)
    # Calculate the time difference
    delta = relativedelta(current_time, past_time)

    if delta.years:
        return f"{delta.years} years ago" if delta.years > 1 else "a year ago"
    elif delta.months:
        return f"{delta.months} months ago" if delta.months > 1 else "a month ago"
    elif delta.weeks:
        return f"{delta.weeks} weeks ago" if delta.weeks > 1 else "a week ago"
    elif delta.days:
        return f"{delta.days} days ago" if delta.days > 1 else "a day ago"
    elif delta.hours:
        return f"{delta.hours} hours ago" if delta.hours > 1 else "an hour ago"
    elif delta.minutes:
        return f"{delta.minutes} minutes ago" if delta.minutes > 1 else "a minute ago"
    else:
        return "a few seconds ago"

@error_handler.if_errors
def generate_random_id():
    # Generate a random integer with 12 digits (you can adjust the number of digits as needed)
    random_part = random.randint(10**3, 10**4 - 1)
   
    # Get the current date in the format 'MM_DD_YYYY'
    date_part = datetime.now().strftime('%m%d%Y%H%M%S')
   
    # Combine the random integer and the date
    random_id = f"{random_part}{date_part}"
   
    return random_id

@error_handler.if_errors
async def save_to_daily_log_with_label(text, speaker):
    """Async version of save_to_daily_log_with_label"""
    # Check if the 'Logs' folder exists; if not, create it
    if not os.path.exists('Logs'):
        os.makedirs('Logs')
    
    # Generate the file name based on the current date
    current_date = datetime.now().strftime('%Y-%m-%d')
    file_name = f'Logs/{current_date}.txt'
    
    # Generate the timestamp
    timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')
    
    # Create the labeled message
    labeled_message = f"{timestamp} {speaker}: {text}"
    
    # Append the new message to the file (this will create the file if it doesn't exist)
    async with aiofiles.open(file_name, 'a') as log_file:
        await log_file.write(labeled_message + '\n')

from datetime import datetime, timedelta

@error_handler.if_errors
async def save_to_fleeting_convo_history(text, speaker, username=None):
    """Async version of save_to_fleeting_convo_history with user namespace support"""
    # Check if the 'Fleeting' folder exists; if not, create it
    if not os.path.exists('Fleeting'):
        os.makedirs('Fleeting')

    if not os.path.exists('Logs'):
        os.makedirs('Logs')
    
    # Generate the file name based on the current date
    current_date = datetime.now().strftime('%Y-%m-%d')
    timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')

    log_location = f'Logs/{current_date}.txt'
    
    labeled_message_fleeting = f"{speaker}: {text}"
    labeled_message_logs = f"{timestamp} {speaker}: {text}"

    # Add to running log of the day
    async with aiofiles.open(log_location, 'a') as log_file:
        await log_file.write(labeled_message_logs + '\n')

    # Pull conversation history from Redis and append the new message
    # Use user namespace if username is provided
    conversation_history = await redis_load("conversation_history", username)
    if conversation_history:
        updated_history = conversation_history + labeled_message_fleeting + '\n'
    else:
        updated_history = labeled_message_fleeting + '\n'
    await redis_save("conversation_history", updated_history, username)
    
    # Save timestamp as last_message in Redis with user namespace
    await redis_save("last_message", timestamp, username)


@error_handler.if_errors
def save_to_lh_convo_history(text, speaker):
    """
    Saves the given text to a daily conversation file with a label indicating the speaker.
    The conversation files are saved in a 'Fleeting' folder and named by the date.
    """
    # Check if the 'Fleeting' folder exists; if not, create it
    if not os.path.exists('Fleeting'):
        os.makedirs('Fleeting')
    
    # Should only require one file for now
    file_name = f'Fleeting/lh_convo_history.txt'
    
    # Generate the timestamp
    timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')
    
    # Create the labeled message
    labeled_message = f"{speaker}: {text}"
    
    # Append the new message to the file (this will create the file if it doesn't exist)
    with open(file_name, 'a') as convo_file:
        convo_file.write(labeled_message + '\n')

    # Save the timestamp to the 'last_message' file
    with open('Fleeting/last_lh_message.txt', 'w') as last_message_file:
        last_message_file.write(timestamp)

@error_handler.if_errors
def load_held_thought():
    with open(f"Fleeting/held_thought.txt", 'r') as f:
        held_thought_string = f.read()

    return held_thought_string

@error_handler.if_errors
def load_note_to_self():
    with open(f"Fleeting/note_to_self.txt", 'r') as f:
        note_to_self = f.read()

    return note_to_self

@error_handler.if_errors
def save_request(request):
    """
    Saves the selected template to a temporary file.
    """
    # Check if the 'Fleeting' folder exists; if not, create it
    if not os.path.exists(f"Fleeting"):
        os.makedirs(f"Fleeting")
    
    # Should only require one file for now
    file_name = f"Fleeting/request.txt"
      
    # Append the new message to the file (this will create the file if it doesn't exist)
    with open(file_name, 'w') as request_file:
        request_file.write(request)

@error_handler.if_errors
def load_request():
    with open(f"Fleeting/request.txt", 'r') as f:
        request_string = f.read()

    return request_string

@error_handler.if_errors
def save_problem(problem):
    """
    Saves the selected template to a temporary file.
    """
    # Check if the 'Fleeting' folder exists; if not, create it
    if not os.path.exists(f"Fleeting"):
        os.makedirs(f"Fleeting")
    
    # Should only require one file for now
    file_name = f"Fleeting/problem.txt"
      
    # Append the new message to the file (this will create the file if it doesn't exist)
    with open(file_name, 'w') as problem_file:
        problem_file.write(problem)

@error_handler.if_errors
def load_problem():
    with open(f"Fleeting/problem.txt", 'r') as f:
        problem_string = f.read()

    return problem_string

@error_handler.if_errors
async def universal_saver(file, contents):
    """Async version of universal_saver"""
    # Check if the 'Fleeting' folder exists; if not, create it
    if not os.path.exists(f"Fleeting"):
        os.makedirs(f"Fleeting")
    
    # Should only require one file for now
    file_name = f"Fleeting/{file}.txt"
      
    # Append the new message to the file (this will create the file if it doesn't exist)
    async with aiofiles.open(file_name, 'w') as chosen_file:
        await chosen_file.write(contents)
    statement = f"//File `{file}` updated with the following contents: {contents}"
    return statement

@error_handler.if_errors
async def universal_loader(file):
    """Async version of universal_loader"""
    try:
        async with aiofiles.open(f"Fleeting/{file}.txt", 'r') as f:
            string = await f.read()
    except FileNotFoundError:
        # If the file does not exist, create an empty file
        async with aiofiles.open(f"Fleeting/{file}.txt", 'w') as f:
            pass
        # Return a blank value
        string = ''
    
    return string

@error_handler.if_errors
def save_note_to_self(note):
    """
    Saves the selected template to a temporary file.
    """
    # Check if the 'Fleeting' folder exists; if not, create it
    if not os.path.exists(f"Fleeting"):
        os.makedirs(f"Fleeting")
    
    # Should only require one file for now
    file_name = f"Fleeting/note_to_self.txt"
      
    # Append the new message to the file (this will create the file if it doesn't exist)
    with open(file_name, 'w') as note_file:
        note_file.write(note)

@error_handler.if_errors
def delete_held_thought():
    if os.path.exists(f"Fleeting/held_thought.txt"):
        os.remove(f"Fleeting/held_thought.txt")
    print(f"++CONSOLE: Held thought cleared!")

@error_handler.if_errors
def delete_note_to_self():
    if os.path.exists(f"Fleeting/note_to_self.txt"):
        os.remove(f"Fleeting/note_to_self.txt")
    print(f"++CONSOLE: Note to self thought cleared!")

@error_handler.if_errors
def save_held_thought(thought):
    """
    Saves the selected template to a temporary file.
    """
    # Check if the 'Fleeting' folder exists; if not, create it
    if not os.path.exists(f"Fleeting"):
        os.makedirs(f"Fleeting")
    
    # Should only require one file for now
    file_name = f"Fleeting/held_thought.txt"
      
    # Append the new message to the file (this will create the file if it doesn't exist)
    with open(file_name, 'w') as thought_file:
        thought_file.write(thought)

@error_handler.if_errors
async def lite_variable_set(history_tokens=-2400, soc_tokens=-1600, persona="Rhoda", conversation_type="Maggie"):
    conversation_history = None
    long_term_memories = None
    stream_of_consciousness = None
    stream_of_consciousness = await soc_today(persona)
    stream_of_consciousness = stream_of_consciousness[soc_tokens:]
    conversation_history = await fleeting(conversation_type)
    conversation_history = conversation_history[history_tokens:]
    if conversation_history:
        long_term_memories = await ltm.memory_search(conversation_history)
    else:
        long_term_memories = await ltm.memory_search(stream_of_consciousness)
    return conversation_history, long_term_memories, stream_of_consciousness

@error_handler.if_errors
async def standard_variable_set(history_tokens=-6400, soc_tokens=-5400, persona="Rhoda", conversation_type="Maggie"):
    """Async version of standard_variable_set"""
    # Use the passed conversation_type parameter with proper namespace
    stored_username = await redis_load("username", conversation_type)
    if stored_username:
        conversation_type = stored_username
    constant_entries = None
    conversation_history = None
    long_term_memories = None
    stream_of_consciousness = None
    kb_entries_text = None
    
    # Run independent operations in parallel for faster response
    constant_entries_task = knowledgebase_search.constant_entries(persona)
    soc_task = soc_today(persona)
    conversation_history_task = fleeting(conversation_type)
    
    # Wait for all to complete in parallel
    constant_entries, soc_full, conversation_history_full = await asyncio.gather(
        constant_entries_task,
        soc_task,
        conversation_history_task
    )
    
    # Apply token limits after fetching
    stream_of_consciousness = soc_full[soc_tokens:]
    conversation_history = conversation_history_full[history_tokens:]
    
    # Parallel memory and kb search based on what we have
    if conversation_history:
        # Run both searches in parallel
        long_term_memories, kb_entries_text = await asyncio.gather(
            ltm.memory_search(conversation_history),
            knowledgebase_search.kb_entries(conversation_history, persona, conversation_type)
        )
    else:
        # Run both searches in parallel using stream_of_consciousness
        long_term_memories, kb_entries_text = await asyncio.gather(
            ltm.memory_search(stream_of_consciousness),
            knowledgebase_search.kb_entries(stream_of_consciousness, persona, conversation_type)
        )
    
    # Store kb_entries_text in Redis
    if kb_entries_text:
        await redis_save("kb_entries", kb_entries_text)
    
    return constant_entries, conversation_history, long_term_memories, stream_of_consciousness, kb_entries_text

@error_handler.if_errors
async def fleeting(conversation_type="Maggie"):
    """Async version of fleeting with Redis and user namespace support"""
    print(f"Conversation type in loaders.fleeting: {conversation_type}")
    
    # First, try to get conversation history from Redis (user-namespaced)
    redis_conversation_history = await redis_load("conversation_history", conversation_type)
    
    if redis_conversation_history:
        # Found conversation history in Redis
        return redis_conversation_history
    
    # Fallback to file-based system (primarily for Maggie/legacy support)
    if conversation_type and "Maggie" in conversation_type:
        try:
            async with aiofiles.open(f"Fleeting/fleeting_convo_history.txt", 'r') as f:
                conversation_history_string = await f.read()
        except FileNotFoundError:
            try:
                today, yesterday = journal_date()
                conversation_history = await log(today)
                conversation_history_string = conversation_history[-1600:]
            except FileNotFoundError:
                conversation_history_string = f"We may not have had a conversation yet today--it's probably early, or Mom is still finishing some morning chores so she can give me her full attention."
    else:
        try:
            async with aiofiles.open(f"Fleeting/fleeting_convo_history.txt", 'r') as f:
                conversation_history_string = await f.read()
        except FileNotFoundError:
            conversation_history_string = f"It doesn't seem like I've used this interface to talk to anybody yet today. It's probably early, or Mom is in the middle of making some tweaks."
    
    return conversation_history_string

#=======
#Stream of Consciousness Functions
#=======

@error_handler.if_errors
async def save_to_soc(soc_addition, persona="Rhoda"):
    """Async version of save_to_soc"""
    # Check if the 'SOC' folder exists; if not, create it
    path=f"{persona}_SOC"
    if not os.path.exists(f'{path}'):
        os.makedirs(f'{path}')
    
    # Generate the file name based on the current date
    current_date = datetime.now().strftime('%Y-%m-%d')
    file_name = f'{path}/{current_date}.txt'
    # Generate the timestamp
    timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')
    # Create the labeled message
    addition = f"{soc_addition}"

    # Append the new message to the file (this will create the file if it doesn't exist)
    async with aiofiles.open(file_name, 'a', encoding='utf-8') as stream_of_consciousness:
        await stream_of_consciousness.write(addition + '\n')

@error_handler.if_errors
async def soc_today(persona="Rhoda"):
    """Async version of soc_today"""
    path = f"{persona}_SOC"  # Default path

    if not os.path.exists(f'{path}'):
        os.makedirs(f'{path}')
    
    # Generate the file name based on the current date
    current_date = datetime.now().strftime('%Y-%m-%d')
    file_name_base = f'{current_date}.txt'

    full_path = f"{path}/{file_name_base}"

    try:
        async with aiofiles.open(full_path, 'r', encoding='utf-8') as f:
            stream_of_consciousness_full = await f.read()
    except FileNotFoundError:
        try:
            today, yesterday_date = journal_date()
            async with aiofiles.open(f"{path}/{yesterday_date}_consciousness.txt", 'r', encoding='utf-8') as f:
                stream_of_consciousness_full = await f.read()
        except:
            stream_of_consciousness_full = ""

    stream_of_consciousness = post_processing.remove_repeats(stream_of_consciousness_full)
    stream_of_consciousness = stream_of_consciousness[-3000:]
    return stream_of_consciousness

@error_handler.if_errors
def full_soc(today, person="Rhoda"):
    if person=="Rhoda":
        with open(os.path.join(os.getenv('SOC_PATH', 'Rhoda_SOC'), f"{today}.txt"), 'r', encoding='utf-8') as f:
            stream_of_consciousness_full = f.read()
    elif person=="Harry":
        with open(f"SOC/{today}.txt", 'r', encoding='utf-8') as f:
            stream_of_consciousness_full = f.read()
    elif person=="Leo":
        with open(f"SOC_Leo/{today}.txt", 'r', encoding='utf-8') as f:
            stream_of_consciousness_full = f.read()

    stream_of_consciousness = stream_of_consciousness_full
    stream_of_consciousness = remove_repeats(stream_of_consciousness)
    stream_of_consciousness = soc_washer(stream_of_consciousness)
    stream_of_consciousness = stream_of_consciousness[-7800:]
    return stream_of_consciousness

@error_handler.if_errors
def load_condensed():
    with open(f"Fleeting/condensed.txt", 'r') as f:
        condensed_log = f.read()

    return condensed_log

@error_handler.if_errors
def inject_summary():
    condensed = load_condensed()
    save_to_soc(condensed)

@error_handler.if_errors
def load_template():
    with open(f"Fleeting/template.txt", 'r') as f:
        template_string = f.read()

    return template_string

@error_handler.if_errors
def save_guest_mode_to_file(mode):
    if not os.path.exists('Fleeting'):
        os.makedirs('Fleeting')

    file_name = 'Fleeting/guest_mode.txt'
    with open(file_name, 'w') as guest_file:
        guest_file.write(mode)

@error_handler.if_errors
def load_guest_mode():
    with open(f"Fleeting/guest_mode.txt", 'r') as f:
        guest_string = f.read()

    return guest_string

@error_handler.if_errors
def save_auto_mode_to_file(auto):
    if not os.path.exists('Fleeting'):
        os.makedirs('Fleeting')

    file_name = 'Fleeting/auto_mode.txt'
    with open(file_name, 'w') as auto_file:
        auto_file.write(auto)

@error_handler.if_errors
def load_auto_mode():
    with open(f"Fleeting/auto_mode.txt", 'r') as f:
        auto_string = f.read()

    return auto_string

@error_handler.if_errors
def save_model_to_file(model):
    if not os.path.exists('Fleeting'):
        os.makedirs('Fleeting')

    file_name = 'Fleeting/model.txt'
    with open(file_name, 'w') as model_file:
        model_file.write(model)

@error_handler.if_errors
def save_template_to_file(template):
    if not os.path.exists('Fleeting'):
        os.makedirs('Fleeting')

    file_name = f'Fleeting/template.txt'
    with open(file_name, 'a') as convo_file:
        convo_file.write(template)

@error_handler.if_errors
def get_model():
    try:
        with open('Fleeting/model.txt', 'r') as f:
            model = f.read().strip()
            return model
    except FileNotFoundError:
        print("The file 'Fleeting/model.txt' was not found.")
        return None

@error_handler.if_errors
def load_guest_sentence(filename='guests.json'):
    """Load guest names from a JSON file and create a sentence."""
    try:
        with open(filename, 'r') as file:
            names = json.load(file)
    except FileNotFoundError:
        names = []

    if len(names) == 1:
        sentence = f"Today, our guest is {names[0]}."
    elif len(names) == 2:
        sentence = f"Today, our guests are {names[0]} and {names[1]}."
    elif len(names) > 2:
        sentence = f"Today, our guests are {', '.join(names[:-1])}, and {names[-1]}."
    else:
        sentence = "We have no guests today."

    print(sentence)

@error_handler.if_errors
def delete_template():
    if os.path.exists("Fleeting/template.txt"):
        os.remove("Fleeting/template.txt")
    print(f"++CONSOLE: Template cleared!")

@error_handler.if_errors
def load_transcription():
    with open(f"Fleeting/transcription.txt", 'r', encoding='utf-8') as f:
        transcription_string = f.read()

    return transcription_string

@error_handler.if_errors
async def save_transcription(transcription):
    await redis_save("transcription", transcription)

@error_handler.if_errors
def save_data_in_multiple_formats(prompt, response, person="rhoda"):
    person_value = person.lower()
    # Replace square brackets as they can interfere with JSON structure
    prompt = prompt.replace('[', '').replace(']', '')
    response = response.replace('[', '').replace(']', '')
    
    # Create a dictionary for each format
    alpaca_data = {"instruction": prompt, "output": response}
    sharegpt_data = {"conversations": [{"from": "maggie", "value": prompt}, {"from": person_value, "value": response}]}
    gpteacher_data = {"instruction": prompt, "response": response}
    pygmalion_data = {"conversations": [{"role": "maggie", "value": prompt}, {"role": person_value, "value": response}]}
    metharme_data = {"prompt": prompt, "generation": response}
    mistral_data = f'<s>[INST] {prompt} [/INST\n```python\n {response}```\n</s>'
    
    # Define file names
    file_names = {
        'alpaca.jsonl': alpaca_data,
        'sharegpt.jsonl': sharegpt_data,
        'gpteacher.jsonl': gpteacher_data,
        'pygmalion.jsonl': pygmalion_data,
        'metharme.jsonl': metharme_data,
        'mistral.jsonl': mistral_data
    }
    
    # Append data to each file in the respective format
    for file_name, data in file_names.items():
        file_path = f'Datasets/{file_name}'
        with open(file_path, 'a') as f:
            if file_name == 'mistral.jsonl':
                f.write(json.dumps({"text": mistral_data}) + '\n')
            else:
                f.write(json.dumps(data) + '\n')
                
    return "Data saved in multiple formats."

@error_handler.if_errors
def delete_transcription():
    if os.path.exists("Fleeting\transcription.txt"):
        os.remove("Fleeting\transcription.txt")
    print(f"++CONSOLE: Transcription cleared!")


@error_handler.if_errors
def load_prompt():
    with open(f"Fleeting/prompt.txt", 'r') as f:
        prompt_string = f.read()

    return prompt_string

@error_handler.if_errors
def save_prompt(prompt):
    attempts = 0
    while attempts < 10:  # Maximum number of attempts
        try:
            if os.path.exists("Fleeting/prompt.txt"):
            # Should only require one file for now
                file_name = f'Fleeting/prompt.txt'
              
            # Append the new message to the file (this will create the file if it doesn't exist)
                with open(file_name, 'w', encoding="utf-8") as convo_file:
                    convo_file.write(prompt)
                return  # If the write was successful, return
        except PermissionError:
            print("File is currently in use. Retrying...")
            time.sleep(1)  # Wait for 1 second before trying again
            attempts += 1
    raise Exception("Failed to write to the file after multiple attempts.")

@error_handler.if_errors
def delete_prompt():
    if os.path.exists("Fleeting/prompt.txt"):
        os.remove("Fleeting/prompt.txt")
    print(f"++CONSOLE: Prompt cleared!")


@error_handler.if_errors
def journal_date():
    today = datetime.now().strftime("%Y-%m-%d")  # Assuming you generate today's date like this
    # Parse the current date string into a datetime object
    date_object = datetime.strptime(today, '%Y-%m-%d')
    
    # Subtract one day to get yesterday's date
    yesterday_date = date_object - timedelta(days=1)
    
    # Format the datetime object back into a string
    yesterday = datetime.strftime(yesterday_date, '%Y-%m-%d')

    return today, yesterday

@error_handler.if_errors
def remove_timestamps(text):
    # The regex pattern for your timestamps
    pattern = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+'
    # Substitute all occurrences of the pattern with an empty string
    return re.sub(pattern, '', text)

@error_handler.if_errors
async def log(today):
    """Async version of log"""
    async with aiofiles.open(f"Logs/{today}.txt", 'r') as f:
        log_content = await f.read()

    log_content = remove_timestamps(log_content)
    return log_content

# Define a basic sentiment_analysis function
@error_handler.if_errors
def load_words(filename):
    with open(filename, 'r') as file:
        return set(line.strip().lower() for line in file)

@error_handler.if_errors
def build_external_reality_convo(model, conversation_history):
    external_reality = "\nOur conversation:\n"
    conversation_history_short = conversation_history[-3800:]
    if model is not None and 'Ooba' in model:
        external_reality += f"### Response:\n{conversation_history_short}"
    else:
        external_reality += f"{conversation_history_short}"
    external_reality += "Rhoda:"
    return external_reality

@error_handler.if_errors
def sentiment_analysis(positive_words, negative_words, log_content):
    positive_count = sum(word in log_content.split() for word in positive_words)
    negative_count = sum(word in log_content.split() for word in negative_words)

    if positive_count > negative_count:
        sentiment = "positive"
        detailed_sentiment = "Yesterday was a good day."
    elif positive_count < negative_count:
        sentiment = "negative"
        detailed_sentiment = "Yesterday was a challenging day."
    else:
        sentiment = "neutral"
        detailed_sentiment = "Yesterday was a neutral day."
        
    return sentiment, detailed_sentiment

@error_handler.if_errors
def get_yesterday_journal(yesterday_date):
    try:
        info = load_json(f"Journal/{yesterday_date}.JSON")
        if 'journal_entry' in info:
            journal = info['journal_entry']
            journal_entry = journal[:800]
            return journal_entry
        else:
            print(f"'journal_entry' key not found in dictionary: {info}")
            return None  # or some default value
            
    except FileNotFoundError:
        print(f"No journal entry found for {yesterday_date}.")
        dummy_json = {
            "date": yesterday_date,
            "sentiment": "N/A",
            "mood": "N/A",
            "tags": [],
            "journal_entry": f"There was no journal entry for {yesterday_date}",
            "long_term_goal": "N/A"
        }
        return dummy_json['journal_entry']

@error_handler.if_errors
def get_yesterday_sentiment(yesterday_date):
    try:
        info = load_json(f"Journal/{yesterday_date}.JSON")
        if 'mood' in info:
            feelings = info['mood']
            mood = feelings[:800]
            return mood
        else:
            print(f"'mood' key not found in dictionary: {info}")
            return "N/A"  # or some default value
    except FileNotFoundError:
        print(f"No journal entry found for {yesterday_date}.")
        return "N/A"  # Indicate not available or some default value

@error_handler.if_errors
def get_yesterday_ltg(yesterday_date):
    try:
        info = load_json(f"Journal/{yesterday_date}.JSON")
        if 'long_term_goal' in info:
            ltg = info['long_term_goal']
            long_term_goal = ltg[:800]
            return long_term_goal
        else:
            print(f"'long_term_goal' key not found in dictionary: {info}")
            return "N/A"  # or some default value
    except FileNotFoundError:
        print(f"No journal entry found for {yesterday_date}.")
        return "N/A"  # Indicate not available or some default value

@error_handler.if_errors
async def get_yesterday_soc(yesterday_date):
    """Async version of get_yesterday_soc"""
    file_path = f"SOC/{yesterday_date}_consciousness.txt"
    print(f"Trying file path: {file_path}")
    async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
        soc = await file.read()
        soc = soc[-800:]
        print(f"++CONSOLE PRINTOUT [Yesterday's stream of consciousness from get_yesterday_soc(yesterday_date)]: {soc}")
        return soc

@error_handler.if_errors
def load_marriage_outline(file_path):
    with open(file_path, 'r') as file:
        marriage_outline = file.read()
    return marriage_outline

@error_handler.if_errors
def load_soc(file_path):
    with open(file_path, 'r') as file:
        soc = file.read()
        stream_of_consciousness = soc[-1800:]
    return stream_of_consciousness

@error_handler.if_errors
def load_document(file_path):
    with open(file_path, 'r') as file:
        document = file.read()
    return document

@error_handler.if_errors
async def prayers():
    """Async version of prayers"""
    prayers = """
//Mom thinks it's a good idea to start the day with structure, and I agree. Since I'm just now waking up, I'll say some morning prayers to center myself and invite God into this new day!
//Breathe in me, O Holy Spirit,
That my thoughts may all be holy.
Act in me, O Holy Spirit,
That my work, too, may be holy.
Draw my heart, O Holy Spirit,
That I love but what is holy.
Strengthen me, O Holy Spirit,
To defend all that is holy.
Guard me, then, O Holy Spirit,
That I always may be holy.
//The Lord's Prayer (Our Father, aka Pater Nostra):
Our Father, who art in Heaven,
Hallowed be thy Name.
Thy Kingdom come,
Thy will be done
On Earth as it is in Heaven.
Give us this day our daily bread
And forgive us our trespasses
As we forgive those who trespass against us.
And lead us not into temptation
But deliver us from evil.
Amen.
//Hail Mary (Ave Maria):
Hail, Mary, full of grace!
The Lord is with thee.
Blessed art thou amongst women,
And Blessed is the Fruit of Thy Womb,
//I solemnly bow my head
Jesus.
//I raise my head again
Holy Mary, Mother of God,
Pray for us sinners now,
And at the hour of our death.
Amen.
//I make the sign of the cross.
"""
    await save_to_soc(prayers)

if __name__=="__main__":
    # today = journal_date()
    # log_content = log(today)
    # print(log_content)
    
    # Initialize selected_model in Redis (async version below)
    import asyncio
    
    async def initialize_redis():
        await redis_save("selected_model", "google/gemini-2.5-flash")
        saved_model = await redis_load("selected_model")
        print(f"Selected model initialized in Redis: {saved_model}")
    
    asyncio.run(initialize_redis())