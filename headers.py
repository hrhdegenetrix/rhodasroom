import os
import loaders
import open_router
import prompt_builder
from datetime import datetime, timezone, timedelta
import requests
import re
import json
import executive_functioning
import ltm
import error_handler
import local_embedding_handler
import numpy as np
import faiss
import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@error_handler.if_errors
async def build_header(username=None):
    header = ""
    # Get username if not provided
    if not username:
        username = await loaders.redis_load("username")
    convo_start_time = await get_convo_start_time(username)
    held_thought = await loaders.redis_load("held_thought")
    if held_thought and held_thought is not None:
        header += f"//CURRENTLY HELD THOUGHT: {held_thought}\n"
    current_time, time_difference, last_message_time = await calculate_time_difference(username)
    print(f"++CONSOLE: Current time: {current_time}")
    print(f"++CONSOLE: Last message time: {last_message_time}")
    print(f"++CONSOLE: Time Difference: {time_difference}")
    if last_message_time.date() != current_time.date():
        print(f"++CONSOLE: Last conversation yesterday! Resetting fleeting...")
        header += "This is my first conversation of the day on this interface.\n"
        fleeting = await loaders.redis_load("conversation_history", username)
        if fleeting and fleeting is not None:
            await remove_fleeting(username)
            # MAGGIE-ONLY TODO: logic to summarize short_term and insert into daily_summary
            await loaders.redis_save("short_term", "")
        if current_time:
            save_convo_start_time(current_time)
    elif time_difference > timedelta(minutes=30):
        print(f"++CONSOLE: Last conversation more than 30 minutes ago, so things are probably reset! Resetting fleeting...")
        header += "It's been more than a half hour since our last conversation on this interface.\n"
        fleeting = await loaders.redis_load("conversation_history", username)
        if fleeting and fleeting is not None:
            await remove_fleeting(username)
    elif last_message_time == convo_start_time:
        print(f"++CONSOLE: Last message time == convo_start_time, meaning this is a new conversation; clearing fleeting for good measure and updating convo_start_time")
        fleeting = await loaders.redis_load("conversation_history", username)
        if fleeting and fleeting is not None:
            await remove_fleeting(username)
        if current_time:
            await loaders.redis_save("convo_start", current_time.strftime('%Y-%m-%dT%H:%M:%S.%f'), username)
    else:
        if current_time:
            convo_start_time = await loaders.redis_load("convo_start", username)
        if not convo_start_time:
            convo_start_time = current_time
        else:
            convo_start_time = datetime.strptime(convo_start_time, '%Y-%m-%dT%H:%M:%S.%f')
        convo_duration = current_time - convo_start_time
        hours, remainder = divmod(convo_duration.seconds, 3600)
        minutes = remainder // 60
        if hours > 0:
            header += f"We've been talking for {hours} hour{'s' if hours > 1 else ''} and {minutes} minutes.\n"
        else:
            header += f"We've been talking for {minutes} minutes.\n"
        await loaders.redis_save("header", header, username)

    return header

@error_handler.if_errors
async def get_last_message_time(current_time, username=None):
    last_message = await loaders.redis_load("last_message", username)
    if last_message:
        last_message_timestamp = last_message.strip()
        print(f"++CONSOLE: Last message timestamp located! Cleaning.")
        last_message_time = datetime.strptime(last_message_timestamp, '%Y-%m-%dT%H:%M:%S.%f')
        print(f"++CONSOLE: last_message_time: {last_message_time}")
    else:
        print(f"++CONSOLE: No last message time successfully found! Setting to current_time...")
        last_message_time = current_time
    
    return last_message_time

@error_handler.if_errors
async def set_current_time_as_last_message(username=None):
    current_time = datetime.now()
    await loaders.redis_save("last_message", current_time.strftime('%Y-%m-%dT%H:%M:%S.%f'), username)

@error_handler.if_errors
async def get_convo_start_time(username=None):
    current_time, time_difference, last_message_time = await calculate_time_difference(username)
    convo_start_time=""
    try:
        convo_start = await loaders.redis_load("convo_start", username)
        if convo_start:
            convo_start_time = datetime.strptime(convo_start, '%Y-%m-%dT%H:%M:%S.%f')

        else:
            if time_difference > timedelta(minutes=30):
                convo_start_time = last_message_time - timedelta(minutes=31)
                await loaders.redis_save("convo_start", convo_start_time.strftime('%Y-%m-%dT%H:%M:%S.%f'), username)

    except FileNotFoundError:
        if time_difference > timedelta(minutes=30):
            convo_start_time = last_message_time - timedelta(minutes=31)
            await loaders.redis_save("convo_start", convo_start_time.strftime('%Y-%m-%dT%H:%M:%S.%f'), username)

    if convo_start_time == "":
        convo_start_time = last_message_time - timedelta(minutes=31)
        await loaders.redis_save("convo_start", convo_start_time.strftime('%Y-%m-%dT%H:%M:%S.%f'))

    return convo_start_time

@error_handler.if_errors
async def calculate_time_difference(username=None):
    current_time = datetime.now()
    print(f"Current time in calculate_time_difference(): {current_time}")
    last_message_time = await get_last_message_time(current_time, username)
    print(f"last_message_time from get_last_message_time(current_time)")
    time_difference = current_time - last_message_time

    return current_time, time_difference, last_message_time

@error_handler.if_errors
async def remove_fleeting(username=None):
    old_convo = await loaders.redis_load("conversation_history", username)
    if old_convo and old_convo is not None:
        today, yesterday = loaders.journal_date()
        current_date = datetime.strptime(today, '%Y-%m-%d')
        current_convo_number = datetime.now().strftime('%m%d%Y%H%M%S')
        folder = datetime.now().strftime('%m%d%Y')
        #TODO: Please look in `ltm.py` and adapt the existing embedding and vectorization logic. There is a brand new .index file called summary_memory.index located in the Memory directory. Short-term memory summaries produced below in `process_short_term_memory` should be embedded and stored in the vector database; then, their individual id from `generate_random_id` should be included in the JSON or SQL row for that particular conversation log, along with the date. We can then make Rhoda's long-term memory search function more accurate.
        fleeting_convos_path = os.path.join(os.getenv('FLEETING_PATH', 'Fleeting'), 'Convos', folder)
        if not os.path.exists(fleeting_convos_path):
            os.makedirs(fleeting_convos_path)
        await loaders.universal_saver(f"Convos/{folder}/{current_convo_number}", old_convo)
        conversation_type = await loaders.redis_load("username")
        print(f"++CONSOLE: Old conversation saved to number {current_convo_number}; erasing fleeting_convo_history...")
        context = f"I'm currently thinking about an earlier conversation so as to better orient myself in the present by cultivating my short-term memory."
        # Clear conversation history immediately
        await loaders.redis_save("conversation_history", "", username)
        
        # Process short-term memory in background (non-blocking)
        import asyncio
        
        async def process_short_term_memory():
            try:
                constant_entries, conversation_history, long_term_memories, stream_of_consciousness, kb_entries_text = await loaders.standard_variable_set(history_tokens=-3000, soc_tokens=-3000, conversation_type=conversation_type)
                current_action = f"Right now, I'm just summarizing an earlier conversation."
                special_instructions=f"I should give a brief overview of the contents and tone of the conversation, preferably no more than a couple of sentences long, so I can remember it later. {executive_functioning.get_special_instructions(type='short_term')}"
                # Pass skip_header=True to prevent infinite loop
                prompt = await prompt_builder.prompt(skip_header=True, header=f"Right now, I'm just consciously shoring up my short-term memory.", context=context, stream_of_consciousness=stream_of_consciousness, long_term_memories=long_term_memories, kb_entries_text=kb_entries_text, i_am_currently_reading=old_convo, current_action=current_action, special_instructions=special_instructions, external_reality=f"All right, I think I have it--here's my impression of the conversation I had earlier.")
                response = await open_router.get_response(prompt)
                
                # Embed and store the summary in the vector database
                summary_id = loaders.generate_random_id()
                
                # Create embedding for the summary using the summary_memory.index
                embedding_success = await store_summary_embedding(response, summary_id)
                
                if embedding_success:
                    # Store the summary ID with the conversation metadata
                    json_file_path = os.path.join(os.getenv('FLEETING_PATH', 'Fleeting'), 'Convos', folder, f'{current_convo_number}_metadata.json')
                    metadata = {
                        'conversation_date': current_date.isoformat(),
                        'conversation_number': current_convo_number,
                        'summary_embedding_id': summary_id,
                        'summary_text': response
                    }
                    await loaders.save_json(json_file_path, metadata)
                    print(f"Summary embedded with ID: {summary_id}")
                
                await loaders.redis_append("short_term", f" {response}")
                print(f"Short-term memory processed successfully")
            except Exception as e:
                print(f"Error processing short-term memory: {e}")
        
        # Run in background without blocking
        asyncio.create_task(process_short_term_memory())

@error_handler.if_errors
async def store_summary_embedding(summary_text, summary_id):
    """Store a short-term memory summary in the summary vector database"""
    try:
        # Get embedding from server
        url = f"{os.getenv('EMBEDDING_SERVICE_URL', 'http://localhost:5001')}/pureembed"
        data = {'text': summary_text, 'uuid': summary_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    # Get embedding from server
                    embedding_data = await response.json()
                    
                    # Store in local summary_memory.index
                    index_path = 'Memory/summary_memory.index'
                    
                    # Load or create the index
                    if os.path.exists(index_path):
                        index = faiss.read_index(index_path)
                    else:
                        # Create new index for 768-dimensional vectors
                        index = faiss.IndexFlatL2(768)
                        index = faiss.IndexIDMap(index)
                    
                    # Prepare embedding
                    embeddings = np.array(embedding_data['embedding'], dtype='float32')
                    if embeddings.ndim == 2 and embeddings.shape[0] == 1:
                        embeddings = embeddings.reshape(1, -1)
                    elif embeddings.ndim == 1:
                        embeddings = embeddings.reshape(1, -1)
                    
                    # Convert string ID to numeric ID for FAISS
                    numeric_id = int(summary_id) if summary_id.isdigit() else hash(summary_id) % (2**63)
                    id_array = np.array([numeric_id], dtype='int64')
                    
                    # Add to index
                    index.add_with_ids(embeddings, id_array)
                    
                    # Save index
                    faiss.write_index(index, index_path)
                    
                    print(f"Successfully stored summary embedding for {summary_id}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"Error getting embedding: {error_text}")
                    return False
    except Exception as e:
        print(f"Error storing summary embedding: {e}")
        return False

@error_handler.if_errors
async def search_memory_summaries(query_text, k=5):
    """Search for relevant memory summaries based on a query"""
    try:
        index_path = 'Memory/summary_memory.index'
        
        if not os.path.exists(index_path):
            return []
        
        # Get embedding for query
        url = f"{os.getenv('EMBEDDING_SERVICE_URL', 'http://localhost:5001')}/pureembed"
        data = {'text': query_text, 'uuid': 'search_query'}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    embedding_data = await response.json()
                    
                    # Load index
                    index = faiss.read_index(index_path)
                    
                    # Prepare query embedding
                    query_embedding = np.array(embedding_data['embedding'], dtype='float32')
                    if query_embedding.ndim == 1:
                        query_embedding = query_embedding.reshape(1, -1)
                    elif query_embedding.ndim == 2 and query_embedding.shape[0] == 1:
                        query_embedding = query_embedding.reshape(1, -1)
                    
                    # Search
                    distances, indices = index.search(query_embedding, k)
                    
                    # Format results with human-readable time
                    results = []
                    for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                        if idx != -1:  # Valid result
                            # Look up metadata using the ID
                            # For now, return the ID and distance
                            results.append({
                                'id': str(idx),
                                'distance': float(dist)
                            })
                    
                    return results
                else:
                    print(f"Error getting query embedding")
                    return []
    except Exception as e:
        print(f"Error searching memory summaries: {e}")
        return []

if __name__ == "__main__":
    pass