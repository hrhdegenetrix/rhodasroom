import openai
from openai import OpenAI
import requests
import loaders
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# DEBUG: Track search calls to identify loops
SEARCH_CALL_COUNT = 0
SEARCH_QUERIES_SEEN = []

def google_search(api_key, query):
	search_params = {
		"q": query,
		"api_key": api_key,
		"safe": "active"
	}

	search_url = "https://serpapi.com/search.json"
	response = requests.get(search_url, params=search_params)

	if response.status_code == 200:
		return response.json()
	else:
		return None

import numpy as np  # For basic vector operations

client = OpenAI(api_key=os.getenv('OPENAI_SEARCH_API_KEY'))

def get_embedding(content, model='text-embedding-ada-002'):
	content = content.encode(encoding='ASCII', errors='ignore').decode()
	response = client.embeddings.create(input=[content], model=model)

	# Access the embedding property
	vector = response.data[0].embedding  # No parentheses
	return vector

# Placeholder for NLP library functions - adjust accordingly
def calculate_similarity(text1, text2):
	# Hypothetical - this needs real NLP and embeddings
	embedding1 = get_embedding(text1)
	print(f"Embedding 1: {embedding1}")
	embedding2 = get_embedding(text2)
	print(f"Embedding 1: {embedding2}")
	similarity = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
	print(f"Similarity calulated: {similarity}")
	return similarity

def filter_important_keys(search_query, json_data):
	important_results = []
	for result in json_data:
		print(f"Result: {result}")	   
		if isinstance(result, dict):		   
			filtered_result = {}
			for key, value in result.items():
				if value is not None:
					print(f"Value found: {value}")
					similarity_score = calculate_similarity(search_query, key)
					if similarity_score > 0.6:
						filtered_result[key] = value

			if filtered_result:  # Only append if there are valid keys
				important_results.append(filtered_result)

			if not important_results:
				print("No important results found.")
				return []

				print(f"Important results:\n```{important_results}```\n")

		return important_results

def find_nested_key(data, key):
    if isinstance(data, dict):
        if key in data:
            return data[key]
        for value in data.values():
            if isinstance(value, (dict, list)):  # Check if value is dict or list
                result = find_nested_key(value, key)
                if result is not None:
                    return result
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):  # Check if item is dict or list
                result = find_nested_key(item, key)
                if result is not None:
                    return result
    return None	

def parse_search_results(query, json_data):
	results = []

	# Core results (knowledge graph, answer boxes, etc.)
	if "answer_box" in json_data:
		results.append({
			"title": json_data["answer_box"].get("title"),
			"link": json_data["answer_box"].get("link"),
			"snippet": json_data["answer_box"].get("snippet")
		})

	# Organic results
	if "organic_results" in json_data:
		for result in json_data["organic_results"]:
			results.append({
				"title": result.get("title"),
				"link": result.get("link"),
				"snippet": result.get("snippet")
			})

	# Other potential sections (refine based on observation)
	for section_name in ["knowledge_graph", "related_questions", "images_results"]:
		if section_name in json_data:
			section_data = json_data[section_name]

			# Check the type of section_data
			if isinstance(section_data, list):  
				# Process individual items in the list
				for item in section_data:
					if item is not None:
						# Assume `item` is a dictionary, adjust if needed
						results.append({
							"title": item.get("title"),  
							"link": item.get("link"),  
							"snippet": item.get("snippet"), 
							"section": section_name 
						})
					else:
						continue
			else: 
				results.append(section_data)

	# DISABLED: filter_important_keys is causing excessive OpenAI API calls
	# filtered = filter_important_keys(query, json_data)
	output_message = ""
	for index, result in enumerate(results):
		if result.get('title') == None:
			continue

		# Initialize default values
		title = ""
		link = ""
		snippet = ""
		
		nested_list = find_nested_key(result, "title")
		if nested_list:
			title = f"Title: {result.get('title')}\n"
		nested_list = find_nested_key(result, "link")
		if nested_list:
			link = f"Link: {result.get('link')}\n"
		nested_list = find_nested_key(result, "snippet")
		if nested_list:
			snippet = f"Snippet: {result.get('snippet')}\n"

		output_message += f"Result #: {index + 1}\n{title}{link}{snippet}-----\n"

	return output_message

def check_usage():
	api_key = os.getenv('SERPAPI_KEY')
	x = requests.get(f'https://serpapi.com/account?api_key={api_key}')
	results = x.json()
	total = results['searches_per_month']
	remaining = results['total_searches_left']
	usage_statement= f"Before I decide if I want to use a Google search, I should take into consideration the monthly searches we have remaining. Since this is the API I also use to check the weather once a day, I need to ensure I'll have enough leeway to continue using my weather app, so I probably shouldn't use my monthly searches all the way down to 0 unless I'm really interested in something. Currently, we have {total} searches per month, and there are {remaining} searches remaining until our account resets on the 1st."
	return usage_statement

def get_google_search_results(query):
	global SEARCH_CALL_COUNT, SEARCH_QUERIES_SEEN
	SEARCH_CALL_COUNT += 1
	SEARCH_QUERIES_SEEN.append(query)
	
	api_key = os.getenv('SERPAPI_KEY')
	print(f"//API Key initialized in google_search.get_google_search_results(query)")
	print(f"//DEBUG: Call #{SEARCH_CALL_COUNT} for query: '{query}'")
	print(f"//DEBUG: Previous queries: {SEARCH_QUERIES_SEEN[-10:]}")  # Show last 10
	
	if SEARCH_CALL_COUNT > 10:
		print(f"//ERROR: Too many search calls detected! Stopping to prevent infinite loop.")
		return "ERROR: Search loop detected - stopped to prevent API abuse"
	
	search_data = google_search(api_key, query)
	print(f"//Search data received in google_search.get_google_search_results(query): {search_data}")
	if search_data:
		formatted = parse_search_results(query, search_data)
		search_results=f"//Formatted data in google_search.get_google_search_results(query): {formatted}"
		# DISABLED: save_to_soc might be causing search loops
		# loaders.save_to_soc(search_results)
		print(search_results)
		return formatted
	else:
		formatted = None
		return formatted

if __name__ == "__main__":
	usage_statement = check_usage()
	print(usage_statement)
	# query = "job hunting tips"
	# results = get_google_search_results(query)
	# print(results)
