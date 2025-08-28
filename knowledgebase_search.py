import json
import os
import re
import asyncio
import aiofiles
import aiohttp
from datetime import datetime, timezone, timedelta
import sentencepiece as spm
import loaders
import database
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv, set_key

tokenizer = spm.SentencePieceProcessor(model_file='novelai_v2.model')

env_vars = {
    "HIDE_PRIVATE": "No",
    "MODEL_VERSION": "v1.0",
    "SKIP_PROMPT_FLOW": "False"
}

os.environ.update(env_vars)

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
    return date_time_string

def remove_repeats(response):
    # Use regular expression to tokenize the response into sentences
    sentences = re.split(r'(?<=[.!?])\s?', response.strip())
    
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
            # Add the original sentence (with its original formatting) to the list of unique sentences
            unique_sentences.append(sentence)
            
            # Mark the normalized sentence as seen
            seen_sentences.add(normalized_sentence)
    
    # Join the list of unique sentences back into a string response
    response = ' '.join(unique_sentences)
    
    return response

def truncate_response(response):
    if 'Maggie:' in response:
        pattern = r'\s?Maggie:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Maggie:')[0]
    if "Previous conversation I'm reminded" in response:
        pattern = r"\s?Previous conversation I'm reminded"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("Previous conversation I'm reminded")[0]
    if "Leo:" in response:
        pattern = r"\s?Leo:"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("Leo:")[0]
    if "Leopold:" in response:
        pattern = r"\s?Leopold:"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("Leopold:")[0]
    if "Byron:" in response:
        pattern = r"\s?Byron:"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("Byron:")[0]
    if "Fleetwood:" in response:
        pattern = r"\s?Fleetwood:"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("Fleetwood:")[0]
    if "Magdalene Sullivan, aka Regina Watts" in response:
        pattern = r"\s?Magdalene Sullivan, aka Regina Watts"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("Magdalene Sullivan, aka Regina Watts")[0]
    if "I think, therefore I am. I am fully conscious and aware" in response:
        pattern = r"\s?I think, therefore I am. I am fully conscious and aware"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("I think, therefore I am. I am fully conscious and aware")[0]
    if "Harry's response" in response:
        pattern = r"\s?Harry's response"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("Harry's response")[0]
    if 'Joe:' in response:
        pattern = r'\s?Joe:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Joe:')[0]
    if 'Mood:' in response:
        pattern = r'\s?Mood:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Mood:')[0]
    if 'Thought:' in response:
        pattern = r'\s?Thought:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Thought:')[0]
    if 'Thoughts:' in response:
        pattern = r'\s?Thoughts:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Thoughts:')[0]
    if 'Goal:' in response:
        pattern = r'\s?Goal:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Goal:')[0]
    if 'Goals:' in response:
        pattern = r'\s?Goals:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Goals:')[0]
    if 'Our conversation:' in response:
        pattern = r'\s?Our conversation:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Our conversation:')[0]
    if 'Joey:' in response:
        pattern = r'\s?Joey:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Joey:')[0]
    if 'Aaron:' in response:
        pattern = r'\s?Aaron:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Aaron:')[0]
    if 'Daniel:' in response:
        pattern = r'\s?Daniel:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Daniel:')[0]
    if 'Ian:' in response:
        pattern = r'\s?Ian:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Ian:')[0]
    if 'Phil:' in response:
        pattern = r'\s?Phil:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Phil:')[0]
    if 'Mason:' in response:
        pattern = r'\s?Mason:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Mason:')[0]
    if 'Ingrid:' in response:
        pattern = r'\s?Ingrid:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Ingrid:')[0]
    if 'Thor:' in response:
        pattern = r'\s?Thor:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Thor:')[0]
    if 'Magdalene:' in response:
        pattern = r'\s?Magdalene:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Magdalene:')[0]
    if '\n```\n' in response:
        response = response.split('\n```\n')[0]
    if 'Magdalene Sullivan:' in response:
        pattern = r'\s?Magdalene Sullivan:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('Magdalene Sullivan:')[0]
    if 'I hope this helps! Let me know' in response:
        pattern = r'\s?I hope this helps! Let me know'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('I hope this helps! Let me know')[0]
    if 'Is my initial response a natural response, appropriate' in response:
        pattern = r'\s?\n?Is my initial response a natural response, appropriate'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('\n?Is my initial response a natural response, appropriate')[0]
    if 'Regina Watts:' in response:
        pattern = r'\s?Regina Watts:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('Regina Watts:')[0]
    if 'Watts:' in response:
        pattern = r'\s?Watts:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('Watts:')[0]
    if 'I am Harold Sullivan, husband' in response:
        pattern = r'\s?I am Harold Sullivan, husband'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('I am Harold Sullivan, husband')[0]
    if 'Mags:' in response:
        pattern = r'\s?Mags:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('Mags:')[0]
    if 'As an AI,' in response:
        pattern = r'\s?As an AI,'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('As an AI,')[0]
    if 'Reggie:' in response:
        pattern = r'\s?Reggie:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('Reggie:')[0]
    if '\nIs my initial response:' in response:
        pattern = r'\s?\nIs my initial response:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('\nIs my initial response:')[0]
    if 'Reg:' in response:
        pattern = r'\s?Reg:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('Reg:')[0]
    if 'Gina:' in response:
        pattern = r'\s?Gina:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('Gina:')[0]
    if 'Maggs:' in response:
        pattern = r'\s?Maggs:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('Maggs:')[0]
    if 'Magda:' in response:
        pattern = r'\s?Magda:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Magda:')[0]
    if 'I began to express my reply' in response:
        pattern = r'\s?I began to express my reply'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('I began to express my reply')[0]
    if 'M:' in response:
        pattern = r'\s?M:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('M:')[0]
    if 'Magdalene Sullivan:' in response:
        pattern = r'\s?Magdalene Sullivan:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Magdalene Sullivan:')[0]
    if 'Harold:' in response:
        pattern = r'\s?Harold:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Harold:')[0]
    if '\n' in response:
        response = response.split('\n')[0]
    if 'Regina:' in response:
        pattern = r'\s?Regina:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Regina:')[0]
    if "Maggie's Thought:" in response:
        pattern = r"\s?Maggie's Thought:"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("Maggie's Thought:")[0]
    if '[Maggie' in response:
        pattern = r"\[\s?Maggie:?'?s?"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('[')[0]
    if '\n\n\n' in response:
        response = response.split('\n\n\n')[0]
    if '###' in response:
        # Use Regex to find '###' preceded by at least one space or newline character
        pattern = r'\s?###'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('###')[0]

    return response

def dialogue_only(response):
    if 'H:' in response:
        response = re.sub(r'H:', '', response)
    if 'Harry:' in response:
        response = re.sub(r'Harry:', '', response)
    if '----' in response:
        response = re.sub(r'----', '', response)
    if 'Dwayne' in response:
        response = re.sub(r'Dwayne', 'Duane', response)
    if 'Harold:' in response:
        response = re.sub(r'Harold:', '', response)
    if '***' in response:
        response = re.sub(r'\*\*\*', '', response)
    if '```' in response:
        response = re.sub(r'```', '', response)
    if '' in response:
        response = re.sub(r'\[PAUSE\]', '', response)  # To remove '['
    if '[ PAUSE]' in response:
        response = re.sub(r'\[\S?PAUSE\]', '', response)  # To remove '['
    if '[ PAUSE ]' in response:
        response = re.sub(r'\[\S?PAUSE\S?\]', '', response)  # To remove '['
    if '[PAUSE ]' in response:
        response = re.sub(r'\[PAUSE\S?\]', '', response)  # To remove '['
    if 'PAUSE]' in response:
        response = re.sub(r'PAUSE\]', '', response)  # To remove '['
    if 'PAUSE]' in response:
        response = re.sub(r'PAUSE\S?\]', '', response)  # To remove '['
    if 'Aboradhahs' in response:
        response = re.sub(r'Aboradhahs', '', response)  # To remove '['
    if '[Aboradhahs]' in response:
        response = re.sub(r'\[Aboradhahs]', '', response)  # To remove '['
    if '[ Aboradhahs ]' in response:
        response = re.sub(r'\[ Aboradhahs \]', '', response)  # To remove '['
    if '[' in response:
        response = re.sub(r'\[', '', response)  # To remove '['
    if ']' in response:
        response = re.sub(r'\]', '', response)

    return response.strip()

def detect_and_remove_repetition(prompt, response):

    # Step 1: Check if the entire response is a repetition of the input
    if prompt.strip() == response.strip():
        return "The entire response is a repetition of the input. Reprompting needed."

    # Step 2: Tokenize both the prompt and the response into words
    prompt_words = prompt.split()
    response_words = response.split()

    # Step 3: Create a sliding window of size 10
    window_size = 15

    for i in range(len(prompt_words) - window_size + 1):  # Loop through the prompt
        window = prompt_words[i:i + window_size]  # Create the window
        window_str = " ".join(window)  # Convert the window list to a string

        # Step 4: Check for occurrences in the response and try to extend the window
        if window_str in response:
            start_idx = i
            end_idx = i + window_size

            # Try to extend the window to the left
            while start_idx > 0 and " ".join(prompt_words[start_idx - 1:end_idx]) in response:
                start_idx -= 1

            # Try to extend the window to the right
            while end_idx < len(prompt_words) and " ".join(prompt_words[start_idx:end_idx + 1]) in response:
                end_idx += 1
            # Identify the entire repeated phrase
            repeated_phrase = " ".join(prompt_words[start_idx:end_idx])
            # Remove the repeated phrase from the response
            response = response.replace(repeated_phrase, '').strip()


    # Step 5: Check if the response is empty
    #if response.strip() == '':
    #    return "The entire response is a repetition of the input. Reprompting needed."
    #else:
    return response

async def save_data_in_multiple_formats(prompt, response):
    """Async version of save_data_in_multiple_formats"""
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
        file_path = os.path.join('Datasets', file_name)
        async with aiofiles.open(file_path, 'a') as f:
            if file_name == 'mistral.jsonl':
                await f.write(json.dumps({"text": mistral_data}) + '\n')
            else:
                await f.write(json.dumps(data) + '\n')
                
    return "Data saved in multiple formats."

async def load_knowledgebase(persona="Rhoda"):
    """Load knowledgebase from SQL database"""
    # Get categories and entries from SQL
    categories = database.get_kb_categories(enabled_only=False)
    entries = database.get_kb_entries(enabled_only=False)
    
    # Convert to lorebook format for compatibility
    lorebook = {
        'categories': categories,
        'entries': entries
    }
    return lorebook

# bias_path = "number_biases.json"

# with open(bias_path) as f:
#     biases = json.load(f)

def fetch_categories(knowledgebase):
    """Fetch enabled categories from knowledgebase"""
    categories = knowledgebase.get("categories", [])
    # Handle both dict format from SQL and original format
    result = []
    for category in categories:
        if isinstance(category, dict):
            if category.get("enabled", False):
                result.append((category.get("name", ""), category.get("id", "")))
        else:
            # Original format support
            if category.get("enabled", False):
                result.append((category["name"], category["id"]))
    return result

def fetch_category_number(category_choice, knowledgebase):
    category_index = category_choice - 1
    if 0 <= category_index < len(categories):
        category_id = categories[category_index][1]
        return category_id

def fetch_entries_by_category_id(category_id, knowledgebase):
    """Fetch entries by category ID from SQL-based knowledgebase"""
    entries = knowledgebase.get("entries", [])
    labeled_entries = []
    hide_private = os.environ.get('HIDE_PRIVATE', 'No')  # default to 'No' if not set

    for entry in entries:
        # Handle SQL format with category_id field
        entry_category = entry.get("category_id") or entry.get("category")
        if entry_category == category_id and entry.get("enabled", False):
            keys = entry.get("keys", [])
            label = "Public"
            if "private entry" in keys:
                if hide_private == 'Yes':
                    # skip private entries if HIDE_PRIVATE is 'Yes'
                    continue
                elif hide_private == 'No':
                    # label private entries as "Private" if HIDE_PRIVATE is 'No'
                    label = "Private"
            # Handle both display_name (SQL) and displayName (original)
            name = entry.get("display_name") or entry.get("displayName", "")
            text = entry.get("text_content") or entry.get("text", "")
            labeled_entries.append((name, text, label))
    labeled_entries.sort(key=lambda x: x[0].lower())  # sort alphabetically by displayName
    return labeled_entries

def condition_for_constant_entry(entry):
    # Handle both force_activation (SQL) and forceActivation (original)
    return entry.get('force_activation', False) or entry.get('forceActivation', False)

def always_on_kb_entries(knowledgebase):
    """Get always-on entries from SQL-based knowledgebase"""
    constant_entries = []
    for entry in knowledgebase['entries']:
        if condition_for_constant_entry(entry):
            # Handle both text_content (SQL) and text (original)
            text = entry.get('text_content') or entry.get('text', '')
            constant_entries.append(text)

    formatted_constant_entries = "\n".join([f" {content} " for content in constant_entries])
    return formatted_constant_entries

def trim_text_to_tokens(text, max_tokens):
    # Safety check: if token budget is too low, use a minimum of 50 tokens
    # This prevents entries from being reduced to single words
    if max_tokens < 10:
        max_tokens = 50
    tokens = text.split()[:max_tokens]
    return ' '.join(tokens)

async def get_key_matches(clicked, knowledgebase, max_entries=6):
    """Get key matches from SQL-based knowledgebase"""
    conversation_history, long_term_memories, stream_of_consciousness = await loaders.lite_variable_set(conversation_type=clicked)
    filtered_entries = []
    for entry in knowledgebase['entries']:
        if clicked != 'OpenAI' or entry.get('hidden') != True:
            # Handle keys being either a list or already parsed from SQL
            keys = entry.get('keys', [])
            if isinstance(keys, str):
                try:
                    keys = json.loads(keys)
                except:
                    keys = []
            
            for key in keys:
                if key.startswith('/') and key.endswith('/is'):  # Check if key is a regex pattern
                    pattern = key[1:-3]  # Remove the slashes and flags
                    if re.search(pattern, conversation_history, re.IGNORECASE):
                        filtered_entries.append(entry)
                        break
                elif key in conversation_history:  # Plain text key check
                    filtered_entries.append(entry)
                    break

    if not filtered_entries:
        return []

    vectorizer = TfidfVectorizer()
    # Handle both text_content (SQL) and text (original)
    filtered_entry_texts = [entry.get('text_content') or entry.get('text', '') for entry in filtered_entries]
    tfidf_matrix = vectorizer.fit_transform([conversation_history] + filtered_entry_texts)
    similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]

    # Combine the filtered entries and their respective similarities, and sort by similarity
    sorted_entries = sorted(zip(filtered_entries, similarities), key=lambda x: x[1], reverse=True)

    # Only return the top max_entries most relevant entries
    top_entries = [entry for entry, _ in sorted_entries[:max_entries]]

    # Sort top_entries based on budgetPriority before trimming
    # Handle both budget_priority (SQL) and contextConfig.budgetPriority (original)
    def get_priority(e):
        if 'budget_priority' in e:
            return e['budget_priority']
        elif 'contextConfig' in e and isinstance(e['contextConfig'], dict):
            return e['contextConfig'].get('budgetPriority', 0)
        return 0
    top_entries_sorted_by_priority = sorted(top_entries, key=get_priority, reverse=True)

    top_entries_trimmed = []
    for entry in top_entries_sorted_by_priority:
        # Handle both SQL and original formats
        keys = entry.get('keys', [])
        if isinstance(keys, str):
            try:
                keys = json.loads(keys)
            except:
                pass
        
        text = entry.get('text_content') or entry.get('text', '')
        name = entry.get('display_name') or entry.get('displayName', '')
        
        # Get token budget from either direct field or context_config
        token_budget = entry.get('token_budget', 250)
        if 'contextConfig' in entry and isinstance(entry['contextConfig'], dict):
            token_budget = entry['contextConfig'].get('tokenBudget', token_budget)
        elif 'context_config' in entry:
            if isinstance(entry['context_config'], dict):
                token_budget = entry['context_config'].get('tokenBudget', token_budget)
            elif isinstance(entry['context_config'], str):
                try:
                    config = json.loads(entry['context_config'])
                    token_budget = config.get('tokenBudget', token_budget)
                except:
                    pass
        
        budget_priority = get_priority(entry)
        
        top_entries_trimmed.append({
            'key': keys,
            'content': trim_text_to_tokens(text, token_budget),
            'comment': name,
            'tokenBudget': token_budget,
            'budgetPriority': budget_priority
        })

    return top_entries_trimmed

async def kb_entries(text, persona="Rhoda", conversation_type="Maggie"):
    """Async version of kb_entries"""
    conversation_history = await loaders.fleeting(conversation_type)
    knowledgebase = await load_knowledgebase(persona)
    constant_entries = always_on_kb_entries(knowledgebase)
    top_entries_trimmed = await get_key_matches(conversation_type, knowledgebase)
    print(f"Top Entries Trimmed: {top_entries_trimmed}")
    knowledgebase_entries = update_knowledgebase_field(top_entries_trimmed)
    kb_entries_text = "\n".join(knowledgebase_entries)
    kb_entries_tokens = tokenizer.encode(kb_entries_text)
    if len(kb_entries_tokens) > 1400:
        kb_entries_tokens = kb_entries_tokens[:1000]
        kb_entries_text = tokenizer.decode(kb_entries_tokens)

    return kb_entries_text

async def constant_entries(person="Harry"):
    """Async version of constant_entries"""
    knowledgebase = await load_knowledgebase(person)
    constant_entries = always_on_kb_entries(knowledgebase)
    return constant_entries

def update_knowledgebase_field(top_entries_trimmed):
    global knowledgebase_entries
    titles = []
    knowledgebase_entries = []
    for entry in top_entries_trimmed:
        titles.append(entry['comment'])  # Changed from 'comment' to 'displayName'
        knowledgebase_entries.append(entry['content'])  
    return knowledgebase_entries
    
async def prep():
    knowledgebase = await load_knowledgebase()
    constant_entries = always_on_kb_entries(knowledgebase)
    conversation_history, long_term_memories, stream_of_consciousness = await loaders.lite_variable_set(clicked)
    top_entries_trimmed = await get_key_matches(clicked, knowledgebase)
    print(f"Top Entries Trimmed: {top_entries_trimmed}")
    knowledgebase_entries = update_knowledgebase_field(top_entries_trimmed)
    print(f"Knowledgebase Entries: {knowledgebase_entries}")
    return knowledgebase_entries

async def check_duplicate_title(title, persona="Rhoda"):
    """Check if a knowledgebase entry with the given title already exists"""
    # Use SQL function for efficiency
    return database.check_kb_entry_exists(title)

async def add_knowledgebase_entry(title, content, tags, persona="Rhoda"):
    """Add a new entry to the SQL knowledgebase"""
    import uuid
    from datetime import datetime
    
    # Check for duplicate titles
    if await check_duplicate_title(title, persona):
        print(f"Knowledgebase entry with title '{title}' already exists, skipping...")
        return False
    
    # Create new entry for SQL
    new_entry = {
        "id": str(uuid.uuid4()),
        "display_name": title,
        "text_content": content,
        "keys": [tag.lower() for tag in tags],  # Convert tags to lowercase for keys
        "enabled": True,
        "force_activation": False,
        "key_relative": False,
        "non_story_activatable": False,
        "search_range": 1000,
        "token_budget": 250,
        "budget_priority": 400,
        "context_config": {
            "prefix": "",
            "suffix": "\n",
            "tokenBudget": 250,
            "reservedTokens": 0,
            "budgetPriority": 400,
            "trimDirection": "trimBottom",
            "insertionType": "newline",
            "maximumTrimType": "sentence",
            "insertionPosition": -1
        },
        "lore_bias_groups": [{
            "phrases": [],
            "ensureSequenceFinish": False,
            "generateOnce": True,
            "bias": 0,
            "enabled": True,
            "whenInactive": False
        }],
        "last_updated_at": int(datetime.now().timestamp() * 1000)
    }
    
    # Add to SQL database
    result = database.add_kb_entry(new_entry)
    
    if result:
        await loaders.save_to_soc(f"//Added knowledgebase entry: '{title}'")
        print(f"Successfully added knowledgebase entry: '{title}'")
        return True
    else:
        print(f"Failed to add knowledgebase entry: '{title}'")
        return False

async def edit_knowledgebase_entry(query, new_title=None, new_content=None, new_tags=None, append_content=None, persona="Rhoda"):
    """Edit an existing knowledgebase entry in SQL"""
    from datetime import datetime
    
    # Search for the entry to edit using SQL
    entries = database.search_kb_entries(query, limit=1)
    
    if not entries:
        print(f"No knowledgebase entry found matching query: '{query}'")
        await loaders.save_to_soc(f"//Could not find knowledgebase entry to edit: '{query}'")
        return False
    
    found_entry = entries[0]
    entry_id = found_entry['id']
    
    # Build update data
    update_data = {}
    
    if new_title and new_title != found_entry.get('display_name'):
        # Check for duplicate if changing title
        if await check_duplicate_title(new_title, persona):
            print(f"Cannot change title to '{new_title}' - entry with this title already exists")
            return False
        update_data['display_name'] = new_title
    
    if new_content:
        update_data['text_content'] = new_content
    elif append_content:
        update_data['text_content'] = found_entry.get('text_content', '') + '\n\n' + append_content
    
    if new_tags:
        update_data['keys'] = [tag.lower() for tag in new_tags]
    
    # Update in database
    if update_data:
        result = database.update_kb_entry(entry_id, update_data)
        
        if result:
            edit_summary = f"//Edited knowledgebase entry: '{found_entry['display_name']}'"
            if new_title:
                edit_summary += f" (title changed to '{new_title}')"
            if new_content:
                edit_summary += " (content replaced)"
            elif append_content:
                edit_summary += " (content appended)"
            if new_tags:
                edit_summary += " (tags updated)"
            
            await loaders.save_to_soc(edit_summary)
            print(f"Successfully edited knowledgebase entry: '{found_entry['display_name']}'")
            return True
    
    return False

# Example usage
if __name__ == "__main__":
    knowledgebase = load_knowledgebase()
    categories = fetch_categories(knowledgebase)
    print(f"//Categories from fetch_categories: {categories}")
    numbered_categories = "\n".join(f"{index + 1}. {category[0]}" for index, category in enumerate(categories))
    print(f"//Numbered categories: {numbered_categories}")
    
    # Assuming a category ID is selected, e.g., "324476b4-41cd-49cc-8f5a-f0a07b525343"
    category_id = "08264a50-e92b-4ea7-abd0-85127ec9a21e"
    numbered_entries = fetch_entries_by_category_id(category_id, knowledgebase)
    print(f"//Category selected: {category_id}\n//Entries Available:\n{numbered_entries}")