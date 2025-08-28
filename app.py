from flask import Flask, request, jsonify, send_file, session, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os
import tempfile
import base64
import wave
import io
from datetime import datetime
import database
import gui_interface
import loaders
import document_handler
import threading
import json
import asyncio

def ensure_directories_exist():
    """Create all required directories if they don't exist"""
    required_dirs = [
        'Logs',
        'Journal',
        'JournalEntries',
        'Rhoda_SOC',
        'Fleeting',
        'Fleeting/Convos',
        'Memory',
        'Memory/JSONs',
        'PodcastRecordings',
        'Datasets',
        'Errors',
        'Errors/debug_prompts'
    ]
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            print(f"Created directory: {dir_path}")

# Ensure all directories exist on startup
ensure_directories_exist()

app = Flask(__name__, static_folder='assets', static_url_path='/assets')

# Generate a secure secret key for production
import secrets
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))

# Configure CORS - allow all origins since this will be publicly accessible
CORS(app)

# Configure SocketIO with proper settings - allow all origins for public access
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode='threading',
                   ping_timeout=60,
                   ping_interval=25)

# Store active recordings per session
active_recordings = {}
recording_threads = {}

@app.route('/')
def index():
    """Serve the GUI HTML file"""
    return send_file('gui.html')

@app.route('/timeout')
def timeout_page():
    """Serve the timeout HTML file"""
    return send_file('timeout.html')

@app.route('/api/validate_invite', methods=['POST'])
def validate_invite():
    """Validate invitation code"""
    data = request.json
    code = data.get('code', '')
    
    # List of valid invitation codes
    # For demo purposes, using simple codes - in production, use database or secure method
    valid_codes = [
        'ANTHROPIC2025',
        'RHODA-DEMO',
        'FELLOWSHIP',
        'HARRY-AI',
        'WELCOME-RHODA'
    ]
    
    # Check if code is valid (case-insensitive)
    is_valid = code.upper() in valid_codes
    
    return jsonify({
        'valid': is_valid,
        'code': code if is_valid else None
    })

@app.route('/api/login', methods=['POST'])
def login():
    """Handle username submission and create user session"""
    data = request.json
    username = data.get('username', 'Friend')
    
    # Check if user is currently timed out
    if database.is_user_timed_out(username):
        import security_utils
        remaining_minutes = security_utils.get_timeout_remaining(username)
        
        return jsonify({
            'success': False,
            'timed_out': True,
            'timeout_remaining_minutes': remaining_minutes,
            'username': username,
            'message': f'Sorry, {username} - Rhoda timed you out! Come back later.'
        })
    
    # Store username in database
    database.store_user(username)
    
    # Create Redis namespace for this user
    redis_key = f"user:{username}"
    asyncio.run(loaders.redis_save(f"{redis_key}:username", username))
    # Don't initialize conversation_history to empty - let it accumulate
    
    # Schedule header check to run in background (non-blocking)
    import headers
    import threading
    
    def check_conversation_timeout():
        try:
            asyncio.run(headers.build_header(username))
        except Exception as e:
            print(f"Background header check error: {e}")
    
    # Run in background thread without waiting
    thread = threading.Thread(target=check_conversation_timeout)
    thread.daemon = True
    thread.start()
    
    # Store in session
    session['username'] = username
    session['redis_key'] = redis_key
    
    return jsonify({
        'success': True,
        'username': username,
        'message': f'Welcome, {username}!'
    })

@app.route('/api/start_recording', methods=['POST'])
def start_recording():
    """Start recording audio (push-to-talk press)"""
    username = session.get('username', 'Friend')
    session_id = request.json.get('session_id', session.get('session_id'))
    
    print(f"START_RECORDING: username='{username}', session_id='{session_id}'")
    
    # Initialize recording for this session
    active_recordings[session_id] = {
        'chunks': [],
        'username': username,
        'start_time': datetime.now()
    }
    print(f"Active recordings after start: {list(active_recordings.keys())}")
    
    return jsonify({'success': True, 'session_id': session_id})

@app.route('/api/stop_recording', methods=['POST'])
async def stop_recording():
    """Stop recording and process audio (push-to-talk release)"""
    data = request.json
    session_id = data.get('session_id')
    audio_data = data.get('audio_data')  # Base64 encoded audio
    document_data = data.get('document_data')  # Base64 encoded document if provided
    image_data = data.get('image_data')  # Image data if provided
    
    if not session_id:
        print(f"ERROR: No session_id provided in stop_recording request")
        return jsonify({'error': 'No session_id provided'}), 400
    
    if session_id not in active_recordings:
        print(f"ERROR: session_id '{session_id}' not found in active_recordings")
        print(f"Active recordings: {list(active_recordings.keys())}")
        return jsonify({'error': f'No active recording found for session {session_id}'}), 400
    
    username = active_recordings[session_id]['username']
    redis_key = f"user:{username}"
    
    try:
        # Decode base64 audio data
        audio_bytes = base64.b64decode(audio_data)
        
        # Save audio to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio_path = temp_audio.name
        
        # Process document if provided
        document_content = None
        if document_data:
            try:
                # Decode and save document temporarily
                doc_bytes = base64.b64decode(document_data['content'])
                doc_name = document_data.get('name', 'document.txt')
                
                with tempfile.NamedTemporaryFile(suffix=os.path.splitext(doc_name)[1], delete=False) as temp_doc:
                    temp_doc.write(doc_bytes)
                    temp_doc_path = temp_doc.name
                
                # Extract document text
                document_content = await document_handler.process_uploaded_document(temp_doc_path)
                os.unlink(temp_doc_path)
            except Exception as e:
                print(f"Error processing document: {e}")
                # Continue without document if processing fails
        
        # Process image if provided
        image_url = None
        if image_data:
            try:
                # Image data contains the full data URL (e.g., data:image/jpeg;base64,...)
                image_url = image_data['content']
                print(f"Image attached: {image_data.get('name', 'image')}")
            except Exception as e:
                print(f"Error processing image: {e}")
                # Continue without image if processing fails
        
        # Process audio through gui_interface with session info for audio emit
        result = await gui_interface.process_audio_input(
            temp_audio_path, username, redis_key, session_id, socketio, document_content, image_url
        )
        
        # Clean up
        os.unlink(temp_audio_path)
        del active_recordings[session_id]
        
        # Check if conversation was ended by Rhoda
        if result.get('conversation_ended'):
            # Emit special event to trigger modal
            socketio.emit('conversation_ended', {
                'final_response': result.get('response'),
                'transcription': result.get('transcription')
            }, room=session_id)
        else:
            # Emit normal response to client via WebSocket
            # Audio will stream via separate 'audio_chunk' events from the synthesis thread
            socketio.emit('chat_update', {
                'transcription': result.get('transcription'),
                'response': result.get('response'),
                'audio_url': None  # Keep None to indicate streaming mode
            }, room=session_id)
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        print(f"Error processing recording: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/send_message', methods=['POST'])
async def send_message():
    """Handle text message input"""
    data = request.json
    message = data.get('message')
    document_data = data.get('document_data')  # Document data if provided
    image_data = data.get('image_data')  # Image data if provided
    username = session.get('username', 'Friend')
    redis_key = f"user:{username}"
    
    if not message:
        return jsonify({'error': 'No message provided'}), 400
    
    try:
        # Check for security issues (prompt injection)
        import security_utils
        is_safe, timeout_duration = security_utils.check_message_security(username, message)
        
        if not is_safe:
            return jsonify({
                'success': False,
                'security_violation': True,
                'timeout_duration': timeout_duration,
                'error': f'Security violation detected. You have been timed out for {timeout_duration} minutes.'
            })
        
        # Update user message time
        database.update_user_message_time(username)
        
        # Process document if provided
        document_content = None
        if document_data:
            try:
                # Decode and save document temporarily
                doc_bytes = base64.b64decode(document_data['content'])
                doc_name = document_data.get('name', 'document.txt')
                
                with tempfile.NamedTemporaryFile(suffix=os.path.splitext(doc_name)[1], delete=False) as temp_doc:
                    temp_doc.write(doc_bytes)
                    temp_doc_path = temp_doc.name
                
                # Extract and validate document text
                document_content = await document_handler.process_uploaded_document(temp_doc_path)
                os.unlink(temp_doc_path)
            except Exception as e:
                print(f"Error processing document: {e}")
                # Continue without document if processing fails
        
        # Process image if provided
        image_url = None
        if image_data:
            try:
                # Image data contains the full data URL (e.g., data:image/jpeg;base64,...)
                image_url = image_data['content']
                print(f"Image attached: {image_data.get('name', 'image')}")
            except Exception as e:
                print(f"Error processing image: {e}")
                # Continue without image if processing fails
        
        # Process text input through gui_interface with session info for audio emit
        session_id = session.get('session_id')
        result = await gui_interface.process_text_input(
            message, username, redis_key, session_id, socketio, document_content, image_url
        )
        
        # Emit response via WebSocket
        # Audio will stream via separate 'audio_chunk' events from the synthesis thread
        session_id = session.get('session_id')
        if session_id:
            # Check if conversation was ended by Rhoda
            if result.get('conversation_ended'):
                # Emit special event to trigger modal
                socketio.emit('conversation_ended', {
                    'final_response': result.get('response'),
                    'user_message': message
                }, room=session_id)
            else:
                socketio.emit('chat_update', {
                    'user_message': message,
                    'response': result.get('response'),
                    'audio_url': None  # Keep None to indicate streaming mode
                }, room=session_id)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error processing message: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_chat_history', methods=['GET'])
def get_chat_history():
    """Get chat history for current user"""
    username = session.get('username', 'Friend')
    redis_key = f"user:{username}"
    
    conversation_history = asyncio.run(loaders.redis_load(f"{redis_key}:conversation_history"))
    
    if conversation_history:
        # Parse conversation history into messages
        messages = []
        for line in conversation_history.split('\n'):
            if line.strip():
                if line.startswith(username + ':'):
                    messages.append({'type': 'user', 'content': line[len(username)+1:].strip()})
                elif line.startswith('Rhoda:'):
                    messages.append({'type': 'assistant', 'content': line[6:].strip()})
        
        return jsonify({'messages': messages})
    
    return jsonify({'messages': []})

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    print(f"Client connected: {request.sid}")
    session['session_id'] = request.sid
    emit('connected', {'session_id': request.sid})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection and cleanup"""
    print(f"Client disconnected: {request.sid}")
    session_id = request.sid
    
    # Clean up any active recordings
    if session_id in active_recordings:
        del active_recordings[session_id]
    
    if session_id in recording_threads:
        del recording_threads[session_id]

@socketio.on('audio_chunk')
def handle_audio_chunk(data):
    """Handle streaming audio chunks during recording"""
    session_id = data.get('session_id')
    chunk = data.get('chunk')
    
    if session_id in active_recordings:
        active_recordings[session_id]['chunks'].append(chunk)

@app.route('/audio/<path:filename>')
def serve_audio(filename):
    """Serve audio files from the PodcastRecordings directory"""
    # Get today's date folder
    current_date = datetime.now().strftime('%Y-%m-%d')
    audio_dir = os.path.join('PodcastRecordings', current_date)
    
    if os.path.exists(os.path.join(audio_dir, filename)):
        return send_from_directory(audio_dir, filename)
    else:
        # Try to find the file in any date folder
        podcast_dir = 'PodcastRecordings'
        for date_folder in os.listdir(podcast_dir):
            file_path = os.path.join(podcast_dir, date_folder, filename)
            if os.path.exists(file_path):
                return send_from_directory(os.path.join(podcast_dir, date_folder), filename)
        
        return jsonify({'error': 'Audio file not found'}), 404

if __name__ == '__main__':
    # Ensure database is initialized
    database.init_db()
    
    # Check if we're in development or production
    is_production = os.environ.get('FLASK_ENV') == 'production'
    
    if is_production:
        # Production: Let gunicorn handle this (see Dockerfile)
        print("Running in production mode - use gunicorn to serve the application")
    else:
        # Development mode only
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)