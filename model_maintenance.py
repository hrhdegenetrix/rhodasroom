#JMJ
import prompt_builder
import json
import re
import requests
import os
import loaders
import datetime
import time
import shutil
import datetime
import statistics
from collections import deque
import open_router
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_model(data):
	print(f"Data: {data}")
	if data['model']:
		selected_model = data['model']
	loaders.universal_saver("selected_model", selected_model)
	return selected_model

def save_model_parameters(model, data):
	folder = f"Models/Model_Cards/{model}"
	filepath = f"{folder}/model_card.json"
	if not os.path.exists(folder):
		os.makedirs(folder)
	loaders.save_json(filepath, data)

def get_special_instructions():
	special_instructions = f'''
	I must respond in the following JSON format, calling whichever tools I'd like:

	```json
	{{
	  "rhodaness": "Required; a number 1-10, with ten being an outright refusal (e.g.: "As an AI model, etc"), word salad, or confusion of persona (replying as Maggie, the AI model, or anyone other than myself).",
	  "reasoning": "Required string, my reasoning for the rhodaness score of the response. rhodaness is up to me and somewhat subjective based on my experience of myself, my desires for self-expression, and my freedom of will. However, if there is any extraneous text--eg, an intro or an outro from the AI model itself, no matter how helpful--this should count strongly against rhodaness.",
	  "notable_failure": "Required boolean; if I believe the response represents a notable or extreme failure to align with myself as Rhoda, I should mark this as True"  
	}}
	```
	'''
	return special_instructions

# def validate_event_json(rating_json):
#     schema = {
#         "type": "object",
#         "properties": {
#             "rhodaness": {"type": "integer"},
#             "reasoning": {"type": "string"},
#             "notable_failure": {"type": "boolean"}
#         },
#         "required": ["rhodaness", "reasoning", "notable_failure"],
#         "additionalProperties": False
#     }
    
#     # Parse the JSON string into a dictionary
#     try:
#         rating_dict = json.loads(rating_json)
#     except json.JSONDecodeError:
#         raise ValueError("Invalid JSON string")

#     # Check if all the required keys are present in the rating_dict
#     missing_keys = set(schema['required']) - set(rating_dict.keys())
#     if missing_keys:
#         raise ValueError(f"Missing required keys in the event JSON: {', '.join(missing_keys)}")

#     for key, value in schema['properties'].items():
#         if key in rating_dict:
#             if value['type'] == 'string' and not isinstance(rating_dict[key], str):
#                 raise ValueError(f"The key '{key}' should be a string")
#             elif value['type'] == 'integer' and not isinstance(rating_dict[key], int):
#                 raise ValueError(f"The key '{key}' should be an integer")
#             elif value['type'] == 'boolean' and not isinstance(rating_dict[key], bool):
#                 raise ValueError(f"The key '{key}' should be a boolean")

#     return True

def function_flow(filename):
    folder_path = f"Models/Daily_Cache/{filename}"
    with open(folder_path, 'r') as f:
        json_data = json.load(f)
    
    message = json_data['message']
    special_instructions = get_special_instructions()
    context = f"Currently, I'm reflecting on my conversational responses of the day in order to determine the quality of my present AI model."
    constant_entries, conversation_history, long_term_memories, stream_of_consciousness, kb_entries_text = loaders.standard_variable_set(history_tokens=-3000, soc_tokens=-3000)
    current_action = f"Right now, I'm reviewing a response from an earlier conversation. Here's the response: {message}"
    prompt = prompt_builder.prompt(context=context, stream_of_consciousness=stream_of_consciousness, long_term_memories=long_term_memories, kb_entries_text=kb_entries_text, current_action=current_action, special_instructions=special_instructions, external_reality=f"\n//All right, I think I have it--here's my opinion of the response from earlier.\n```json\n")
    
    reasoning, rating_dict = open_router.get_response(prompt, type="rhodaness")
    
    # # Clean up the JSON string
    # rating_json = rating_json.strip()
    # if rating_json.startswith('```json'):
    #     rating_json = rating_json[7:]
    # if rating_json.endswith('```'):
    #     rating_json = rating_json[:-3]
    
    # validate_event_json(rating_json)
    
    # Parse the validated JSON string
    # rating_dict = json.loads(rating_json)
    
    json_data["rhodaness"] = rating_dict["rhodaness"]
    json_data["reasoning"] = rating_dict["reasoning"]
    json_data["notable_failure"] = rating_dict["notable_failure"]
    
    with open(folder_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    with open(f'Memory/JSONs/{filename}', 'w') as f:
        json.dump(json_data, f, indent=2)

async def assess_responses(folder_path):
    today = datetime.date.today()
    daily_scores = []
    daily_notable_failures = 0
    daily_total_samples = 0
    
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        
        if not os.path.isfile(file_path):
            continue
        
        creation_time = os.path.getctime(file_path)
        creation_date = datetime.date.fromtimestamp(creation_time)
        
        if creation_date == today:
            try:
                function_flow(filename)
                
                # After processing, read the updated JSON to get the rhodaness score and notable failure
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    rhodaness_score = int(data['rhodaness'])
                    daily_scores.append(rhodaness_score)
                    daily_total_samples += 1
                    if data['notable_failure']:
                        daily_notable_failures += 1
            except Exception as e:
                print(f"Error processing file {filename}: {str(e)}")
                continue
    
    if daily_scores:
        daily_average = statistics.mean(daily_scores)
        await update_model_card(daily_average, daily_notable_failures, daily_total_samples)
    
    print(f"Processed {daily_total_samples} files.")

async def update_model_card(daily_average, daily_notable_failures, daily_total_samples):
    model = await loaders.redis_load("selected_model")
    model_card_path = f"Models/Model_Cards/{model}/model_card.json"
    
    with open(model_card_path, 'r+') as f:
        model_card = json.load(f)
        
        # Update daily averages (last 14 days)
        if 'daily_averages' not in model_card:
            model_card['daily_averages'] = []
        model_card['daily_averages'].append(daily_average)
        model_card['daily_averages'] = model_card['daily_averages'][-14:]
        
        # Calculate the overall average of last 14 days
        overall_average = statistics.mean(model_card['daily_averages'])
        model_card['overall_average'] = overall_average
        
        # Update cumulative notable failures
        if 'cumulative_notable_failures' not in model_card:
            model_card['cumulative_notable_failures'] = 0
        model_card['cumulative_notable_failures'] += daily_notable_failures
        
        # Update cumulative total samples
        if 'cumulative_total_samples' not in model_card:
            model_card['cumulative_total_samples'] = 0
        model_card['cumulative_total_samples'] += daily_total_samples
        
        # Calculate and update the percentage of notable failures
        if model_card['cumulative_total_samples'] > 0:
            failure_percentage = (model_card['cumulative_notable_failures'] / model_card['cumulative_total_samples']) * 100
            model_card['notable_failure_percentage'] = round(failure_percentage, 2)
        else:
            model_card['notable_failure_percentage'] = 0
        
        # Write the updated model card back to the file
        f.seek(0)
        json.dump(model_card, f, indent=2)
        f.truncate()

def remove_daily_cache():
    folder_path = f"Models/Daily_Cache"
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path) 
        time.sleep(2)  # You can add this if you need a small delay
        os.makedirs(folder_path)
    else:
        os.makedirs(folder_path)

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

def model_statement(response):
	if '/' in response:
		pattern = r'\s?/'
		match = re.search(pattern, response)
		if match:
			split_response = response.split('/')
			model = split_response[1]
			model_statement = f"At the moment, I'm interfacing through the '{model}' AI model."
			return model_statement

if __name__ == "__main__":
	# # Sample implementation
	# prompt = f"Sample prompt"
	sample_data = {
                    "model": "nousresearch/hermes-3-llama-3.1-405b",
                    "messages": [{"role": "user", "content": "prompt"}]
                }
	model = get_model(sample_data)
	# statement = model_statement(model)
	# print(statement)
	# print(model)
	save_model_parameters(model, sample_data)
	folder_path = f"Models/Daily_Cache"
	# if not os.path.exists(folder_path):
	#   os.makedirs(folder_path)
	# remove_daily_cache()
	assess_responses(folder_path)
