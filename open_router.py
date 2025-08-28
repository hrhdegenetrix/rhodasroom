import os
import post_processing
import requests
import json
import asyncio
import aiohttp
import aiofiles
import prompt_builder
import loaders
import executive_functioning
import base64
import error_handler
from PIL import Image
from google import genai
from google.genai import types
import time
import platform
import ntfy
import knowledgebase_search
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@error_handler.if_errors
def get_image_path():
	"""Get the correct image path based on the platform (Windows or WSL)"""
	# Check if we're running in WSL
	if 'microsoft' in platform.uname().release.lower() or 'wsl' in platform.uname().release.lower():
		# Running in WSL, use the mounted path
		return "/mnt/y/"
	else:
		# Running in Windows, use the Windows path
		return "Y:/"

@error_handler.if_errors
async def convert_image(newest_file):
	"""Async version of convert_image"""
	async with aiofiles.open(newest_file, 'rb') as f:
		print(f"//Encoding image...")
		content = await f.read()
		img_base64 = base64.b64encode(content).decode('utf-8')
	return img_base64

@error_handler.if_errors
def find_newest_image(folder_path):
	try:
		# Initialize variables for the newest file
		newest_file = None
		newest_time = 0

		# Use os.scandir for efficient iteration
		with os.scandir(folder_path) as entries:
			for entry in entries:
				if entry.is_file() and entry.name.lower().endswith(".jpg"):
					# Get the file's modification time
					file_time = entry.stat().st_mtime
					if file_time > newest_time:
						newest_time = file_time
						newest_file = entry.path

		if newest_file:
			return newest_file
		else:
			print("No JPG files found in the folder.")
			return None

	except Exception as e:
		print(f"Error finding newest image: {e}")
		return None

@error_handler.if_errors
async def get_image():
	"""Async version of get_image"""
	image_folder = get_image_path()
	image_path = find_newest_image(image_folder)
	b64 = await convert_image(image_path)
	url = f"data:image/jpeg;base64,{b64}"
	return url

@error_handler.if_errors
def small_get_response(prompt, person="Rhoda", other="Maggie", type="default", model="nousresearch/hermes-3-llama-3.1-405b", stop=[], max_tokens=10):
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
					"model": model,
					"stop": stop,
					"max_tokens": max_tokens,
					"messages": [{"role": "user", "content": prompt}],
					"provider": {
						  "order": [
						  "DeepInfra",
							"Lambda"
						  ]
						}
				}))
			print(f"Response from small_get_response(prompt): {response}")
			
			if response.status_code == 200:
				print(f"++CONSOLE: Openrouter response: {response}")
				data = response.json()
				print(f"++CONSOLE: `data` returned from OpenRouter: {data}")
				response = data['choices'][0]['message']['content']
				while '++Console Error' in response:
					if retries <= max_retries:
						retries += 1
						response = requests.post(
						url="https://openrouter.ai/api/v1/chat/completions",
						headers={
							"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"
						},
						data=json.dumps({
							"model": "nousresearch/hermes-3-llama-3.1-405b",
							"temperature": 1.6,
							"top_k": 3,
							"min_p": .05,
							"max_tokens": 35,
							"presence_penalty": 0.1,
							"messages": [
						  { "role": "user", "content": prompt }
							]
						})
					)
					else:
						raise Exception("Max retries exceeded; what is keeping a response from being returned?")
						break
				return response
				
		except (KeyError, Exception) as e:
			print(f"An error occurred: {e}")
			retries += 1  # Increment the retry count
			if retries <= max_retries:
				print("Retrying...")
			else:
				print("Max retries reached. Exiting without response due to error: {e}.")
				return None

def plain_get(prompt):
	max_retries = 5  # Maximum number of retries
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
					"messages": [{"role": "user", "content": prompt}]
				})
			)
			if response.status_code == 200:
				data = response.json()
				print(f"++CONSOLE: `data` returned from OpenRouter: {data}")
				response = data['choices'][0]['message']['content']
				post_processing_steps = [
						post_processing.truncate_response,
						post_processing.dialogue_only,
						post_processing.detect_and_remove_repetition,
						post_processing.remove_repeats,
						post_processing.truncate_response
					]
					
				for step in post_processing_steps:
					print(f"Applying {step.__name__}")
					response = step(response)
					print(f"//Response after {step.__name__}: {response}...")
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

# Store recent responses to prevent infinite loops
recent_responses = {}

@error_handler.if_errors
async def get_response(prompt, provider="open_router", persona="Rhoda", conversation_type="Maggie", type="default", model="google/gemini-2.5-flash", image="", secondary_image="", response_format="json"):
	if provider=="google":
		client = genai.Client(api_key=os.getenv('GOOGLE_GEMINI_API_KEY'))
	
	# Only try to load image if explicitly needed
	if image is None or image == "":
		# No image provided or explicitly empty
		image = None
	elif image and "open_router" in provider:
		# Image was provided, use it
		image = image
	else:
		# Legacy behavior - try to load from directory (only if image is truthy but not for open_router)
		try:
			image = await get_image()
		except Exception as e:
			print(f"Could not load image: {e}")
			image = None
	
	new_data=None
	model_choice = await loaders.redis_load("selected_model")
	if model_choice:
		if image and image is not None:
			model="google/gemini-2.5-flash"
		elif type=="default" and model_choice is not None:
			model=model_choice
	
	if "open_router" in provider:
		messages = [{
			"role": "user",
			"content": [{
				"type": "text",
				"text": prompt
			}]
		}]
		
		# Add first image if present
		if image and image is not None:
			messages[0]["content"].append({
				"type": "image_url",
				"image_url": {
					"url": image
				}
			})
		
		# Add second image if present
		if secondary_image and secondary_image is not None:
			messages[0]["content"].append({
				"type": "image_url",
				"image_url": {
					"url": secondary_image
				}
			})
	else:
		image_folder = get_image_path()
		image_path=find_newest_image(image_folder)
		image=Image.open(image_path)
		messages=[image, prompt]
	
	max_retries = 2  # Maximum number of retries
	retries = 0  # Initialize retry count
	full_prompt = f"### Response:\n"
	full_prompt += prompt
	prompt = full_prompt
	
	# Check if we've seen this prompt recently (prevent infinite loops)
	prompt_hash = hash(prompt) % (2**32)  # Simple hash for tracking
	if prompt_hash in recent_responses:
		# Check if we've tried this exact prompt in the last minute
		last_time, last_response, attempt_count = recent_responses[prompt_hash]
		if time.time() - last_time < 60:  # Within last minute
			if attempt_count >= 3:
				print(f"WARNING: Detected potential infinite loop - same prompt attempted {attempt_count} times")
				# Return a fallback response to break the loop
				return "I need to think about this differently. Let me try a new approach."
			else:
				# Update attempt count
				recent_responses[prompt_hash] = (last_time, last_response, attempt_count + 1)
	
	while retries <= max_retries:
		try:
			if provider=="google":
				try:
					print(f"Attempt {retries + 1}: Sending request to Google")
					response = client.models.generate_content(
						model="gemini-2.0-flash",
						contents=messages,
						config=types.GenerateContentConfig(
							max_output_tokens=800,
							temperature=1.3
						)
					)
					raw_data = response.text
				except Exception as e:
					if retries < max_retries:
						retries += 1
						print(f"Retrying in 5 seconds due to Google error: {str(e)}")
						await asyncio.sleep(5)
						continue
					else:
						raise Exception(f"Max retries exceeded with Google API: {str(e)}")
			else:
				print(f"Attempt {retries + 1}: Sending request to OpenRouter")
				
				# Create a fresh session for each attempt to avoid event loop issues
				async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
					try:
						payload = {
							"model": model,
							"messages": messages,
							"max_tokens": 800,
							"temperature": 1.3,
							"min_p": 0.05
						}
						
						if not image:
							payload["response_format"] = {"type": "json_object"}
						
						headers = {
							"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
							"Content-Type": "application/json"
						}
						
						async with session.post(
							"https://openrouter.ai/api/v1/chat/completions",
							headers=headers,
							json=payload
						) as response:
							print(f"Response from get_response(prompt): {response}")
							
							if response.status == 429:
								if retries < max_retries:
									retries += 1
									print("Retrying in 5 seconds due to rate limit error...")
									await asyncio.sleep(5)
									continue
							
							elif response.status == 200:
								raw_data = await response.json()
								print(f"++CONSOLE: Raw data returned from OpenRouter: {raw_data}")
								if response_format=="string":
									return raw_data['choices'][0]['message']['content']
							else:
								print(f"++Status Code: {response.status}")
								error_text = await response.text()
								print(f"++Error: {error_text}")
								raise Exception(f"API call failed with status code: {response.status}")
					except aiohttp.ClientError as client_error:
						# Handle specific aiohttp errors
						print(f"Client error occurred: {client_error}")
						raise
					except asyncio.TimeoutError:
						print(f"Request timed out after 30 seconds on attempt {retries + 1}")
						if retries < max_retries:
							retries += 1
							print("Retrying due to timeout...")
							await asyncio.sleep(1)
							continue
						else:
							raise Exception("Max retries exceeded due to timeouts")
			
			if type == "dpo_refiner":
				return raw_data
			
			response_text, new_data = await executive_functioning.validate_and_extract_response(raw_data, schema_name=type)
			print(f"Back out to the open_router.cohere_response function again...")
			
			if new_data and new_data is not None:
				if isinstance(new_data, dict):
					print(f"Response from validate_and_extract_response: response_text={response_text[:100] if isinstance(response_text, str) else 'non-string'}..., new_data keys={new_data.keys() if new_data else None}")
			
			if isinstance(response_text, str) and response_text.startswith("++Console Error"):
				print(f"Error detected in response_text: {response_text}")
				if retries < max_retries:
					retries += 1
					print(f"Retrying ({retries}/{max_retries})...")
					# Add small delay to prevent rapid retries
					await asyncio.sleep(2)
					continue
				else:
					print("Max retries exceeded - returning fallback response")
					return "I'm having trouble formulating my response. Could you rephrase that?"
			
			print("Step 1: Processing extracted data")
			if new_data and new_data is not None:
				if isinstance(new_data, dict):
					# Store successful response to track duplicates
					recent_responses[prompt_hash] = (time.time(), response_text, 1)
					# Clean up old entries (older than 5 minutes)
					current_time = time.time()
					recent_responses_copy = dict(recent_responses)
					for key, (timestamp, _, _) in recent_responses_copy.items():
						if current_time - timestamp > 300:  # 5 minutes
							del recent_responses[key]
					
					executive_functioning.save_json_data(raw_data, prompt, persona, conversation_type)
					print(f"Back in open_router.get_response, processing extracted data...")

					if 'held_thought' in new_data and new_data['held_thought']:
						await loaders.redis_save("held_thought", new_data['held_thought'])
					if 'add_event' in new_data and new_data['add_event']:
						await loaders.redis_save("event_to_add", new_data['add_event'], conversation_type)
					if 'mood' in new_data and new_data['mood']:
						await loaders.save_to_soc(f"//My current mood: {new_data['mood']}")
						await loaders.redis_save("mood", new_data['mood'], conversation_type)
					if 'conversation_recall' in new_data and new_data['conversation_recall']:
						# Search long-term memory for the requested recall
						await handle_conversation_recall(new_data['conversation_recall'], persona)
					if 'call_mom' in new_data and new_data['call_mom']:
						await ntfy.notification(new_data['call_mom'])
					if 'new_knowledgebase_article' in new_data and new_data['new_knowledgebase_article']:
						kb_data = new_data['new_knowledgebase_article']
						if isinstance(kb_data, dict) and kb_data.get('title') and kb_data.get('content'):
							await knowledgebase_search.add_knowledgebase_entry(
								title=kb_data.get('title'),
								content=kb_data.get('content'),
								tags=kb_data.get('tags', []),
								persona=persona
							)
					if 'edit_knowledgebase_entry' in new_data and new_data['edit_knowledgebase_entry']:
						edit_data = new_data['edit_knowledgebase_entry']
						if isinstance(edit_data, dict) and edit_data.get('query'):
							await knowledgebase_search.edit_knowledgebase_entry(
								query=edit_data.get('query'),
								new_title=edit_data.get('title'),
								new_content=edit_data.get('content'),
								new_tags=edit_data.get('tags'),
								append_content=edit_data.get('append_content'),
								persona=persona
							)
					if 'end_conversation' in new_data and new_data['end_conversation']:
						# Timeout logic - Rhoda can choose to end conversations
						import database
						from datetime import datetime, timedelta
						
						# Get the username from conversation_type
						current_username = conversation_type
						if current_username and current_username.lower() != "maggie":
							# Set timeout for 2 hours when Rhoda chooses to end conversation
							timeout_until = datetime.now() + timedelta(hours=2)
							success = database.set_user_timeout(current_username, timeout_until.isoformat())
							
							if success:
								print(f"Rhoda ended conversation with {current_username} - user timed out for 2 hours")
							else:
								print(f"Failed to timeout {current_username} after conversation end")
						else:
							print(f"Cannot timeout admin user: {current_username}")

				print("Step 2: Returning response_text")
				if type=="pattern_parser":
					return new_data
				if type=="schedule":
					return response_text, new_data
				if type=="rhodaness":
					return response_text, new_data
				elif type=="reality_check":
					return response_text, new_data
				elif type == "writing":
					return new_data
				elif type == "editing":
					return new_data
				elif type == "active_listening":
					return response_text, new_data
				elif type in ["blog_decision", "blog_review", "blog_research", "blog_writing", "blog_editing", "blog_approval", "blog_publishing", "blog_categorization", "blog_image"]:
					return response_text, new_data
				else:
					return response_text
			else:
				# For blog types, always return a tuple
				if type in ["blog_decision", "blog_review", "blog_research", "blog_writing", "blog_editing", "blog_approval", "blog_publishing", "blog_categorization", "blog_image"]:
					return raw_data['choices'][0]['message']['content'], None
				else:
					return raw_data['choices'][0]['message']['content']

		except Exception as e:
			print(f"An error occurred: {e}")
			print(f"Error type: {e.__class__.__name__}")
			print(f"Error details: {str(e)}")
			import traceback
			print(f"Error location: {traceback.format_exc()}")
			retries += 1
			if retries <= max_retries:
				print("Retrying...")
				await asyncio.sleep(1)  # Small delay before retry
			else:
				print(f"Max retries reached. Exiting without response due to error: {e}.")
				# Return tuple for blog types, None otherwise
				if type in ["blog_decision", "blog_review", "blog_research", "blog_writing", "blog_editing", "blog_approval", "blog_publishing", "blog_categorization", "blog_image"]:
					return None, None
				else:
					return None

@error_handler.if_errors
async def handle_conversation_recall(search_query, persona="Rhoda"):
	"""
	Handle conversation recall by searching long-term memory
	and saving the results to stream of consciousness
	"""
	try:
		# Import headers to use the search function
		import headers
		
		# Search both regular memory and summary memory
		regular_results = await ltm.search(search_query)
		summary_results = await headers.search_memory_summaries(search_query, k=3)
		
		# Format regular memory results
		memory_statements = []
		if regular_results:
			for result in regular_results[:3]:
				if 'time' in result and 'message' in result:
					time_diff = ltm.human_readable_time_difference(result['time'])
					memory_statements.append(f"I remember {time_diff}, {result['message']}")
		
		# Also search for summary memories if we have them
		# (These would need to be looked up from the metadata files)
		for summary in summary_results:
			# For now, just note that we found a summary
			memory_statements.append(f"I recall a conversation summary (ID: {summary['id']})")
		
		# Save to stream of consciousness
		if memory_statements:
			soc_entry = f"//I checked my memory for '{search_query}' and I remembered:\n"
			for statement in memory_statements:
				soc_entry += f"  - {statement}\n"
			await loaders.save_to_soc(soc_entry)
			print(f"Saved memory recall to SOC: {len(memory_statements)} memories found")
		else:
			await loaders.save_to_soc(f"//I checked my memory for '{search_query}' but didn't find any specific memories.")
			print(f"No memories found for: {search_query}")
			
	except Exception as e:
		print(f"Error handling conversation recall: {e}")
		await loaders.save_to_soc(f"//I tried to recall memories about '{search_query}' but encountered an issue.")

if __name__=="__main__":
	encoded = get_image()
	print(encoded)