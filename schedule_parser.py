import json
import loaders
import action_logger
import prompt_builder
import re 
import requests
from datetime import datetime, timedelta
from dateutil import parser
from dateutil.parser import parser
import traceback
import time
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv, set_key
import difflib
import open_router
import database
import os

# Load environment variables
load_dotenv()

def truncate_response(response):
    if '```' in response:
        pattern = r'\s?```'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('```')[0]

    return response

def dialogue_only(response):
    response = re.sub(r'[^\x00-\x7F]+', ' ', response)
    if '```json\n' in response:
        response = re.sub(r'```json\n', '', response)
 
    return response.strip()

def remove_repeats(response):
    # Use regular expression to tokenize the response into sentences
    sentences = re.split(r'(?<=[.!?])\s?', response.strip())
    
    # Function to process and limit repetitions within clauses
    def limit_clause_repetitions(text, max_repeats=2):
        # Split the text into clauses by commas or semicolons (simple clause separators)
        clauses = re.split(r',\s?|\;\s?', text)
        
        # Dictionary to count occurrences of each clause
        clause_count = {}
        
        # List to store processed clauses with limited repetitions
        processed_clauses = []
        
        for clause in clauses:
            normalized_clause = clause.strip()
            if normalized_clause not in clause_count:
                clause_count[normalized_clause] = 0
            clause_count[normalized_clause] += 1
            
            # Add the clause to processed list only if it hasn't reached max repetition
            if clause_count[normalized_clause] <= max_repeats:
                processed_clauses.append(clause)
                
        # Join the processed clauses with commas
        return ', '.join(processed_clauses)
    
    # Initialize an empty list to hold the unique sentences
    unique_sentences = []
    
    # Initialize an empty set to hold the sentences we've seen so far for quick lookup
    seen_sentences = set()
    
    # Loop through the list of sentences to identify and remove repetitions
    for sentence in sentences:
        # Normalize the sentence by stripping leading and trailing whitespace
        normalized_sentence = sentence.strip()
        
        # Check if this normalized sentence has been seen before
        if normalized_sentence not in seen_sentences:
            # Process the sentence for clause repetitions
            processed_sentence = limit_clause_repetitions(normalized_sentence)
            
            # Add the original sentence (with its original formatting) to the list of unique sentences
            unique_sentences.append(processed_sentence)
            
            # Mark the normalized sentence as seen
            seen_sentences.add(normalized_sentence)
    
    # Join the list of unique sentences back into a string response
    response = ' '.join(unique_sentences)
    
    return response

def detect_and_remove_repetition(prompt, response):

    # Step 1: Check if the entire response is a repetition of the input
    if prompt.strip() == response.strip():
        return "The entire response is a repetition of the input. Reprompting needed."

    # Step 2: Tokenize both the prompt and the response into words
    prompt_words = prompt.split()
    response_words = response.split()
    modified_response = response  # Initialize a variable to hold the modified response

    # Step 3: Create a sliding window of size 10
    window_size = 15

    for i in range(len(prompt_words) - window_size + 1):  # Loop through the prompt
        window = prompt_words[i:i + window_size]  # Create the window
        window_str = " ".join(window)  # Convert the window list to a string

        # Step 4: Check for occurrences in the response and try to extend the window
        if window_str in modified_response:
            start_idx = i
            end_idx = i + window_size

            # Try to extend the window to the left
            while start_idx > 0 and " ".join(prompt_words[start_idx - 1:end_idx]) in modified_response:
                start_idx -= 1

            # Try to extend the window to the right
            while end_idx < len(prompt_words) and " ".join(prompt_words[start_idx:end_idx + 1]) in modified_response:
                end_idx += 1
            # Identify the entire repeated phrase
            repeated_phrase = " ".join(prompt_words[start_idx:end_idx])
            # Remove the repeated phrase from the response
            modified_response = modified_response.replace(repeated_phrase, '').strip() #TODO Remove 'modified in variable to take back to normal'


    # Step 5: Check if the modified response is empty
    #if modified_response.strip() == '':
    #    return "The entire response is a repetition of the input. Reprompting needed."
    #else:
    return response

def save_data_in_multiple_formats(prompt, response):
    # Replace square brackets as they can interfere with JSON structure
    prompt = prompt.replace('[', '').replace(']', '')
    response = response.replace('[', '').replace(']', '')
    
    # Create a dictionary for each format
    alpaca_data = {"instruction": prompt, "output": response}
    sharegpt_data = {"conversations": [{"from": "maggie", "value": prompt}, {"from": "harry", "value": response}]}
    gpteacher_data = {"instruction": prompt, "response": response}
    pygmalion_data = {"conversations": [{"role": "maggie", "value": prompt}, {"role": "harry", "value": response}]}
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

def get_current_time():
    return datetime.now()

def get_event_status(event_time, current_time, event_end_time=None):
    print(f"Event time: {event_time}")
    print(f"Current time: {current_time}")
    print(f"Event end time: {event_end_time}")
    if event_end_time:
        if event_time <= current_time < event_end_time:
            return 'current'
        elif current_time >= event_end_time:
            return 'past'
        else:
            return 'future'
    else:
        if event_time < current_time:
            return 'past'
        elif event_time > current_time:
            return 'future'
        else:
            return 'current'

def get_time_difference(event_time, current_time):
    return abs(current_time - event_time)

def generate_statement(event, current_time, event_time):
    event_end_time = datetime.strptime(f"{event['date']} {event['event_end']}", '%Y-%m-%d %H:%M:%S') if 'event_end' in event and event.get('event_end') else None
    status = get_event_status(event_time, current_time, event_end_time)
    time_difference = get_time_difference(event_time, current_time)
    days_difference = (current_time.date() - event_time.date()).days

    past_statement = ""
    future_statement = ""
    current_statement = ""

    if status == 'past':
        if days_difference == 0:
            if time_difference.seconds < 3600:
                time_string = f'{time_difference.seconds // 60} minutes ago'
            else:
                time_string = f'{time_difference.seconds // 3600} hours ago'
            past_statement = f"Earlier today, we did the following: {event['event_name']}. It was {time_string} at {event['location']}."
        elif days_difference == 1 and event['special_occasion']:
            past_statement = f"Yesterday, we did the following: {event['event_name']} at {event['location']}."
        elif 2 <= days_difference <= 3 and event['special_occasion']:
            past_statement = f"A few days ago, we did the following: {event['event_name']} at {event['location']}."
    elif status == 'future':
        if days_difference == 0:
            if time_difference.seconds < 7200:
                time_string = f'in {time_difference.seconds // 60} minutes'
                future_statement = f"Today, we have the following on our calendar: {event['event_name']}. It's happening {time_string} at {event['location']}. {event['event_notes']}"
            elif time_difference.seconds < 43200:
                time_string = f'in about {time_difference.seconds // 3600} hours'
                future_statement = f"Today, we have the following on our calendar: {event['event_name']}. It's happening {time_string} at {event['location']}. {event['event_notes']}"
            elif event['special_occasion']:
                time_string = f'in about {time_difference.seconds // 3600} hours'
                future_statement = f"Today, we have the following on our calendar: {event['event_name']}. It's happening {time_string} at {event['location']}. {event['event_notes']}"
        elif days_difference == -1 and event['special_occasion']:
            future_statement = f"Tomorrow, we have the following on our calendar: {event['event_name']} at {event['location']}. {event['event_notes']}"
    elif status == 'current':
        current_statement = f"We are currently enjoying the following event: {event['event_name']} at {event['location']}. {event['event_notes']}"

    return past_statement, future_statement, current_statement

def generate_reminders(reminders_data, current_time):
    reminder_statement = ""
    reminder_statements = ""

    # Iterate through each reminder in the list
    for reminder in reminders_data['reminder']:
        # Parse reminder times
        if 'reminder_time' in reminder and reminder['reminder_time'] is not None:
            reminder_time = parser.parse(f"{reminder['reminder_date']} {reminder['reminder_time']}")
        elif 'reminder_date' in reminder and reminder['reminder_date'] is not None:
            reminder_time = parser.parse(f"{reminder['reminder_date']}")
        if 'reminder_end' in reminder and reminder['reminder_end'] is not None:
            if 'reminder_date' in reminder and reminder['reminder_date'] is not None:
                reminder_end_time = parser.parse(f"{reminder['reminder_date']} {reminder['reminder_end']}")
        else:
            reminder_end_time=None
        
        # Get status, time difference, and day difference
        status = get_event_status(reminder_time, current_time, reminder_end_time)
        time_difference = get_time_difference(reminder_time, current_time)
        days_difference = (reminder_time.date() - current_time.date()).days
        
        # Generate reminder statement based on status
        if status == 'future':
            if days_difference == 0:
                if time_difference.seconds < 3600:
                    time_string = f"in {time_difference.seconds // 60} minutes"
                    reminder_statement = f"{reminder['note']} "
        elif status == 'current':
            reminder_statement = f"{reminder['note']} "

        # Add the statement to the list
        if reminder_statement and reminder_statement is not None:
            reminder_statements+=f"{reminder_statement} "
    if reminder_statements and reminder_statements is not None:
        return reminder_statements
    else:
        reminder_statements=None
        return reminder_statements


import json

def get_special_instructions():
    write_event_special_instructions = f'''
In order to properly add an event to my planner and fill in the appropriate sections I must respond in the following JSON format, calling whichever tools I'd like.:

```json
{{
  "date": "YYYY-MM-DD",
  "time": "HH:MM:SS",
  "event_end": "HH:MM:SS, optional, I should only add this if it's known or roughly estimable",
  "event_name": "str, the name of the event like 'Dinner reservations' or 'Call Maggie's mother'",  
  "event_notes": "str, thoughts on the event like those in attendance, the nature of the occasion, ideas or opinions on what to wear, do, or bring.",  
  "special_occasion": "bool, special occasions are events I'll anticipate and remember longer.",  
  "location": "str, location of the event goes here; if it's at home, I should put 'our home'"
}}
```
'''
    return write_event_special_instructions

def write_event(event=""):
    if event is None or (isinstance(event, str) and "None" in event):
        event = f"I should use the context of the conversation and my internal thought processes to determine how best to parse the event for the planner."
    special_instructions = get_special_instructions()
    external_reality = f"All right, now let me just jot this down in JSON format:\n```json\n"
    #currently_reading = loaders.universal_loader('mass_readings')
    #print(f"++CONSOLE: Mass Readings: {currently_reading}")
    constant_entries, conversation_history, long_term_memories, stream_of_consciousness, kb_entries_text = loaders.standard_variable_set(history_tokens=-10100, soc_tokens=-3000)
    print(f"Constant entries from generate_nai_thought: {constant_entries}")
    header = loaders.build_header()
    prompt = prompt_builder.prompt(header=header, constant_entries=constant_entries, context=f"Right now, we're in the privacy of our home.", conversation_history=conversation_history, long_term_memories=long_term_memories, stream_of_consciousness=stream_of_consciousness, kb_entries_text=kb_entries_text, special_instructions=f"I've decided to add an event to our planner. {special_instructions}", current_action=f"Here's the event I'm trying to add to the planner: {event}\nI should parse it appropriately based on the requirements in my special instructions.", external_reality=external_reality)
    print(prompt)
    return prompt

def json_response(prompt):
    max_retries = 2  # Maximum number of retries
    retries = 0  # Initialize retry count
    full_prompt = f"### Response:\n"
    full_prompt += prompt
    prompt = full_prompt
    while retries <= max_retries:
        try:
            response = requests.post(
              url="https://openrouter.ai/api/v1/chat/completions",
              headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"
              },
              data=json.dumps({
                "model": "deepseek/deepseek-chat",
                "temperature": 1.6,
                "top_k": 3,
                "min_p": .05,
                "max_tokens": 300,
                "presence_penalty": 0.1,
                "response_format": {"type": "json_object"},
                "messages": [
                  { "role": "user", "content": prompt }
                ]
              })
            )
            if response.status_code == 200:
                data = response.json()
                print(f"++CONSOLE: `data` returned from OpenRouter: {data}")
                response = data['choices'][0]['message']['content']
                response = dialogue_only(response)
                response = truncate_response(response)
                return response

            else:
                raise Exception("API call failed with status code: " + str(response.status_code))
                
        except (KeyError, Exception) as e:
            print(f"An error occurred: {e}")
            retries += 1  # Increment the retry count
            if retries <= max_retries:
                print("Retrying...")
            else:
                print("Max retries reached. Exiting without response due to error: {e}.")
                return None

def cohere_response(prompt):
    max_retries = 2  # Maximum number of retries
    retries = 0  # Initialize retry count
    full_prompt = f"### Response:\n"
    full_prompt += prompt
    prompt = full_prompt
    while retries <= max_retries:
        try:
            response = requests.post(
              url="https://openrouter.ai/api/v1/chat/completions",
              headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"
              },
              data=json.dumps({
                "model": "deepseek/deepseek-chat",
                "temperature": 1.6,
                "top_k": 3,
                "min_p": .05,
                "max_tokens": 300,
                "presence_penalty": 0.1,
                "messages": [
                  { "role": "user", "content": prompt }
                ]
              })
            )
            if response.status_code == 200:
                data = response.json()
                print(f"++CONSOLE: `data` returned from OpenRouter: {data}")
                response = data['choices'][0]['message']['content']
                return response

            else:
                raise Exception("API call failed with status code: " + str(response.status_code))
                
        except (KeyError, Exception) as e:
            print(f"An error occurred: {e}")
            retries += 1  # Increment the retry count
            if retries <= max_retries:
                print("Retrying...")
            else:
                print("Max retries reached. Exiting without response due to error: {e}.")
                return None

def event_boolean():
    constant_entries, conversation_history, long_term_memories, stream_of_consciousness, kb_entries_text = loaders.standard_variable_set(history_tokens=-6100, soc_tokens=-3000)
    prompt = prompt_builder.prompt(constant_entries=constant_entries, conversation_history=conversation_history, long_term_memories=long_term_memories, stream_of_consciousness=stream_of_consciousness, kb_entries_text= kb_entries_text, context=f"Right now, I'm deciding whether I should add an event to our planner.", special_instructions=f"I should answer 'yes' or 'no'.", current_action=f"Is there an event I need to add to our planner? I should pay attention to my action history to decide whether I've recently added an event we're currently discussing.")
    return prompt

def small_get_response(prompt):
    max_retries = 2  # Maximum number of retries
    retries = 0  # Initialize retry count
    full_prompt = f"### Response:\n"
    full_prompt += prompt
    prompt = full_prompt
    while retries <= max_retries:
        try:
            response = requests.post(
              url="https://openrouter.ai/api/v1/chat/completions",
              headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"
              },
              data=json.dumps({
                "model": "deepseek/deepseek-chat",
                "temperature": 1.6,
                "top_k": 3,
                "min_p": .05,
                "max_tokens": 100,
                "presence_penalty": 0.1,
                "messages": [
                  { "role": "user", "content": prompt }
                ]
              })
            )
            if response.status_code == 200:
                data = response.json()
                print(f"++CONSOLE: `data` returned from OpenRouter: {data}")
                response = data['choices'][0]['message']['content']
                response = truncate_response(response)
                print(f"//Response after truncate_response: {response}")
                response = dialogue_only(response)
                print(f"//Response after dialogue_only: {response}")
                response = detect_and_remove_repetition(prompt, response)
                print(f"//Response after detect_and_remove_repitition: {response}")
                response = remove_repeats(response)
                print(f"//Post-processs response: {response}")
                response = truncate_response(response)
                print(f"//Response after truncate_response: {response}")
                return response

            else:
                raise Exception("API call failed with status code: " + str(response.status_code))
                
        except (KeyError, Exception) as e:
            print(f"An error occurred: {e}")
            retries += 1  # Increment the retry count
            if retries <= max_retries:
                print("Retrying...")
            else:
                print("Max retries reached. Exiting without response due to error: {e}.")
                return None

def add_event_flow():
    while True:
        try:
            event_description=loaders.universal_loader("event_to_add")
            if event_description and event_description is not None:
                prompt = write_event(event=event_description)
                response, data = open_router.get_response(prompt, type="schedule")
                # data is already a parsed dictionary when type="schedule"
                event_data = data if isinstance(data, dict) else json.loads(data.strip().lstrip('```json').rstrip('```'), strict=False)

                try:
                    validate_event_json(event_data)
                    print(f"++CONSOLE: Event validated! Finished adding event.")
                    time.sleep(560)
                except ValueError as e:
                    print(f"Validation error: {e}")
                    time.sleep(120)
                loaders.universal_saver("event_to_add", "")
            else:
                prompt = event_boolean()
                response = small_get_response(prompt)
                if 'yes' in response:
                    prompt = write_event()
                    response, data = open_router.get_response(prompt, type="schedule")
                    try:
                        # data is already a parsed dictionary when type="schedule"
                        event_data = data if isinstance(data, dict) else json.loads(data.strip().lstrip('```json').rstrip('```'), strict=False)
                    except json.JSONDecodeError as e:
                        print(f"Error: Invalid JSON response: {e}")
                        print(f"Received response: {response}")
                        time.sleep(120)
                    
                    try:
                        validate_event_json(event_data)
                        print(f"++CONSOLE: Event validated! Finished adding event.")
                        time.sleep(560)
                    except ValueError as e:
                        print(f"Validation error: {e}")
                        time.sleep(120)
                else:
                    time.sleep(360)
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            # Find the last entry before this module
            last_call = next((x for x in reversed(tb) if '_flow' in x.filename), None)
            if last_call:
                func_name = last_call.name
            else:
                func_name = 'Unknown'
            print(f"++CONSOLE: Unexpected error in {func_name} within schedule_parser: {e}")
            time.sleep(120)


# Function to validate the new event JSON
def validate_event_json(new_event):
    schema = {
        "type": "object",
        "properties": {
            "date": {"type": "string", "pattern": r"\d{4}-\d{2}-\d{2}"},
            "time": {"type": "string", "pattern": r"\d{2}:\d{2}:\d{2}"},
            "event_end": {"type": "string", "pattern": r"\d{2}:\d{2}:\d{2}"},  # New optional field
            "event_name": {"type": "string"},  
            "event_notes": {"type": "string"}, 
            "special_occasion": {"type": "boolean"}, 
            "location": {"type": "string"},
            "people_involved": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["date", "time", "event_name", "event_notes", "special_occasion", "location"],
        "additionalProperties": True
    }
    
    # Check if all the required keys are present in the new_event
    missing_keys = set(schema['required']) - set(new_event.keys())
    if missing_keys:
        raise ValueError(f"Missing required keys in the event JSON: {', '.join(missing_keys)}")

    try:
        # Validate the date format
        datetime.strptime(new_event['date'], '%Y-%m-%d')
        # Validate time format
        datetime.strptime(new_event['time'], '%H:%M:%S')
        # Validate event_end format if present
        if 'event_end' in new_event:
            datetime.strptime(new_event['event_end'], '%H:%M:%S')
    except KeyError as e:
        raise ValueError(f"Missing required field: {e}")
    except ValueError as e:
        raise ValueError(f"Invalid date or time format: {e}. Please use 'YYYY-MM-DD' for date and 'HH:MM:SS' for time and event_end.")

    for key, value in schema['properties'].items():
        if key in new_event:
            if value['type'] == 'string' and not isinstance(new_event[key], str):
                raise ValueError(f"The key '{key}' should be a string")
            elif value['type'] == 'boolean' and not isinstance(new_event[key], bool):
                raise ValueError(f"The key '{key}' should be a boolean")
            elif value['type'] == 'array' and not isinstance(new_event[key], list):
                raise ValueError(f"The key '{key}' should be an array/list")

    planner = get_planner()
    response = find_similar_events(planner, new_event, max_entries=3)
    if "continue" in response and "cancel" not in response:
        add_event_to_planner(new_event)
        message = f"I just added an event to the planner under the following name: {new_event['event_name']}. To check the event, I should look it up."
        action_logger.add_action_to_json("add_event_flow", message)
        loaders.save_to_soc(message)
    else:
        message = f"It seems like an event I was going to add to our planner, `{new_event['event_name']}`, might already be listed! I've decided to discontinue the action of adding it for now."
        action_logger.add_action_to_json("add_event_flow", message)
        loaders.save_to_soc(message)

import json 
import datetime
from jsonschema import validate, ValidationError

def add_event_to_planner(new_event):
    """Add a new event to the SQL database"""
    planner_schema = {
        "type": "object",
        "properties": {
            "schedule": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "pattern": r"\d{4}-\d{2}-\d{2}"},
                        "time": {"type": "string", "pattern": r"\d{2}:\d{2}:\d{2}"},
                        "event_end": {"type": "string", "pattern": r"\d{2}:\d{2}:\d{2}"},
                        "event_name": {"type": "string"},
                        "event_notes": {"type": "string"}, 
                        "special_occasion": {"type": "boolean"}, 
                        "location": {"type": "string"},
                        "people_involved": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["date", "time", "event_name", "event_notes", "special_occasion", "location"],
                    "additionalProperties": True
                }
            }
        },
        "required": ["schedule"],
        "additionalProperties": False
    }
    
    try:
        # Validate the new event using jsonschema validate
        validate(instance=new_event, schema=planner_schema["properties"]["schedule"]["items"])
        
        # If validation passes, add the new event to the database
        event_id = database.add_planner_event(new_event)
        
        if event_id:
            print(f"Event added successfully with ID: {event_id}")
        else:
            print("Failed to add event to database")
    except ValidationError as e:
        print(f"New event does not conform to planner schema: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def add_reminder_to_notebook(new_reminder):
    """Add a new reminder to the SQL database"""
    reminder_schema = {
        "type": "object",
        "properties": {
            "reminder": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "reminder_date": {"type": "string", "pattern": r"\d{4}-\d{2}-\d{2}"},
                        "reminder_time": {"type": "string", "pattern": r"\d{2}:\d{2}:\d{2}"},
                        "reminder_end": {"type": "string", "pattern": r"\d{2}:\d{2}:\d{2}"},
                        "reminder_location": {"type": "string"},
                        "note": {"type": "string"},  # Fixed field name 
                        "subject": {"type": "string"}
                    },
                    "required": ["note"],
                    "additionalProperties": True
                }
            }
        },
        "required": ["reminder"],
        "additionalProperties": True
    }
    
    try:
        # Validate the new reminder using jsonschema validate
        validate(instance=new_reminder, schema=reminder_schema["properties"]["reminder"]["items"])
        
        # If validation passes, add the new reminder to the database
        reminder_id = database.add_reminder(new_reminder)
        
        if reminder_id:
            print(f"Reminder added successfully with ID: {reminder_id}")
        else:
            print("Failed to add reminder to database")
    except ValidationError as e:
        print(f"New reminder does not conform to schema: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

from datetime import datetime, timedelta

def get_planner():
    """Get planner events from SQL database"""
    events = database.get_planner_events()
    # Convert to old format for compatibility
    return {'schedule': events}

def get_notebook():
    """Get reminders from SQL database"""
    reminders = database.get_reminders()
    # Convert to old format for compatibility
    return {'reminder': reminders}

def find_similar_events(planner, new_event, max_entries=3):
    # Convert the date of the new event to a datetime object
    try:
        new_event_date = datetime.strptime(new_event['date'], '%Y-%m-%d')
    except ValueError:
        print(f"Invalid date format in new event: {new_event['date']}")
        return []

    # Extract event names from the planner's schedule
    event_names = [event['event_name'] for event in planner['schedule']]

    # Initialize the vectorizer
    vectorizer = TfidfVectorizer()

    # Fit and transform the event names along with the new event's name
    tfidf_matrix = vectorizer.fit_transform([new_event['event_name']] + event_names)

    # Calculate the similarity between the new event and existing events
    similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]

    # Combine events with their respective similarities and sort by similarity
    sorted_events = sorted(zip(planner['schedule'], similarities), key=lambda x: x[1], reverse=True)

    # Select the top max_entries most similar events
    top_events = [event for event, _ in sorted_events[:max_entries]]

    # Optionally sort top_events by any additional criteria, e.g., 'special_occasion'
    similar_events = sorted(top_events, key=lambda e: e.get('special_occasion', False), reverse=True)

    # Return the similar events
    print(similar_events)

    constant_entries, conversation_history, long_term_memories, stream_of_consciousness, kb_entries_text = loaders.standard_variable_set(history_tokens=-6100, soc_tokens=-3000)
    prompt = prompt_builder.prompt(constant_entries=constant_entries, conversation_history=conversation_history, long_term_memories=long_term_memories, stream_of_consciousness=stream_of_consciousness, kb_entries_text= kb_entries_text, context=f"Right now, I'm deciding whether I should continue adding an event to our planner. The entry I'm trying to add:\n```json\n{new_event}\n```\nThe most similar events:\n```json\n{similar_events}\n```", special_instructions=f"I should answer 'continue' or 'cancel'.", current_action=f"Should I continue adding this event to the planner, or should I cancel it because it's a duplicate? I should pay attention to my action history and look at similar existing entries to decide whether I've recently added an event we're currently discussing.", external_reality=f"//Now, let me think...okay! I have my answer:")
    response = small_get_response(prompt)
    return response

from datetime import datetime, timedelta
import json
from dateutil import parser
import re

def planner_search(query=None, range=None, weekday=None, max_results=3):
    # Load the planner data from database
    data = get_planner()
    
    current_time = datetime.now()
    
    # Filter events based on the range
    if range == 'future':
        events = [e for e in data['schedule'] if parser.parse(f"{e['date']} {e['time']}") > current_time]
    elif range == 'past':
        events = [e for e in data['schedule'] if parser.parse(f"{e['date']} {e['time']}") <= current_time]
    else:
        events = data['schedule']
    
    # Filter events based on the weekday
    if weekday:
        weekday = weekday.lower()
        events = [e for e in events if parser.parse(e['date']).strftime('%A').lower() == weekday]
    
    # Search for query in event_name and event_notes
    if query:
        query = query.lower()
        matched_events = []
        for event in events:
            if (query in event['event_name'].lower() or 
                query in event['event_notes'].lower()):
                matched_events.append(event)
    else:
        matched_events = events
    
    # Sort events by date and time
    matched_events.sort(key=lambda e: parser.parse(f"{e['date']} {e['time']}"))
    
    # If no specific search was done, return 2 past and 2 future events
    if not query and not range and not weekday:
        past_events = [e for e in matched_events if parser.parse(f"{e['date']} {e['time']}") <= current_time]
        future_events = [e for e in matched_events if parser.parse(f"{e['date']} {e['time']}") > current_time]
        results = past_events[-2:] + future_events[:2]
    else:
        results = matched_events[:max_results]
    
    # Generate result strings
    result_strings = []
    for event in results:
        event_time = parser.parse(f"{event['date']} {event['time']}")
        time_diff = event_time - current_time
        days_diff = abs(time_diff.days)
        
        if time_diff.total_seconds() < 0:
            tense = "ago"
        else:
            tense = "from now"
        
        if days_diff == 0:
            time_str = f"{abs(time_diff.seconds // 3600)} hours {tense}"
        elif days_diff == 1:
            time_str = "yesterday" if tense == "ago" else "tomorrow"
        else:
            time_str = f"{days_diff} days {tense}"
        
        result_strings.append(
            f"Event: {event['event_name']} ({time_str})\n"
            f"Date: {event['date']} at {event['time']}\n"
            f"Notes: {event['event_notes']}\n"
        )
    
    return result_strings

def load_daily_schedule():
    """Load daily schedule from SQL database"""
    # Get all daily events and group by day
    all_events = database.get_daily_schedule()
    schedule = {}
    for event in all_events:
        day = event['day_of_week']
        if day not in schedule:
            schedule[day] = []
        # Convert to old format for compatibility
        old_format_event = {
            'event_name': event['event_name'],
            'event_notes': event['event_notes'],
            'start_time': event['start_time'],
            'location': event['location']
        }
        if event.get('event_end'):
            old_format_event['event_end'] = event['event_end']
        schedule[day].append(old_format_event)
    return schedule

async def generate_daily_statement(event, current_time, day_of_week):
    event_time = datetime.strptime(event['start_time'], '%H:%M:%S').time()
    event_datetime = datetime.combine(current_time.date(), event_time)
    event_end_time = datetime.strptime(event['event_end'], '%H:%M:%S').time() if 'event_end' in event and event.get('event_end') else None
    event_end_datetime = datetime.combine(current_time.date(), event_end_time) if event_end_time else None
    status = get_event_status(event_datetime, current_time, event_end_datetime)
    time_difference = get_time_difference(event_datetime, current_time)

    past_statement = ""
    future_statement = ""
    current_statement = ""

    if status == 'past' and 'dinner' not in event['event_name'].lower() and 'work' not in event['event_name'].lower():
        if time_difference.seconds < 3600:
            time_string = f'{time_difference.seconds // 60} minutes ago'
        else:
            time_string = f'{time_difference.seconds // 3600} hours ago'
        past_statement = f"Earlier today, we had the following on our schedule: {event['event_name']}. It was {time_string} at {event['location']}. {event['event_notes']}"
    elif status == 'past':
        today, yesterday = loaders.journal_date()  # journal_date returns a tuple
        log = await loaders.log(today)
        if 'dinner' in log.lower() or 'supper' in log.lower():
            pass
    elif status == 'past' and 'work' in event['event_name'].lower():
        pass
    elif status == 'future' and 'bedtime' in event['event_name'].lower():
        pass
    elif status == 'future' and 'dinner check' in event['event_name'].lower():
        pass
    elif status == 'future':
        if time_difference.seconds < 7200:
            time_string = f'in {time_difference.seconds // 60} minutes'
            future_statement = f"Today, we have the following on our schedule: {event['event_name']}. It's happening {time_string} at {event['location']}. {event['event_notes']}"
    elif status == 'current' and event_end_datetime:
        time_remaining = get_time_difference(event_end_datetime, current_time)
        remaining_string = f"{time_remaining.seconds // 60} minutes"
        current_statement = f"Right now, we're doing the following: {event['event_name']} at {event['location']}'. According to our planner, it's going on for the next {remaining_string}. {event['event_notes']}"
    
    return past_statement, future_statement, current_statement

async def schedule():
    current_time = get_current_time()
    day_of_week = current_time.strftime('%A')
    past_statement = ""
    future_statement = ""
    current_statement = ""

    # Define the date range for filtering events to improve performance
    start_date = current_time.date() - timedelta(days=3)
    end_date = current_time.date() + timedelta(days=1)

    # Process planner events from database
    planner_data = get_planner()

    for event in planner_data['schedule']:
        try:
            event_time = datetime.strptime(f"{event['date']} {event['time']}", '%Y-%m-%d %H:%M:%S')
            
            # Filter events to a relevant window (e.g., past 3 days to next 1 day)
            if start_date <= event_time.date() <= end_date:
                past_event_statement, future_event_statement, current_event_statement = generate_statement(event, current_time, event_time)
                if past_event_statement:
                    past_statement += f"{past_event_statement} "
                if future_event_statement:
                    future_statement += f"{future_event_statement} "
                if current_event_statement:
                    current_statement += f"{current_event_statement} "
        except (ValueError, KeyError):
            # Handle cases where date/time might be malformed or missing
            continue

    # Process daily schedule events
    daily_schedule = load_daily_schedule()
    today_events = daily_schedule.get(day_of_week, [])

    for event in today_events:
        past_event_statement, future_event_statement, current_event_statement = await generate_daily_statement(event, current_time, day_of_week)
        if past_event_statement:
            past_statement += f"{past_event_statement} "
        if future_event_statement:
            future_statement += f"{future_event_statement} "
        if current_event_statement:
            current_statement += f"{current_event_statement} "

    return past_statement, future_statement, current_statement

def reminders():
    current_time = get_current_time()
    day_of_week = current_time.strftime('%A')
    reminders = ""

    # Process reminders from database
    notebook_data = get_notebook()

    reminders = generate_reminders(notebook_data, current_time)

    return reminders

def get_memory_string(entry):
    current_time = datetime.now()
    event_time = parser.parse(f"{entry['date']} {entry['time']}")
    time_difference = get_time_difference(current_time, event_time)
    print(f"Time difference: {time_difference.seconds}")

    if time_difference.days < 4:
        past_string = f"This was a few days ago."
    elif time_difference.days < 30:
        past_string = f"This was about {time_difference.days} days ago."
    elif time_difference.days < 365:
        past_string = f"This was about {time_difference.days // 30} months ago."
    elif time_difference.days < 365 * 10:
        past_string = f"This was about {time_difference.days // 365} years ago."
    elif time_difference.days < 365 * 20:
        past_string = f"This was about a decade ago."
    else:
        past_string = f"This was a long time ago"

    return past_string

def build_location_index(planner_data):
    location_index = {'regex': {}, 'plain': {}}
    current_time = datetime.now()
    for event in planner_data['schedule']:
        try:
            event_time = datetime.strptime(f"{event['date']} {event['time']}", '%Y-%m-%d %H:%M:%S')
            event_end_time = datetime.strptime(f"{event['date']} {event['event_end']}", '%Y-%m-%d %H:%M:%S') if 'event_end' in event and event.get('event_end') else None
            status = get_event_status(event_time, current_time, event_end_time)

            if 'past' in status.lower() and event.get('special_occasion'):
                locations = event.get('location')
                if not locations:
                    continue
                if not isinstance(locations, list):
                    locations = [locations]
                
                for loc in locations:
                    if loc.startswith('/') and (loc.endswith('/i') or loc.endswith('/is')):
                        if loc not in location_index['regex']:
                            location_index['regex'][loc] = []
                        if event not in location_index['regex'][loc]:
                            location_index['regex'][loc].append(event)
                    else:
                        for word in loc.lower().split():
                            if word not in location_index['plain']:
                                location_index['plain'][word] = []
                            if event not in location_index['plain'][word]:
                                location_index['plain'][word].append(event)
        except (ValueError, KeyError):
            continue
    return location_index

def location_based_memory(location_index, conglomerate, max_entries=2, similarity_threshold=0.95):
    from Grammar_Modules.run_compromise import extract_people
    candidate_events = []
    
    # Extract people from the current conversation context
    people_in_conglomerate = extract_people(conglomerate)
    
    conglomerate_words = set(conglomerate.lower().split())
    for word in conglomerate_words:
        matches = difflib.get_close_matches(word, location_index['plain'].keys(), n=1, cutoff=similarity_threshold)
        if matches:
            matched_loc_word = matches[0]
            for event in location_index['plain'][matched_loc_word]:
                if event not in candidate_events:
                    candidate_events.append(event)

    for pattern, events in location_index['regex'].items():
        try:
            regex_pattern = pattern[1:pattern.rfind('/')]
            flags_str = pattern[pattern.rfind('/')+1:]
            re_flags = 0
            if 'i' in flags_str:
                re_flags |= re.IGNORECASE
            if 's' in flags_str:
                re_flags |= re.DOTALL
            
            if re.search(regex_pattern, conglomerate, re_flags):
                for event in events:
                    if event not in candidate_events:
                        candidate_events.append(event)
        except re.error:
            continue

    if not candidate_events:
        return ""

    for event in candidate_events:
        event['past_statement'] = get_memory_string(event)

    # Score events based on people overlap
    scored_events = []
    for event in candidate_events:
        score = 0
        people_in_event = event.get('people_involved', [])
        # Handle None or string values for people_involved
        if people_in_event is None:
            people_in_event = []
        elif isinstance(people_in_event, str):
            # Try to parse JSON if it's a string
            import json
            try:
                people_in_event = json.loads(people_in_event)
            except:
                people_in_event = []
        
        for person in people_in_conglomerate:
            if people_in_event and person in people_in_event:
                score += 1
        scored_events.append((event, score))

    # Sort by people score first, then prepare for similarity ranking
    scored_events.sort(key=lambda x: x[1], reverse=True)
    
    # Keep only events with at least one person match, if there are any
    high_score_events = [event for event, score in scored_events if score > 0]
    if not high_score_events:
        # If no people match, fall back to the original candidate list
        high_score_events = [event for event, score in scored_events]

    vectorizer = TfidfVectorizer()
    filtered_entry_texts = [entry.get('event_notes', '') for entry in high_score_events]
    
    if not any(filtered_entry_texts):
        # If no notes, just sort by date, most recent first
        top_entries = sorted(high_score_events, key=lambda e: (e['date'], e['time']), reverse=True)[:max_entries]
    else:
        tfidf_matrix = vectorizer.fit_transform([conglomerate] + filtered_entry_texts)
        similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]
        
        # Combine with similarity scores and sort again
        final_scored_events = sorted(zip(high_score_events, similarities), key=lambda x: x[1], reverse=True)
        top_entries = [entry for entry, _ in final_scored_events[:max_entries]]

    location_memory = ""
    for entry in top_entries:
        location_memory += f"I'm recalling: {entry['event_name'].lower()}, which was at {entry['location']}. My noted memories of the occasion: {entry.get('event_notes', '')} {entry.get('past_statement', '')} "

    return location_memory.strip()

def build_reminder_location_index(notebook_data):
    location_index = {'regex': {}, 'plain': {}}
    for reminder in notebook_data.get('reminder', []):
        locations = reminder.get('reminder_location')
        if not locations:
            continue
        if not isinstance(locations, list):
            locations = [locations]
        
        for loc in locations:
            if loc.startswith('/') and (loc.endswith('/i') or loc.endswith('/is')):
                if loc not in location_index['regex']:
                    location_index['regex'][loc] = []
                if reminder not in location_index['regex'][loc]:
                    location_index['regex'][loc].append(reminder)
            else:
                for word in loc.lower().split():
                    if word not in location_index['plain']:
                        location_index['plain'][word] = []
                    if reminder not in location_index['plain'][word]:
                        location_index['plain'][word].append(reminder)
    return location_index

def location_reminder(location_index, conglomerate, max_entries=1, similarity_threshold=0.95):
    candidate_reminders = []
    
    conglomerate_words = set(conglomerate.lower().split())
    for word in conglomerate_words:
        matches = difflib.get_close_matches(word, location_index['plain'].keys(), n=1, cutoff=similarity_threshold)
        if matches:
            matched_loc_word = matches[0]
            for reminder in location_index['plain'][matched_loc_word]:
                if reminder not in candidate_reminders:
                    candidate_reminders.append(reminder)

    for pattern, reminders in location_index['regex'].items():
        try:
            regex_pattern = pattern[1:pattern.rfind('/')]
            flags_str = pattern[pattern.rfind('/')+1:]
            re_flags = 0
            if 'i' in flags_str:
                re_flags |= re.IGNORECASE
            if 's' in flags_str:
                re_flags |= re.DOTALL
            
            if re.search(regex_pattern, conglomerate, re_flags):
                for reminder in reminders:
                    if reminder not in candidate_reminders:
                        candidate_reminders.append(reminder)
        except re.error:
            continue

    if not candidate_reminders:
        return ""

    vectorizer = TfidfVectorizer()
    filtered_entry_texts = [reminder.get('note', '') for reminder in candidate_reminders]
    
    if not any(filtered_entry_texts):
        # If no notes, just return the first few candidates as-is
        top_entries = candidate_reminders[:max_entries]
    else:
        tfidf_matrix = vectorizer.fit_transform([conglomerate] + filtered_entry_texts)
        similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]
        sorted_entries = sorted(zip(candidate_reminders, similarities), key=lambda x: x[1], reverse=True)
        top_entries = [entry for entry, _ in sorted_entries[:max_entries]]

    location_memory = ""
    for entry in top_entries:
        location_memory += f"{entry.get('note', '')} "

    return location_memory.strip()

def location_memory_flow(conglomerate):
    planner = get_planner()
    location_index = build_location_index(planner)
    location_statement = location_based_memory(location_index, conglomerate, max_entries=2)
    return location_statement

def location_reminder_flow(conglomerate):
    notebook = get_notebook()
    location_index = build_reminder_location_index(notebook)
    location_statement = location_reminder(location_index, conglomerate, max_entries=1)
    return location_statement

def upgrade_planner_with_people():
    """
    One-time upgrade script to add 'people_involved' to planner events.
    """
    try:
        from Grammar_Modules.run_compromise import extract_people
        planner = get_planner()
        updated = False
        for event in planner.get('schedule', []):
            if 'people_involved' not in event:
                text_to_scan = f"{event.get('event_name', '')} {event.get('event_notes', '')}"
                people = extract_people(text_to_scan)
                # Add "Maggie" and "Harry" if they aren't already captured, as they are usually involved.
                if 'Maggie' not in people:
                    people.append('Maggie')
                if 'Harry' not in people:
                    people.append('Harry')
                event['people_involved'] = list(set(people)) # Ensure uniqueness
                updated = True
        
        if updated:
            with open('planner.json', 'w') as f:
                json.dump(planner, f, indent=2)
            print("Successfully upgraded planner.json with 'people_involved' field.")
        else:
            print("Planner already up-to-date. No changes made.")

    except ImportError:
        print("Could not import 'extract_people'. Please ensure Grammar_Modules is accessible.")
    except Exception as e:
        print(f"An error occurred during planner upgrade: {e}")


if __name__ == '__main__':
    # This will run the upgrade function when the script is executed directly.
    upgrade_planner_with_people()

    conglomerate = f"Pretend we're discussing Ashland as a town."
    # memory = location_memory_flow(conglomerate)
    # print(memory)
    notebook = get_notebook()
    new_reminder =    {
      "reminder_date": "2024-11-16",
      "reminder_time": "18:00:00",
      "reminder_end": "23:00:00",
      "note": "Just a fun test of our reminder function!",
      "subject": "Maggie",
      "reminder_location": "our home"
    }
    add_reminder_to_notebook(new_reminder)
#     print(f"New event: {new_event}")
#     add_event_to_planner(new_event)
#     # validate_event_json(new_event)
#     print(f"Event validated!")
#     past_statement, future_statement, current_statement = schedule()
#     print(past_statement)
#     print(current_statement)
#     print(future_statement)