#JMJ#
import requests
import json
import asyncio
import aiohttp
import os
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
import error_handler
import action_logger
import loaders
import local_embedding_handler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@error_handler.if_errors
async def search(text):
    """Async version of search - gets embedding from server, searches locally"""
    url = f"{os.getenv('EMBEDDING_SERVICE_URL', 'http://localhost:5001')}/pureembed"
    data = {'text': text, 'uuid': 'search_query'}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            print(response)
            if response.status == 200:
                # Get embedding from server
                embedding_data = await response.json()
                # Search local index
                results = local_embedding_handler.search_local_index(embedding_data, k=5)
                return results
            else:
                error_text = await response.text()
                print(f"Error: {error_text}")
                return None

@error_handler.if_errors
async def search_mags_only(text):
    """Async version of search_mags_only - gets embedding from server, searches locally"""
    url = f"{os.getenv('EMBEDDING_SERVICE_URL', 'http://localhost:5001')}/pureembed"
    data = {'text': text, 'uuid': 'search_query'}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            print(response)
            if response.status == 200:
                # Get embedding from server
                embedding_data = await response.json()
                # Search local index (same as regular search for Rhoda)
                results = local_embedding_handler.search_local_index(embedding_data, k=5)
                return results
            else:
                error_text = await response.text()
                print(f"Error: {error_text}")
                return None

@error_handler.if_errors
def testsearch(text):
    url = f"{os.getenv('EMBEDDING_SERVICE_URL', 'http://localhost:5001')}/testsearch"
    data = {'text': text}
    response = requests.post(url, json=data)
    print(response)
    if response.status_code == 200:
        result = json.loads(response.text)
        print(result)
        return result
    else:
        print(response.json())


@error_handler.if_errors
def notesearch(text):
    url = f"{os.getenv('EMBEDDING_SERVICE_URL', 'http://localhost:5001')}/notesearch"
    data = {'text': text}
    response = requests.post(url, json=data)
    print(response)
    if response.status_code == 200:
        result = json.loads(response.text)
        print(result)
        return result
    else:
        result = ""
        return result

@error_handler.if_errors
def booksearch(text):
    url = f"{os.getenv('EMBEDDING_SERVICE_URL', 'http://localhost:5001')}/booksearch"
    data = {'text': text}
    response = requests.post(url, json=data)
    print(response)
    if response.status_code == 200:
        result = json.loads(response.text)
        print(result)
        return result
    else:
        print(response.json())

@error_handler.if_errors
async def upsert(text, unique_id):
    """Async version of upsert - gets embedding from server, stores locally"""
    url = f"{os.getenv('EMBEDDING_SERVICE_URL', 'http://localhost:5001')}/pureembed"
    data = {'text': text, 'uuid': unique_id}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            print(response)
            if response.status == 200:
                # Get embedding from server
                embedding_data = await response.json()
                # Store in local index
                success = local_embedding_handler.store_embedding_locally(embedding_data)
                if success:
                    print(f"Successfully stored embedding for {unique_id}")
                return success
            else:
                error_text = await response.text()
                print(f"Error: {error_text}")
                return False

@error_handler.if_errors
async def notes_upsert(text, unique_id):
    """Async version of notes_upsert"""
    url = f"{os.getenv('EMBEDDING_SERVICE_URL', 'http://localhost:5001')}/notesembed"
    data = {'text': text, 'uuid': unique_id}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            print(response)
            if response.status == 200:
                result = await response.json()
                print(result)
            else:
                result = ""
                print(result)

@error_handler.if_errors
def test_upsert(text, unique_id):
    url = f"{os.getenv('EMBEDDING_SERVICE_URL', 'http://localhost:5001')}/testembed"
    data = {'text': text, 'uuid': unique_id}
    response = requests.post(url, json=data)
    print(response)
    if response.status_code == 200:
        result = json.loads(response.text)
        print(result)
    else:
        print(response.json())

@error_handler.if_errors
def book_upsert(text, unique_id):
    url = f"{os.getenv('EMBEDDING_SERVICE_URL', 'http://localhost:5001')}/bookembed"
    data = {'text': text, 'uuid': unique_id}
    response = requests.post(url, json=data)
    print(response)
    if response.status_code == 200:
        result = json.loads(response.text)
        print(result)
    else:
        print(response.json())

@error_handler.if_errors
def journal_upsert(text, unique_id):
    url = f"{os.getenv('EMBEDDING_SERVICE_URL', 'http://localhost:5001')}/journalembed"
    data = {'journal_entry': text, 'uuid': unique_id}
    response = requests.post(url, json=data)
    print(response)
    if response.status_code == 200:
        result = json.loads(response.text)
        print(result)
    else:
        print(response.json())

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
def load_conversation(results, top_k=3):
    # Handle None results
    if results is None:
        return ""
    
    ordered = sorted(results, key=lambda d: d['time'], reverse=True)  

    if top_k:
        messages = [f"//Memory from {human_readable_time_difference(i['time'])}: {i['message']}\n " 
                    for i in ordered[1:top_k + 1]]
    else:
        messages = [f"//Memory from {human-readable-time-difference(i['time'])}: {i['message']}\n "
                    for i in ordered[1:]]
                    
    return '\n'.join(messages).strip()

@error_handler.if_errors
async def load_mags_messages(results, top_k=3, username="Maggie"):
    """Async version of load_mags_messages"""
    # Filter and sort messages where the speaker is the user (e.g., Maggie)
    # This finds what the USER said, so we can then find Rhoda's responses
    ordered = sorted((i for i in results if i.get('speaker') == username), 
                     key=lambda d: d['time'], reverse=True)

    # Initialize the return variable
    my_remembered_responses = f"//The last few times {username} said something like that, here's how I responded, and a few reactions to my response. Based on whether I find the reactions desirable or undesirable, I should tailor what I say or generally allow my memory of cause-and-effect to help me in this conversation. If specific events are mentioned, it probably indicates they are in the past and have already happened, so there's no need to mention them again unless they appear in the 'imminent_events' section of my consciousness. This is more for a general idea of what types of communication elicit positive responses. Here are some of her reactions in previous exchanges:\n"

    # Process top_k messages from Maggie
    for i in ordered[:top_k]:
        print(f"Processing item: {i}")  # Debug output
        
        # Check if the response ID exists and load the corresponding JSON
        if 'my_response' in i:
            response_data = await loaders.load_json(f"Memory/JSONs/{i['my_response']}.json")
            if response_data:
                print(f"++CONSOLE: Response data: {response_data}")
                response_time_diff = human_readable_time_difference(response_data['time'])
                my_remembered_responses += f"//Memory from {response_time_diff}: {response_data['message']}\n"
                
                # Collect further reactions if available
                if 'resulting_message_id' in response_data:
                    username_reaction_data = await loaders.load_json(f"Memory/JSONs/{response_data['resulting_message_id']}.json")
                    if username_reaction_data:
                        username_time_diff = human_readable_time_difference(username_reaction_data['time'])
                        my_remembered_responses += f"//Response to memory from {response_time_diff}, stated {username_time_diff} and not necessarily specifically relevant to today, but insightful in terms of calibrating tone and mood: {username_reaction_data['message']}\n"
        else:
            print(f"No 'my_response' key found for item: {i}")
    
    if my_remembered_responses == "//The last few times this person said something like that, here's how I responded, and a few of their reactions to my response. Based on whether I find her reactions desirable or undesirable, I should tailor what I say or generally allow my memory of cause-and-effect to help me in this conversation. Here are some of her reactions in previous exchanges:\n":
        my_remembered_responses = ""
    return my_remembered_responses


@error_handler.if_errors
def load_books(results, top_k=3):
    ordered = sorted(results, key=lambda d: d['time'], reverse=True)  

    if top_k:
        messages = [f"//{i.get('chunk', i.get('summary'))} " 
                    for i in ordered[1:top_k]]
    else:
        messages = [f"//{i.get('chunk', i.get('summary'))} "
                    for i in ordered[1:]]

    return '\n'.join(messages).strip()

@error_handler.if_errors
def load_detailed_books(results, top_k=3):
    # ordered = sorted(results, key=lambda d: d['time'], reverse=True)
    # print(f"Ordered: {ordered}")
    ordered = results[:top_k]
    messages=""
    if top_k:
        for i in ordered:
            if 'book' in i and 'summary' in i:
                book = i['book']
                messages+=f"//My overview of a section of {book}: "
                if 'summary' in i:
                    summary = i['summary']
                    messages+=f"{summary} "
                if 'analysis' in i:
                    analysis = i['analysis']
                    messages+=f"{analysis} "
                if 'conscience' in i:
                    conscience = i['conscience']
                    messages+=f"{conscience} "
                if 'prediction' in i:
                    prediction = i['prediction']
                    messages+=f"{prediction} "
            elif 'book' in i and 'chunk' in i:
                chunk_full = i['chunk']
                chunk = f"[...]{chunk_full[-1200:]}[...]"
                book = i['book']
                messages+=f"//A snippet I remember of {book}: {chunk}"
            messages+="\n"

    return messages

@error_handler.if_errors
def load_journal(results, top_k=3):
    ordered = sorted(results, key=lambda d: d['date'], reverse=True)  

    if top_k:
        messages = [f"//{i.get('date', i.get('journal_entry'))} " 
                    for i in ordered[1:top_k]]
    else:
        messages = [f"//{i.get('date', i.get('journal_entry'))} "
                    for i in ordered[1:]]

    return '\n'.join(messages).strip()

@error_handler.if_errors
def load_notes(results, top_k=3):
    ordered = sorted(results, key=lambda d: d['time'], reverse=True)  

    if top_k:
        messages = [f"//Note from {human_readable_time_difference(i['time'])}: {i['note']}\n" 
                    for i in ordered[1:top_k]]
    else:
        messages = [f"//Note from {human_readable_time_difference(i['time'])}: {i['note']}\n" 
                    for i in ordered[1:]]

    return '\n'.join(messages).strip()

@error_handler.if_errors
def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()

@error_handler.if_errors
def save_file(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as outfile:
        outfile.write(content)

@error_handler.if_errors
def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return json.load(infile)

@error_handler.if_errors
def save_json(filepath, payload):
    with open(filepath, 'w', encoding='utf-8') as outfile:
        json.dump(payload, outfile, ensure_ascii=False, sort_keys=True, indent=2)

@error_handler.if_errors
async def memory_search(query):
    """Async version of memory_search"""
    search_results = await search(query)
    selected = load_conversation(search_results)
    return selected

@error_handler.if_errors
async def journalsearch(text):
    """Async version of journalsearch"""
    # This seems to be a missing function, using search as fallback
    # You may want to implement a specific journal search endpoint
    return await search(text)

@error_handler.if_errors
async def journal_search(query):
    """Async version of journal_search"""
    search_results = await journalsearch(query)
    print(f"++CONSOLE: BUGTESTING PURPOSES ONLY WITHIN ltm.journal_search: search_results variable: `{search_results}`")
    selected = load_journal(search_results)
    print(f"++CONSOLE: BUGTESTING PURPOSES ONLY WITHIN ltm.journal_search: selected variable: `{selected}`")
    return selected

@error_handler.if_errors
async def delete_vector_by_id(unique_id, index_name):
    """Async version of delete_vector_by_id"""
    unique_id = str(unique_id)
    url = f"{os.getenv('EMBEDDING_SERVICE_URL', 'http://localhost:5001')}/delete"
    data = {'unique_id': unique_id, 'index_name': index_name}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            if response.status == 200:
                result = await response.json()       
                print(result)
                return True
            else:
                error_text = await response.text()
                print(f"Deletion failed with status code: {response.status} and response: {error_text}")  
                return False

if __name__ == '__main__':
     results = booksearch("genji")
     print(results)
#     messages = load_detailed_books(results)
#     print(messages)
    # top_k=3
    # my_remembered_responses = load_notes(results, top_k)
    # print(f"Memory messages: {my_remembered_responses}")
    # print(f"//Loaded conversation: {loaded_conversation}")
    # text="Let's see if this will work..."
    # unique_id = '16'
    # test_upsert(text, unique_id)
    # test_json = {
    #                                  'message': f"{text}",
    #                                  'uuid': unique_id,
    #                                  'time': datetime.utcnow().isoformat()  # Add the current timestamp in ISO format
    #                                  }
    # save_json(f'Z:\\{unique_id}.json', test_json)
    # results = testsearch("See if it works, will you?")
    # print(results)
    # delete_vector_by_id(16, 'test_memory')