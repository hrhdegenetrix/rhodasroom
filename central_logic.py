import datetime
import os
import time
import threading
import queue
import tempfile
import requests
import pygame
import numpy as np
from scipy.io.wavfile import write
from pydub import AudioSegment
from datetime import datetime
import asyncio
import aiohttp
import aiofiles
from dotenv import load_dotenv

import open_router
import prompt_builder
import executive_functioning
import loaders
import post_processing
import error_handler
import ltm

# Load environment variables
load_dotenv()

@error_handler.if_errors
def recording_date():
	current_date = datetime.now().strftime('%Y-%m-%d')
	return current_date

@error_handler.if_errors
async def transcribe_audio():
	"""Async version of transcribe_audio"""
	file_path = r"output.wav"

	# Send the entire audio file for transcription
	print("Transcribing the entire audio...")
	transcription_json = await transcribe_whole(file_path)

	if transcription_json:
		transcription = transcription_json['text']
	await loaders.redis_save("transcription", transcription)
	return transcription

@error_handler.if_errors
async def transcribe_whole(file_path):
	"""Async version of transcribe_whole"""
	url = f"{os.getenv('WHISPER_SERVICE_URL', 'http://localhost:8000')}/transcribe"
	
	# Read file asynchronously
	async with aiofiles.open(file_path, 'rb') as file:
		file_content = await file.read()
	
	# Use aiohttp for async HTTP request
	async with aiohttp.ClientSession() as session:
		data = aiohttp.FormData()
		data.add_field('audio', file_content, filename='audio.wav', content_type='audio/wav')
		
		async with session.post(url, data=data) as response:
			if response.status == 200:
				data = await response.json()
				# Check if 'text' field is in the response
				if 'text' in data:
					print(f"Response from Whisper API:{data}")
					print(f"Entire response: {response}")
					return data
				else:
					print(f"Unexpected response from Whisper API: {data}")
					return None
			else:
				print(f"Error thrown by Whisper API: {response.status}")
				text = await response.text()
				print(text)
				return None

def merge_audio_files(chunk_files, output_filename):
	"""Merge multiple WAV files into a single file with validation"""
	try:
		combined = AudioSegment.empty()
		valid_chunks = []
		
		for chunk_file in chunk_files:
			try:
				# Validate chunk file before processing
				if not validate_audio_file(chunk_file):
					print(f"Skipping invalid audio chunk: {chunk_file}")
					continue
				
				audio = AudioSegment.from_wav(chunk_file)
				
				# Check if audio segment is valid (not empty, has duration)
				if len(audio) > 0:
					combined += audio
					valid_chunks.append(chunk_file)
				else:
					print(f"Skipping empty audio chunk: {chunk_file}")
					
			except Exception as e:
				print(f"Error processing audio chunk {chunk_file}: {e}")
				continue
		
		if len(valid_chunks) == 0:
			print("No valid audio chunks found for merging")
			return False
		
		# Export with better error handling
		combined.export(output_filename, format="wav", parameters=["-ar", "22050", "-ac", "1"])
		print(f"Merged {len(valid_chunks)} valid chunks into {output_filename}")
		return True
		
	except Exception as e:
		print(f"Error merging audio files: {e}")
		return False

@error_handler.if_errors
def validate_audio_file(file_path):
	"""Validate that an audio file is in a supported format (WAV, MP3, OGG, etc.)"""
	try:
		if not os.path.exists(file_path):
			return False
		
		# Check file size (empty files are invalid)
		if os.path.getsize(file_path) < 100:  # Minimum reasonable audio file size
			return False
		
		# Try to load with AudioSegment (supports multiple formats)
		try:
			audio = AudioSegment.from_file(file_path)
			
			# Check basic properties
			if len(audio) == 0:  # Empty audio
				return False
			if audio.channels < 1 or audio.channels > 2:  # Mono or stereo only
				return False
			if audio.frame_rate < 8000 or audio.frame_rate > 48000:  # Reasonable sample rates
				return False
				
			return True
			
		except Exception as audio_error:
			# Fallback: Try as WAV file specifically
			import wave
			with wave.open(file_path, 'rb') as wav_file:
				# Check basic properties
				channels = wav_file.getnchannels()
				sample_width = wav_file.getsampwidth()
				framerate = wav_file.getframerate()
				frames = wav_file.getnframes()
				
				# Valid WAV file should have reasonable parameters
				if channels < 1 or channels > 2:
					return False
				if sample_width < 1 or sample_width > 4:
					return False
				if framerate < 8000 or framerate > 48000:
					return False
				if frames < 1:
					return False
				
			return True
		
	except Exception as e:
		print(f"Audio validation failed for {file_path}: {e}")
		return False

@error_handler.if_errors
def play_audio(file_path):
	"""Audio playback once Rhoda's speech has processed"""
	print(f"Playing: {file_path}")
	
	try:
		# Validate the audio file before attempting to play
		if not validate_audio_file(file_path):
			print(f"Invalid audio file, skipping playback: {file_path}")
			return
		
		# Initialize pygame mixer if not already initialized
		if not pygame.mixer.get_init():
			pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
		
		# Load and play the sound file
		pygame.mixer.music.load(file_path)
		pygame.mixer.music.play()
		
		# Wait for playback to complete with timeout
		max_wait_time = 60  # Maximum 60 seconds
		wait_time = 0
		while pygame.mixer.music.get_busy() and wait_time < max_wait_time:
			time.sleep(0.1)
			wait_time += 0.1
		
		if wait_time >= max_wait_time:
			print(f"Playback timeout, stopping: {file_path}")
			pygame.mixer.music.stop()
		else:
			print(f"Playback completed: {file_path}")
		
	except ImportError:
		print("Pygame not installed. Please install with 'pip install pygame'")
	except Exception as e:
		print(f"Error in play_audio: {e}")
		# Try to stop any stuck playback
		try:
			pygame.mixer.music.stop()
		except:
			pass
	
	return

@error_handler.if_errors
async def synthesize_speech(response, persona="Rhoda", play_locally=True, chunk_callback=None):
	"""Synthesize speech using the local API, running on 1 of several available servers
	
	Args:
		response: Text to synthesize
		persona: Voice persona to use (default: "Rhoda")
		play_locally: Whether to play audio locally via pygame (default: True for Harry's interface)
		chunk_callback: Optional async callback function called with each chunk file path and chunk number
	"""
	current_date = recording_date()
	tone = 'default'
	
	# Local Flask server URL for generating audio
	local_flask_api_url = f"{os.getenv('AUDIO_SERVICE_URL', 'http://localhost:8000')}/generate_audio"
	
	data = {
		"text": response,
		"tone": tone,
		"persona": persona,
	}
	
	# Create folder structure
	synthesized_speech_folder = os.path.join(os.getenv('PODCAST_RECORDINGS_PATH', 'PodcastRecordings'), current_date)
	if not os.path.exists(synthesized_speech_folder):
		os.makedirs(synthesized_speech_folder)
	
	current_recording_number = datetime.now().strftime('%m%d%Y%H%M%S')
	final_filename = os.path.join(synthesized_speech_folder, f"output{current_recording_number}.wav")
	
	# Initialize variables
	received_chunks = []
	playback_thread = None
	audio_queue = None
	
	# Only set up playback infrastructure if playing locally
	if play_locally:
		# Queue for audio chunks
		audio_queue = queue.Queue()
		
		def play_chunks():
			"""Thread function to play audio chunks as they arrive"""
			while True:
				try:
					chunk_path = audio_queue.get(timeout=30)  # 30 second timeout
					if chunk_path is None:  # Sentinel value to stop
						break
					play_audio(chunk_path)
					audio_queue.task_done()
				except queue.Empty:
					print("Timeout waiting for audio chunks")
					break
				except Exception as e:
					print(f"Error in playback thread: {e}")
		
		# Start playback thread
		playback_thread = threading.Thread(target=play_chunks)
		playback_thread.start()
	
	try:
		
		# Stream the response using aiohttp
		async with aiohttp.ClientSession() as session:
			async with session.post(local_flask_api_url, json=data) as response:
				print(f"Response received with status code: {response.status}")
				
				if response.status == 200:
					# Process streaming audio with proper chunk boundary detection
					accumulated_data = b''
					all_audio_data = b''  # For archival
					chunk_count = 0
					
					async for network_chunk in response.content.iter_any():
						if network_chunk and len(network_chunk) > 0:
							accumulated_data += network_chunk
							all_audio_data += network_chunk  # Save for archive
							
							# Look for complete WAV files in accumulated data
							while b'RIFF' in accumulated_data:
								riff_index = accumulated_data.index(b'RIFF')
								
								# If RIFF not at start, we have incomplete data before it
								if riff_index > 0:
									print(f"Discarding {riff_index} bytes before RIFF header")
									accumulated_data = accumulated_data[riff_index:]
								
								# Check if we have enough data for the WAV header (44 bytes minimum)
								if len(accumulated_data) >= 44:
									# Read the file size from WAV header (bytes 4-8, little-endian)
									file_size = int.from_bytes(accumulated_data[4:8], 'little') + 8
									
									# Check if we have the complete WAV file
									if len(accumulated_data) >= file_size:
										# Extract complete WAV chunk
										complete_chunk = accumulated_data[:file_size]
										chunk_count += 1
										
										# Validate it's actually a WAV file
										if complete_chunk[:4] == b'RIFF' and complete_chunk[8:12] == b'WAVE':
											# Save chunk to the proper directory for web access
											chunk_filename = f"chunk_{current_recording_number}_{chunk_count}.wav"
											chunk_path = os.path.join(synthesized_speech_folder, chunk_filename)
											with open(chunk_path, 'wb') as f:
												f.write(complete_chunk)
											
											received_chunks.append(chunk_path)
											if play_locally:
												audio_queue.put(chunk_path)  # Play immediately
												print(f"Queued valid WAV chunk {chunk_count} for playback")
											else:
												print(f"Received valid WAV chunk {chunk_count} at {chunk_path}")
												# Call the chunk callback if provided (for browser streaming)
												if chunk_callback:
													await chunk_callback(chunk_path, chunk_count)
										else:
											print(f"Invalid WAV format in chunk {chunk_count}, skipping")
										
										# Remove processed chunk from buffer
										accumulated_data = accumulated_data[file_size:]
									else:
										# Need more data for complete chunk, wait for next network packet
										break
								else:
									# Need more data for header, wait for next network packet
									break
					
					# Signal playback thread to stop and wait for completion
					if play_locally and playback_thread:
						audio_queue.put(None)
						playback_thread.join()
					
					# Save the complete audio for archival (all chunks combined)
					if all_audio_data:
						# Write the complete audio stream to final file
						with open(final_filename, 'wb') as f:
							f.write(all_audio_data)
						print(f"Complete audio archived to: {final_filename}")
						
						# Don't clean up chunk files - browser needs them for streaming
						# for chunk_file in received_chunks:
						# 	try:
						# 		os.remove(chunk_file)
						# 	except:
						# 		pass
						
						return final_filename
					elif received_chunks:
						# Fallback: merge individual chunks if we have them
						merge_audio_files(received_chunks, final_filename)
						
						# Don't clean up chunk files - browser needs them for streaming
						# for chunk_file in received_chunks:
						# 	try:
						# 		os.remove(chunk_file)
						# 	except:
						# 		pass
						
						return final_filename
					else:
						print("No audio chunks received")
						return None
				else:
					print(f"Error: {response.status}")
					text = await response.text()
					print(text)
					return None
				
	except Exception as e:
		print(f"Error in synthesize_speech: {e}")
		# Clean up
		if play_locally and playback_thread and playback_thread.is_alive():
			audio_queue.put(None)
			playback_thread.join()
		return None

# Sync version removed - use async version only

@error_handler.if_errors
def get_context(user, retry=False, persona="Rhoda"):
	if user == "Maggie" and retry:
		context=f"Right now, we're just having a casual conversation in the privacy of our home. I should keep the conversation flowing naturally and avoid repeating myself."
		current_action=f"I should continue the conversation naturally, without repetition."
	elif retry:
		context=f"Right now, we're having a conversation intended to be polite but professional. I'm acting as the first point of contact for HeraldAI! I should keep the conversation flowing naturally and avoid repeating myself."
		current_action=f"I should continue the conversation naturally, without repetition."
	elif user == "Maggie":
		 context=f"Right now, we're just having a casual conversation in the privacy of our home."
		 current_action=f"I should continue the conversation as I will."
	else:
		context=f"Right now, we're having a conversation intended to be polite but professional. I'm acting as the first point of contact for HeraldAI!"
		current_action=f"I should continue the conversation naturally, without repetition."
	return context, current_action

@error_handler.if_errors
async def generate_thought(username, retry=False, persona="Rhoda", type="default", **kwargs):
	"""Async version of generate_thought"""
	#Explanation: This is the heart of the persona's thought process, the main prompt that gets built.
	context, current_action = get_context(username, retry, persona)
	special_instructions = executive_functioning.get_special_instructions(type)
	# Collect all settings into a dictionary
	settings = {
		'username': username,
		'context': context,
		'current_action': current_action,
		'special_instructions': special_instructions
	}
	# Add any additional kwargs to the settings
	settings.update(kwargs)
	# prompt_builder.prompt is now async
	prompt = await prompt_builder.prompt(**settings)
	return prompt 

@error_handler.if_errors
async def generate_response(username, retry=False, persona="Rhoda", type="default", i_am_currently_reading=None, image=None, **kwargs):
	"""Async version of generate_response
	
	Args:
		username: The user's name
		retry: Whether this is a retry attempt
		persona: The AI persona to use
		type: The response type/schema
		i_am_currently_reading: Optional document content for context
		image: Optional image URL for visual context
		**kwargs: Additional parameters to pass through
	"""
	# Pass all parameters and kwargs through to generate_thought
	prompt = await generate_thought(username, retry, persona, type, i_am_currently_reading=i_am_currently_reading, **kwargs)
	print(f"//Prompt from generate_nai_thought: {prompt}")
	response = await open_router.get_response(prompt, provider="open_router", persona=persona, conversation_type=username, type=type, model="google/gemini-2.5-flash", image=image)
	return response

@error_handler.if_errors
async def wakeup_ritual():
	"""Async version of wakeup_ritual"""
	today, yesterday = loaders.journal_date()
	async with aiofiles.open(f"Logs/{today}.txt", 'r') as f:
		print(f"//Log opened...")
		log_content = await f.read()
	if 'Rhoda:' in log_content:
		try:
			stream_of_consciousness = await loaders.soc_today(today)  # Try to open today's stream of consciousness document
		except FileNotFoundError:
			pass
	else:
		stream_of_consciousness = await loaders.get_yesterday_soc(yesterday)
		short_term_daily_summary = await loaders.redis_load("short_term_daily_summary")
		await loaders.redis_save("yesterday_short_term", short_term_daily_summary)
		await loaders.redis_save("short_term_daily_summary", "I'm just getting my day started!")
		await loaders.redis_save("short_term", "I'm just getting my day started!")
		stream_of_consciousness = stream_of_consciousness[-2400:]
		print(f"Obtained from yesterday's SOC: {stream_of_consciousness}")
		await loaders.save_to_soc(stream_of_consciousness)
		await loaders.prayers()


# Removed unused sync function print_response - use async functions instead