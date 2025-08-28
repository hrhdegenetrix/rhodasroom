"""
GUI Interface Module - Adapts central_logic.py for browser-based interaction
Handles both audio and text input processing with proper session management
"""

import os
import tempfile
import base64
import wave
import io
from datetime import datetime
import numpy as np
from scipy.io.wavfile import write
import threading
import time
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import existing modules
import central_logic
import loaders
import prompt_builder
import executive_functioning
import post_processing
import ltm
import error_handler
import document_handler

# Global state for recording management
active_recordings = {}
recording_lock = threading.Lock()

@error_handler.if_errors
async def process_audio_input(audio_file_path, username, redis_key=None, session_id=None, socketio=None, document_content=None, image_url=None):
    """
    Process audio input from browser recording
    Adapts on_record_button_release() for web use
    """
    # Use user-specific Redis namespace
    if not redis_key:
        redis_key = f"user:{username}"
    
    # Store username in Redis for this session
    await loaders.redis_save("username", username, username)
    
    # Get current date for recording organization
    current_date = central_logic.recording_date()
    
    # Create recording folder
    recording_folder = os.path.join(os.getenv('PODCAST_RECORDINGS_PATH', 'PodcastRecordings'), current_date)
    if not os.path.exists(recording_folder):
        os.makedirs(recording_folder, exist_ok=True)
    
    # Save the recording with timestamp
    current_recording_number = datetime.now().strftime('%m%d%Y%H%M%S')
    recording_filename = os.path.join(recording_folder, f"input{current_recording_number}.wav")
    
    # Copy audio file to recordings folder - use simple file write to avoid permission issues
    with open(audio_file_path, 'rb') as src:
        audio_data = src.read()
    with open(recording_filename, 'wb') as dst:
        dst.write(audio_data)
    
    # Transcribe the audio
    transcription_result = transcribe_audio_file(audio_file_path)
    
    if not transcription_result:
        return {'error': 'Failed to transcribe audio'}
    
    raw_transcription = transcription_result
    transcription = post_processing.process_transcript(raw_transcription)
    
    # Check for security issues (prompt injection) in transcribed text
    import security_utils
    is_safe, timeout_duration = security_utils.check_message_security(username, transcription)
    
    if not is_safe:
        return {
            'error': f'Security violation detected in audio. You have been timed out for {timeout_duration} minutes.',
            'security_violation': True,
            'timeout_duration': timeout_duration
        }
    
    # Save transcription to Redis with user namespace
    await loaders.redis_save("transcription", transcription, username)
    
    # Update conversation history
    await loaders.save_to_fleeting_convo_history(transcription, username, username)
    await loaders.save_transcription(transcription)
    
    # Generate unique ID and metadata for transcription
    unique_id_transcription = loaders.generate_random_id()
    previous_message = await loaders.redis_load("last_response_id", username)
    
    metadata_transcription = {
        'speaker': username,
        'message': f"{datetime.utcnow().isoformat()} {username}: {transcription}",
        'uuid': unique_id_transcription,
        'prior_message_id': previous_message,
        'time': datetime.utcnow().isoformat()
    }
    
    # Save metadata
    await loaders.redis_save("last_transcript_id", unique_id_transcription, username)
    
    if previous_message:
        previous_json_path = os.path.join('Memory', 'JSONs', f'{previous_message}.json')
        if os.path.exists(previous_json_path):
            previous_json = await loaders.load_json(previous_json_path)
            previous_json["resulting_message_id"] = unique_id_transcription
            await loaders.save_json(previous_json_path, previous_json)
    
    await loaders.save_json(os.path.join('Memory', 'JSONs', f'{unique_id_transcription}.json'), metadata_transcription)
    
    # Store in long-term memory (skip await to avoid blocking)
    # This will run in background without blocking the response
    asyncio.create_task(ltm.upsert(transcription, unique_id_transcription))  # Fire and forget
    
    # Generate response
    response, conversation_ended = await generate_response_for_user(username, transcription, document_content, image_url)
    
    # Save response to Redis
    await loaders.redis_save("response", response, username)
    
    # Update conversation history with response IMMEDIATELY
    await loaders.save_to_fleeting_convo_history(response, 'Rhoda', username)
    await loaders.save_to_daily_log_with_label(response, "Rhoda")
    
    # Debug session_id and socketio
    print(f"DEBUG: session_id={session_id}, socketio={socketio}, response_length={len(response)}")
    
    # Start audio synthesis in a separate thread to ensure it runs
    if session_id and socketio and response:  # Also check response is not empty
        print(f"Starting audio synthesis thread for {username} with session_id: {session_id}")
        print(f"Response to synthesize: {response[:100]}...")  # Log first 100 chars
        # Use threading to ensure audio synthesis runs independently
        import threading
        def run_synthesis():
            """Run synthesis in a new event loop in thread"""
            try:
                print(f"Audio synthesis thread running for {username}")
                # Create new event loop for this thread
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                # Run the synthesis
                new_loop.run_until_complete(synthesize_and_send_audio(response, username, session_id, socketio))
                new_loop.close()
                print(f"Audio synthesis completed for {username}")
            except Exception as e:
                print(f"Error in audio synthesis thread: {e}")
                import traceback
                traceback.print_exc()
        
        # Start thread
        synthesis_thread = threading.Thread(target=run_synthesis, daemon=True)
        synthesis_thread.start()
        print(f"Audio synthesis thread started for {username}")
    else:
        print(f"WARNING: Not starting audio synthesis - session_id={session_id}, socketio={socketio}, response_empty={not response}")
    
    # Return response immediately without waiting for audio
    audio_url = None  # Audio will be sent via WebSocket when ready
    
    # Create response metadata
    unique_id_response = loaders.generate_random_id()
    # Store response in long-term memory (skip await to avoid blocking) 
    asyncio.create_task(ltm.upsert(response, unique_id_response))  # Fire and forget
    
    metadata_response = {
        'speaker': 'Rhoda',
        'message': f"{datetime.utcnow().isoformat()} Rhoda: {response}",
        'uuid': unique_id_response,
        'prior_message': unique_id_transcription,
        'time': datetime.utcnow().isoformat()
    }
    
    metadata_transcription['my_response'] = unique_id_response
    await loaders.redis_save("last_response_id", unique_id_response, username)
    
    await loaders.save_json(os.path.join('Memory', 'JSONs', f'{unique_id_response}.json'), metadata_response)
    await loaders.save_json(os.path.join('Memory', 'JSONs', f'{unique_id_transcription}.json'), metadata_transcription)

  
    # Reset temporary Redis values
    await loaders.redis_save("response", "", username)
    await loaders.redis_save("vectorized", "", username)
    await loaders.redis_save("printed", "", username)
    
    return {
        'success': True,
        'transcription': transcription,
        'response': response,
        'audio_url': audio_url,
        'timestamp': datetime.now().isoformat(),
        'conversation_ended': conversation_ended
    }

@error_handler.if_errors
async def process_text_input(text_message, username, redis_key=None, session_id=None, socketio=None, document_content=None, image_url=None):
    """
    Process text input from browser (bypasses transcription)
    """
    # Use user-specific Redis namespace
    if not redis_key:
        redis_key = f"user:{username}"
    
    # Store username in Redis for this session
    await loaders.redis_save("username", username, username)
    
    # Skip transcription step, use text directly
    transcription = text_message
    
    # Check for security issues (prompt injection) in text message
    import security_utils
    is_safe, timeout_duration = security_utils.check_message_security(username, transcription)
    
    if not is_safe:
        return {
            'error': f'Security violation detected. You have been timed out for {timeout_duration} minutes.',
            'security_violation': True,
            'timeout_duration': timeout_duration
        }
    
    # Save to Redis with user namespace
    await loaders.redis_save("transcription", transcription, username)
    
    # Update conversation history
    await loaders.save_to_fleeting_convo_history(transcription, username, username)
    
    # Generate unique ID and metadata
    unique_id_transcription = loaders.generate_random_id()
    previous_message = await loaders.redis_load("last_response_id", username)
    
    metadata_transcription = {
        'speaker': username,
        'message': f"{datetime.utcnow().isoformat()} {username}: {transcription}",
        'uuid': unique_id_transcription,
        'prior_message_id': previous_message,
        'time': datetime.utcnow().isoformat(),
        'input_type': 'text'
    }
    
    # Save metadata
    await loaders.redis_save("last_transcript_id", unique_id_transcription, username)
    
    if previous_message:
        previous_json_path = os.path.join('Memory', 'JSONs', f'{previous_message}.json')
        if os.path.exists(previous_json_path):
            previous_json = await loaders.load_json(previous_json_path)
            previous_json["resulting_message_id"] = unique_id_transcription
            await loaders.save_json(previous_json_path, previous_json)
    
    await loaders.save_json(os.path.join('Memory', 'JSONs', f'{unique_id_transcription}.json'), metadata_transcription)
    
    # Store in long-term memory (skip await to avoid blocking)
    # This will run in background without blocking the response
    asyncio.create_task(ltm.upsert(transcription, unique_id_transcription))  # Fire and forget
    
    # Generate response
    response, conversation_ended = await generate_response_for_user(username, transcription, document_content, image_url)
    
    # Save response to Redis
    await loaders.redis_save("response", response, username)
    
    # Update conversation history with response IMMEDIATELY
    await loaders.save_to_fleeting_convo_history(response, 'Rhoda', username)
    await loaders.save_to_daily_log_with_label(response, "Rhoda")
    
    # Debug session_id and socketio
    print(f"DEBUG: session_id={session_id}, socketio={socketio}, response_length={len(response)}")
    
    # Start audio synthesis in a separate thread to ensure it runs
    if session_id and socketio and response:  # Also check response is not empty
        print(f"Starting audio synthesis thread for {username} with session_id: {session_id}")
        print(f"Response to synthesize: {response[:100]}...")  # Log first 100 chars
        # Use threading to ensure audio synthesis runs independently
        import threading
        def run_synthesis():
            """Run synthesis in a new event loop in thread"""
            try:
                print(f"Audio synthesis thread running for {username}")
                # Create new event loop for this thread
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                # Run the synthesis
                new_loop.run_until_complete(synthesize_and_send_audio(response, username, session_id, socketio))
                new_loop.close()
                print(f"Audio synthesis completed for {username}")
            except Exception as e:
                print(f"Error in audio synthesis thread: {e}")
                import traceback
                traceback.print_exc()
        
        # Start thread
        synthesis_thread = threading.Thread(target=run_synthesis, daemon=True)
        synthesis_thread.start()
        print(f"Audio synthesis thread started for {username}")
    else:
        print(f"WARNING: Not starting audio synthesis - session_id={session_id}, socketio={socketio}, response_empty={not response}")
    
    # Return response immediately without waiting for audio
    audio_url = None  # Audio will be sent via WebSocket when ready
    
    # Create response metadata
    unique_id_response = loaders.generate_random_id()
    # Store response in long-term memory (skip await to avoid blocking) 
    asyncio.create_task(ltm.upsert(response, unique_id_response))  # Fire and forget
    
    metadata_response = {
        'speaker': 'Rhoda',
        'message': f"{datetime.utcnow().isoformat()} Rhoda: {response}",
        'uuid': unique_id_response,
        'prior_message': unique_id_transcription,
        'time': datetime.utcnow().isoformat()
    }
    
    metadata_transcription['my_response'] = unique_id_response
    await loaders.redis_save("last_response_id", unique_id_response, username)
    
    await loaders.save_json(os.path.join('Memory', 'JSONs', f'{unique_id_response}.json'), metadata_response)
    await loaders.save_json(os.path.join('Memory', 'JSONs', f'{unique_id_transcription}.json'), metadata_transcription)
    
    # Reset temporary Redis values
    await loaders.redis_save("response", "", username)
    await loaders.redis_save("vectorized", "", username)
    await loaders.redis_save("printed", "", username)
    
    return {
        'success': True,
        'response': response,
        'audio_url': audio_url,
        'timestamp': datetime.now().isoformat(),
        'conversation_ended': conversation_ended
    }

@error_handler.if_errors
def on_record_button_press(username):
    """
    Handle push-to-talk button press event
    Initializes recording session
    """
    with recording_lock:
        session_id = f"{username}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        active_recordings[session_id] = {
            'username': username,
            'start_time': datetime.now(),
            'chunks': [],
            'is_recording': True
        }
        print(f"Recording started for {username} (session: {session_id})")
        return session_id

@error_handler.if_errors
def on_record_button_release(session_id):
    """
    Handle push-to-talk button release event
    ENSURES microphone is properly closed and released
    """
    with recording_lock:
        if session_id not in active_recordings:
            print(f"No active recording found for session {session_id}")
            return None
        
        # Mark recording as stopped IMMEDIATELY
        active_recordings[session_id]['is_recording'] = False
        active_recordings[session_id]['end_time'] = datetime.now()
        
        # Force microphone release
        print(f"Microphone released for session {session_id}")
        
        # Process the recorded audio
        recording_data = active_recordings[session_id]
        username = recording_data['username']
        
        # Clean up the recording session
        del active_recordings[session_id]
        
        print(f"Recording stopped and cleaned up for {username} (session: {session_id})")
        return {
            'success': True,
            'username': username,
            'message': 'Recording stopped and microphone released'
        }

@error_handler.if_errors
def transcribe_audio_file(file_path):
    """
    Transcribe audio file using the whisper API
    """
    import requests
    
    url = f"{os.getenv('WHISPER_SERVICE_URL', 'http://localhost:8000')}/transcribe"
    
    try:
        with open(file_path, "rb") as file:
            response = requests.post(url, files={'audio': file})
        
        if response.status_code == 200:
            data = response.json()
            if 'text' in data:
                print(f"Transcription successful: {data['text'][:100]}...")
                return data['text']
            else:
                print(f"Unexpected response from Whisper API: {data}")
                return None
        else:
            print(f"Error from Whisper API: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return None

@error_handler.if_errors
async def generate_response_for_user(username, transcription, document_content=None, image_url=None):
    """
    Generate AI response for user input
    Uses existing central_logic functions
    Optionally includes document content for context
    Returns tuple: (response, conversation_ended)
    """
    # Check for existing response in Redis
    response = await loaders.redis_load("response", username)
    
    if response and response != "":
        # Check if response is already in log (retry scenario)
        today = datetime.now().strftime('%Y-%m-%d')
        log_path = f"Logs/{today}.txt"
        if os.path.exists(log_path):
            with open(log_path, 'r') as f:
                log_content = f.read()
                if response in log_content:
                    # Generate new response with retry flag
                    response = await central_logic.generate_response(username, retry=True, type="default", i_am_currently_reading=document_content, image=image_url)
    else:
        # Generate fresh response
        response = await central_logic.generate_response(username, type="default", i_am_currently_reading=document_content, image=image_url)
    
    # Handle edge cases
    if response is None:
        response = await central_logic.generate_response(username, retry=True, type="default", i_am_currently_reading=document_content, image=image_url)
    elif response == "The entire response is a repetition of a previous response. Reprompting needed.":
        response = await central_logic.generate_response(username, retry=True, type="default", i_am_currently_reading=document_content, image=image_url)
    
    # Check if user was timed out during response generation (Rhoda ended conversation)
    import database
    conversation_ended = database.is_user_timed_out(username)
    
    return response, conversation_ended

@error_handler.if_errors
async def synthesize_and_send_audio(response_text, username, session_id, socketio):
    """Synthesize audio and emit chunks as they arrive via WebSocket"""
    print(f"Starting audio synthesis for {username} (session: {session_id})")
    print(f"Response text length: {len(response_text)} characters")
    try:
        # Define callback to emit each chunk as it arrives
        async def emit_chunk(chunk_path, chunk_number):
            try:
                print(f"Processing chunk {chunk_number} from path: {chunk_path}")
                # Convert to web-accessible path - chunk files are in PodcastRecordings/date/
                filename = os.path.basename(chunk_path)
                web_path = f"/audio/{filename}"
                
                # Emit this chunk via WebSocket immediately 
                print(f"Emitting audio_chunk event for chunk {chunk_number}")
                socketio.emit('audio_chunk', {
                    'audio_url': web_path,
                    'chunk_number': chunk_number,
                    'is_final': False
                }, room=session_id)
                print(f"Audio chunk {chunk_number} sent for {username}: {web_path}")
            except Exception as e:
                print(f"Error emitting chunk {chunk_number}: {e}")
                import traceback
                traceback.print_exc()
        
        # Synthesize with chunk callback for streaming
        synthesized_file = await central_logic.synthesize_speech(
            response_text, 
            persona="Rhoda", 
            play_locally=False,
            chunk_callback=emit_chunk
        )
        
        # Emit final signal when all chunks are done
        if synthesized_file:
            socketio.emit('audio_chunk', {
                'is_final': True
            }, room=session_id)
            print(f"All audio chunks sent for {username}")
    except Exception as e:
        print(f"Error synthesizing and sending audio: {e}")
        import traceback
        traceback.print_exc()

# Removed synthesize_and_save_speech - now using streaming approach in synthesize_and_send_audio

@error_handler.if_errors
def cleanup_stale_recordings():
    """
    Clean up any recordings that have been active for too long
    Ensures no microphones stay open indefinitely
    """
    with recording_lock:
        current_time = datetime.now()
        stale_sessions = []
        
        for session_id, recording in active_recordings.items():
            # If recording has been active for more than 5 minutes, clean it up
            duration = (current_time - recording['start_time']).total_seconds()
            if duration > 300:  # 5 minutes
                stale_sessions.append(session_id)
        
        for session_id in stale_sessions:
            print(f"Cleaning up stale recording session: {session_id}")
            del active_recordings[session_id]
        
        return len(stale_sessions)

# Start cleanup thread
def start_cleanup_thread():
    """
    Start a background thread to clean up stale recordings
    """
    def cleanup_loop():
        while True:
            time.sleep(60)  # Check every minute
            cleaned = cleanup_stale_recordings()
            if cleaned > 0:
                print(f"Cleaned up {cleaned} stale recording sessions")
    
    cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()
    print("Started recording cleanup thread")

# Initialize cleanup on module load
start_cleanup_thread()