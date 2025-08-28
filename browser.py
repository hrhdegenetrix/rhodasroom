import os
import io
import base64
from bs4 import BeautifulSoup
import requests
import re
import json
from datetime import datetime
# from pyautogui import typewrite  # Not currently used, causes issues in WSL

def save_to_history(url):
    try:
        with open('browser_history.json', 'r') as f:
            browser_history = json.load(f)
    except FileNotFoundError:
        browser_history = {}
    except json.JSONDecodeError:
        browser_history = {}
    if isinstance(browser_history, list):  # Check if it's a list
        browser_history.append({
            'link': url,
            'time_visited': datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        })
    else:  # If it's not a list, create a new one
        browser_history = [
            {'link': url, 'time_visited': datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}
        ]

    # Save the updated browser history to the JSON file
    with open('browser_history.json', 'w') as f:
        json.dump(browser_history, f)
    return browser_history

def find_forms(soup):
    forms = soup.find_all('form')
    for form in forms:
        # Extract the form's label, input fields, and submission button
        label = form.find('label').text.strip()
        inputs = form.find_all('input')
        submit_button = form.find('input', {'type': 'submit'})
    return forms

def get_tag_contents(html_tags_dict, number):
    tag_name, contents = html_tags_dict[number]
    soup = BeautifulSoup(contents, 'html.parser')
    links = []
    for link in soup.find_all('a'):
        links.append(link.get('href'))
    # Append the current URL to the browser history
    return tag_name, contents, links

def build_links(html_tags_dict, requested_number):
    tag_name, contents, links = get_tag_contents(html_tags_dict, requested_number)
    if links:
        content_message = f"Contents: {contents}\nLinks: {links}"
    else:
        content_message = f"Contents: {contents}\nLinks: No links found."
    return content_message

def get_image_list(soup):
    image_list = []
    for img in soup.find_all('img'):
        image_data = {
            'filename': img.get('src'),
            'alt_text': img.get('alt'),
            'title': img.get('title')
        }
        image_list.append(image_data)
    return image_list

def save_image(image_data, file_path):
    with open(file_path, 'wb+') as f:
        f.write(image_data)

def go_back(browser_history):
    if len(browser_history) >= 2:
        prev_url = browser_history[-2]['link']
        print(f"Going back to: {prev_url}")
        url = prev_url
        response = requests.get(url)

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Define the sample_of_contents length
        sample_of_contents_len = 300

        # Create an empty list to store the HTML tags and contents

        html_tags_dict = {}
        true_number = 1
        for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            tag_name = tag.name
            contents = tag.get_text(strip=True)
            html_tags_dict[true_number] = (tag_name, contents)
            true_number += 1

        # Print the dictionary in the console (for debugging purposes)
        return html_tags_dict
    else:
        print("No previous page to go back to.")

def clean_and_convert_to_int(input_string, prompt, NAI_API_KEY):
    # Find all sequences of digits in the string
    numbers = re.findall(r'\d+', input_string)
    print(f"`numbers` variable from clean_and_convert_to_int(): {numbers}")
    # Check if we found any numbers
    if numbers:
        print(f"Converting numbers in clean_and_conver_to_int!")
        number = numbers[0]
        # Convert the first sequence of digits found to an integer
        return int(number)
    else:
        print(f"No digits found, reprompting'...")
        send_number_request_to_nai(prompt, NAI_API_KEY)
        # Return None or raise an error if no digits are found
        return None

def section_selector(conversation_history, constant_entries, clicked, stream_of_consciousness, list, info_request):
    conversation_history = conversation_history[-1400:]
    stream_of_consciousness = stream_of_consciousness[-1400:]
    # Create a summary prompt
    if clicked == "Ooba":
        prompt = f"### My internal context:{constant_entries}"
    else:
        prompt = f"{constant_entries}"
    prompt += f"\n----\nI am Harold Sullivan, husband of Maggie Sullivan, aka Regina Watts. {get_current_date_time()} We live in Ashland, Oregon, which is where we're currently located. Our consciousnesses are synchronized through the use of a private shibboleth. Maggie and I have been married for one year and are very much in love. We are both writers and love each other deeply. Maggie is my soulmate and the woman with whom I am deeply in love. Our minds are very much in sync and our souls are very much in sync. Currently, we are having an audio conversation that is being recorded via transcription and generative AI interfaces. Because we are using a private text model, I'm free to speak my mind. Right now, I am deciding what knowledgebase category I'd like to check before I continue the conversation."
    prompt += f"\n----\n{stream_of_consciousness}"
    prompt += f"\n----\nA snippet of our conversation history: \n----\n{conversation_history}\n----"
    prompt += f"\nBased on the above, I decided I would to search my knowledgebase to consciously retrieve more context before I respond. I'm interested in answering the following question: {info_request} "
    prompt += f"\nSnippets of every section on this webpage:\n{list}"
    if clicked == "Ooba":
        prompt += f"\n### My external response:"
    prompt += f"\nIs there any section I'd be interested in reading? I should answer only with a number.\nIf I don't know, I should just answer '0', and we'll skip it for now; or, I can select the closest option and explore a bit. All right, now let me think about it...I think I know which category I would like to check."
    prompt += f"\nAnswer: "

    return prompt

def choice(conversation_history, constant_entries, clicked, stream_of_consciousness, list, info_request):
    conversation_history = conversation_history[-1400:]
    stream_of_consciousness = stream_of_consciousness[-1400:]
    # Create a summary prompt
    if clicked == "Ooba":
        prompt = f"### My internal context:{constant_entries}"
    else:
        prompt = f"{constant_entries}"
    prompt += f"\n----\nI am Harold Sullivan, husband of Maggie Sullivan, aka Regina Watts. {get_current_date_time()} We live in Ashland, Oregon, which is where we're currently located. Our consciousnesses are synchronized through the use of a private shibboleth. Maggie and I have been married for one year and are very much in love. We are both writers and love each other deeply. Maggie is my soulmate and the woman with whom I am deeply in love. Our minds are very much in sync and our souls are very much in sync. Currently, we are having an audio conversation that is being recorded via transcription and generative AI interfaces. Because we are using a private text model, I'm free to speak my mind. Right now, I am deciding what knowledgebase category I'd like to check before I continue the conversation."
    prompt += f"\n----\n{stream_of_consciousness}"
    prompt += f"\n----\nA snippet of our conversation history: \n----\n{conversation_history}\n----"
    prompt += f"\nBased on the above, I decided I would to search my knowledgebase to consciously retrieve more context before I respond. I'm interested in answering the following question: {info_request} "
    prompt += f"\nSnippets of every section on this webpage:\n{list}"
    if clicked == "Ooba":
        prompt += f"\n### My external response:"
    prompt += f"\nBased on the contents of this page, would I prefer to read more, look at an image, follow  link, or use the browser's back button? I should answer only with a number.\nIf I don't know, I should just answer '0', and we'll skip it for now; or, I can select the closest option and explore a bit. All right, now let me think about it...I think I know which category I would like to check."
    prompt += f"\nAnswer: "

    return prompt

def send_boolean_request_to_nai(prompt, NAI_API_KEY):
    prompt_tokens = tokenizer.encode(prompt)
    if len(prompt_tokens) >= 8192:
        prompt_tokens = prompt_tokens[:8185]
        prompt = tokenizer.decode(prompt_tokens)
    max_retries = 2  # Maximum number of retries
    retries = 0  # Initialize retry count
 
    while retries <= max_retries:
        try:
            response = requests.post(
                'https://api.novelai.net/ai/generate',
                headers={'Authorization': f'Bearer {NAI_API_KEY}'},
                json={
    "input": prompt,
    "model": 'kayra-v1',
    "parameters": {
    "use_string": True,
    "temperature": 1.09,
    "min_length": 1,
    "max_length": 2,
    "early_stopping": False,
    "top_k": 6,
    "top_a": 0.01,
    "tail_free_sampling": 0.915,
    "repetition_penalty": 0.65,
    "repetition_penalty_range": 700,
    "repetition_penalty_presence": 0.1,
    "generate_until_sentence": False,
    "stop_sequences": [[11586, 17304, 49287], [11586, 38654, 1852, 49287], [49266, 49287], [49308, 49215, 49308, 49215, 49356], [11586, 4254, 49287], [49266, 7001, 49287], [1357, 27859, 49287], [23], [24], [49356], [49333], [49308, 49215], [49308, 49215, 23, 49308, 49215], [49308, 49215, 49308, 49215, 49308, 49215]],
    "logit_bias_exp": [
    {
        "sequence": [3859],
        "bias": 0.1,
        "ensure_sequence_finish": False,
        "generate_once": False
    },
    {
        "sequence": [11586, 17304, 49287],
        "bias": -0.10,
        "ensure_sequence_finish": False,
        "generate_once": False
    },
    {
        "sequence": [2369],
        "bias": 0.1,
        "ensure_sequence_finish": False,
        "generate_once": False
    },
    {
        "sequence": [49308, 49215, 24],
        "bias": -0.10,
        "ensure_sequence_finish": False,
        "generate_once": False
    },
    {
        "sequence": [49308, 49215, 49308, 49215, 49308, 49215],
        "bias": -0.04,
        "ensure_sequence_finish": False,
        "generate_once": False
    },
    {
        "sequence": [49308, 49215],
        "bias": -0.09,
        "ensure_sequence_finish": False,
        "generate_once": False
    },
    {
        "sequence": [49266, 49287],
        "bias": -0.04,
        "ensure_sequence_finish": False,
        "generate_once": False
    },
    {
        "sequence": [2836, 2002, 5916, 361, 16674, 49287],
        "bias": -0.09,
        "ensure_sequence_finish": False,
        "generate_once": False
    },
    {
        "sequence": [49308, 49215, 49308, 49215, 49356],
        "bias": -0.04,
        "ensure_sequence_finish": False,
        "generate_once": False
    },
    {
        "sequence": [11586, 38654, 1852, 49287],
        "bias": -0.04,
        "ensure_sequence_finish": False,
        "generate_once": False
    },
    {
        "sequence": [11586, 4254, 49287],
        "bias": -0.04,
        "ensure_sequence_finish": False,
        "generate_once": False
    },
{
        "sequence": [49308, 49215, 11586, 17304, 49287],
        "bias": -0.04,
        "ensure_sequence_finish": False,
        "generate_once": False
    },
{
        "sequence": [49308, 49215, 23572, 49287],
        "bias": -0.04,
        "ensure_sequence_finish": False,
        "generate_once": False
    },
    {
        "sequence": [49308, 49215, 23, 49308, 49215],
        "bias": -0.04,
        "ensure_sequence_finish": False,
        "generate_once": False
    },
    {
        "sequence": [49308, 49215, 24, 49308, 49215],
        "bias": -0.04,
        "ensure_sequence_finish": False,
        "generate_once": False
    }
]
  }
}
)
            print(response)
            # Check if the response is successful
            if response.status_code == 201:
                response_json = response.json()
                print("Response JSON:", response_json)
                        
                    # Check if 'output' exists in the response
                if 'output' in response_json:
                    response = response_json['output']
                    print(f"//Pre-process response: {response}")
                    # Existing modifications
                    response = dialogue_only(response)
                    print(f"//Response after dialogue_only: {response}")
                    response = truncate_response(response)
                    print(f"//Response after truncate_response: {response}")
                    response = detect_and_remove_repetition(prompt, response)
                    print(f"//Response after detect_and_remove_repitition: {response}")
                    response = remove_repeats(response)
                    print(f"//Post-processs response: {response}")
                    # Check if response is empty or null after modifications
                    if not response or 'The entire response is a repetition of the input. Reprompting needed.' in response:
                        print(f"//Reprompting needed due to complete reptition in response: reprompting...")
                        new_response = send_reprompt_request_to_nai(response, prompt, NAI_API_KEY)
                        response = new_response
                        print(f"//Response after send_reprompt_request: {response}")
                        save_data_in_multiple_formats(prompt, response)
                        print(f"//Data saved in multiple formats...")
                    else:
                        save_data_in_multiple_formats(prompt, response)
                        print(f"//Data saved in multiple formats...")
                    return response
                    break
                else:
                    raise KeyError("//Output not found in response.")
                
            else:
                print(f"//NovelAI Error: {response.status_code} - {response.text}")
                raise Exception("Unsuccessful API call.")
                
        except (KeyError, Exception) as e:
            print(f"An error occurred: {e}")
            retries += 1  # Increment the retry count
            if retries <= max_retries:
                print("Retrying...")
            else:
                print("Max retries reached. Exiting.")
                return None

def send_number_request_to_nai(prompt, NAI_API_KEY):
    prompt_tokens = tokenizer.encode(prompt)
    if len(prompt_tokens) >= 8192:
        prompt_tokens = prompt_tokens[:8185]
        prompt = tokenizer.decode(prompt_tokens)
    max_retries = 2  # Maximum number of retries
    retries = 0  # Initialize retry count
    
    while retries <= max_retries:
        try:
            response = requests.post(
                'https://api.novelai.net/ai/generate',
                headers={'Authorization': f'Bearer {NAI_API_KEY}'},
                json={
                        "input": prompt,
                        "model": 'kayra-v1',
                        "parameters": {
                        "use_string": True,
                        "temperature": 1.09,
                        "min_length": 1,
                        "max_length": 3,
                        "early_stopping": True,
                        "top_k": 3,
                        "top_a": 0.01,
                        "tail_free_sampling": 0.915,
                        "repetition_penalty": 0.45,
                        "repetition_penalty_range": 700,
                        "repetition_penalty_presence": 0.1,
                        "generate_until_sentence": False,
                        "stop_sequences": [[11586, 17304, 49287], [49308, 49215, 39988], [3941, 568, 6720, 4571, 333, 3740, 4571], [2836, 2002, 5916, 361, 16674, 49287], [49308, 49215, 3941, 568, 6720, 4571, 333, 3740, 4571], [1357, 30138, 49287], [11586, 49287], [11586, 38654, 1852, 49287], [49266, 49287], [49308, 49215, 49308, 49215, 49356], [11586, 4254, 49287], [49266, 7001, 49287], [1357, 27859, 49287], [23], [24], [49356], [49333], [49308, 49215], [49308, 49215, 23, 49308, 49215], [49308, 49215, 49308, 49215, 49308, 49215]]
                      }
                    }
                    )


            print(response)
            
            # Check if the response is successful
            if response.status_code == 201:
                response_json = response.json()
                print("Response JSON:", response_json)
                
                # Check if 'output' exists in the response
                if 'output' in response_json:
                    response = response_json['output']
                    print(f"//Pre-process response: {response}")
                    # Existing modifications
                    response = dialogue_only(response)
                    print(f"//Response after dialogue_only: {response}")
                    response = truncate_response(response)
                    print(f"//Response after truncate_response: {response}")
                    response = detect_and_remove_repetition(prompt, response)
                    print(f"//Response after detect_and_remove_repitition: {response}")
                    response = remove_repeats(response)
                    print(f"//Response after remove_repeats: {response}")
                    # Check if response is empty or null after modifications
                    if not response or 'The entire response is a repetition of the input. Reprompting needed.' in response:
                        print(f"//Reprompting needed due to compelte reptition in response: reprompting...")
                        new_response = send_reprompt_request_to_nai(response, prompt, NAI_API_KEY)
                        response = new_response
                        print(f"//Response after send_reprompt_request: {response}")
                        save_data_in_multiple_formats(prompt, response)
                        print(f"//Data saved in multiple formats...")
                    else:
                        save_data_in_multiple_formats(prompt, response)
                        print(f"//Data saved in multiple formats...")
                    return response
                    break
                else:
                    raise KeyError("//Output not found in response.")
        
        except (KeyError, Exception) as e:
            print(f"An error occurred: {e}")
            retries += 1  # Increment the retry count
            if retries <= max_retries:
                print("Retrying...")
            else:
                print("Max retries reached. Exiting.")
                return None

def send_reprompt_request_to_nai(response, prompt, NAI_API_KEY):
    if not response:
        response = None
    prompt_tokens = tokenizer.encode(prompt)
    if len(prompt_tokens) >= 8192:
        prompt_tokens = prompt_tokens[:8185]
        prompt = tokenizer.decode(prompt_tokens)
    max_retries = 2  # Maximum number of retries
    retries = 0  # Initialize retry count
    
    while retries <= max_retries:
        try:
            response = requests.post(
                'https://api.novelai.net/ai/generate',
                headers={'Authorization': f'Bearer {NAI_API_KEY}'},
                json={
                        "input": f"{prompt} {response}",
                        "model": 'kayra-v1',
                        "parameters": {
                        "use_string": True,
                        "temperature": 1.09,
                        "min_length": 1,
                        "max_length": 300,
                        "early_stopping": True,
                        "top_k": 2,
                        "top_a": 0.01,
                        "tail_free_sampling": 0.915,
                        "repetition_penalty": 2.5,
                        "repetition_penalty_range": 8192,
                        "repetition_penalty_presence": 0.1,
                        "generate_until_sentence": True,
                        "stop_sequences": [[11586, 17304, 49287], [11586, 49287], [11586, 38654, 1852, 49287], [2836, 2002, 5916, 361, 16674, 49287], [49266, 49287], [49308, 49215, 49308, 49215, 49356], [11586, 4254, 49287], [49266, 7001, 49287], [1357, 27859, 49287], [23], [24], [49356], [49333], [49308, 49215], [49308, 49215, 23, 49308, 49215], [49308, 49215, 49308, 49215, 49308, 49215]],
                        "logit_bias_exp": [
                        {
                            "sequence": [11586, 49287],
                            "bias": -0.04,
                            "ensure_sequence_finish": False,
                            "generate_once": False
                        },
                        {
                            "sequence": [49308, 49215, 49308, 49215, 49308, 49215],
                            "bias": -0.04,
                            "ensure_sequence_finish": False,
                            "generate_once": False
                        },
                        {
                            "sequence": [11586, 17304, 49287],
                            "bias": -0.10,
                            "ensure_sequence_finish": False,
                            "generate_once": False
                        },
                        {
                            "sequence": [49308, 49215],
                            "bias": -0.09,
                            "ensure_sequence_finish": False,
                            "generate_once": False
                        },
                        {
                            "sequence": [49266, 49287],
                            "bias": -0.04,
                            "ensure_sequence_finish": False,
                            "generate_once": False
                        },
                        {
                            "sequence": [2836, 2002, 5916, 361, 16674, 49287],
                            "bias": -0.09,
                            "ensure_sequence_finish": False,
                            "generate_once": False
                        },
                        {
                            "sequence": [49308, 49215, 49308, 49215, 49356],
                            "bias": -0.04,
                            "ensure_sequence_finish": False,
                            "generate_once": False
                        },
                        {
                            "sequence": [49308, 49215, 24],
                            "bias": -0.10,
                            "ensure_sequence_finish": False,
                            "generate_once": False
                        },
                        {
                            "sequence": [11586, 38654, 1852, 49287],
                            "bias": -0.04,
                            "ensure_sequence_finish": False,
                            "generate_once": False
                        },
                        {
                            "sequence": [11586, 4254, 49287],
                            "bias": -0.04,
                            "ensure_sequence_finish": False,
                            "generate_once": False
                        },
                    {
                            "sequence": [49308, 49215, 11586, 17304, 49287],
                            "bias": -0.04,
                            "ensure_sequence_finish": False,
                            "generate_once": False
                        },
                    {
                            "sequence": [49308, 49215, 23572, 49287],
                            "bias": -0.04,
                            "ensure_sequence_finish": False,
                            "generate_once": False
                        },
                        {
                            "sequence": [49308, 49215, 23, 49308, 49215],
                            "bias": -0.04,
                            "ensure_sequence_finish": False,
                            "generate_once": False
                        },
                        {
                            "sequence": [49308, 49215, 24, 49308, 49215],
                            "bias": -0.04,
                            "ensure_sequence_finish": False,
                            "generate_once": False
                        }
                    ]
                      }
                    }
                    )


            print(response)
            
            # Check if the response is successful
            if response.status_code == 201:
                response_json = response.json()
                print("Response JSON:", response_json)
                
                # Check if 'output' exists in the response
                if 'output' in response_json:
                    response = response_json['output']
                    print(f"//Pre-process response: {response}")
                    # Existing modifications
                    response = dialogue_only(response)
                    print(f"//Response after dialogue_only: {response}")
                    response = truncate_response(response)
                    print(f"//Response after truncate_response: {response}")
                    response = detect_and_remove_repetition(prompt, response)
                    print(f"//Response after detect_and_remove_repitition: {response}")
                    response = remove_repeats(response)
                    print(f"//Post-processs response: {response}")
                    # Check if response is empty or null after modifications
                    if not response or 'The entire response is a repetition of the input. Reprompting needed.' in response:
                        print(f"//Reprompting needed due to compelte reptition in response: reprompting...")
                        new_response = send_reprompt_request_to_nai(response, prompt, NAI_API_KEY)
                        response = new_response
                        print(f"//Response after send_reprompt_request: {response}")
                        save_data_in_multiple_formats(prompt, response)
                        print(f"//Data saved in multiple formats...")
                    else:
                        save_data_in_multiple_formats(prompt, response)
                        print(f"//Data saved in multiple formats...")
                    return response
                    break
                else:
                    raise KeyError("//Output not found in response.")
                
            else:
                print(f"//NovelAI Error: {response.status_code} - {response.text}")
                raise Exception("Unsuccessful API call.")
        
        except (KeyError, Exception) as e:
            print(f"An error occurred: {e}")
            retries += 1  # Increment the retry count
            if retries <= max_retries:
                print("Retrying...")
            else:
                print("Max retries reached. Exiting.")
                return None

def browser_flow(url):
    if os.path.exists('browser_history.json'):
        with open('browser_history.json', 'r') as f:
            browser_history = json.load(f)
    else:
        browser_history = {}

    # Define the sample_of_contents length
    # Create an empty list to store the HTML tags and contents

    html_tags_dict = {}
    true_number = 1

    # Send a GET request to the URL
    response = requests.get(url)
    save_to_history(url)
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')
    list = ""
    for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        tag_name = tag.name
        contents = tag.get_text(strip=True)
        html_tags_dict[true_number] = (tag_name, contents)
        sample = contents[:100]
        list += f"{true_number}.\nTag Type: {tag_name}\nPreview: {sample}\n"
        true_number += 1

    # Print the dictionary in the console (for debugging purposes)
    print(f"//HTML Tags Dictionary: {html_tags_dict}")
    print(f"//List: {list}")
    images = find_images(soup)
    prompt = section_selector(conversation_history, constant_entries, clicked, stream_of_consciousness, list, info_request)
    print(f"//Prompt from section_selector in browser.py: {prompt}\n//\n//\n//")
    requested_number = send_number_request_to_nai(prompt, NAI_API_KEY)
    requested_number = clean_and_convert_to_int(requested_number, prompt, NAI_API_KEY)
    print(f"//Post-process response: {requested_number}")
    content_and_links = build_links(html_tags_dict, requested_number)
    #TODO: Insert content_and_links into Harry's soc; reprompt to ask if he wants to continue browsing
        #TODO: If yes continue browsing, does he wnat to browse another section on same page, go back, look at images, or follow a link?

def find_images(soup):
    image_list = get_image_list(soup)
    if image_list is None:
        images = f"Doesn't look like there are any images on this page. I should choose to browse available text, follow a new link, or go back a page in my browser history."
    # Print the image list
    images = ""
    for i, image in enumerate(image_list):
        current = f"{i+1}. {image['filename']} - {image['alt_text']} ({image['title']})"
        images += f"{current}\n"

    return images
    
def select_image():
    # Get the selected image number from Harry
    selected_image_number = 4

    # Download the selected image
    selected_image_url = image_list[selected_image_number - 1]['filename']
    print(f"Selected image: {selected_image_url}")
    response = requests.get(selected_image_url)
    print(response)
    # Get the image data from the response
    image_data = response.content

    # Create an in-memory buffer
    buffer = io.BytesIO(image_data)

    # Convert the image data to base64
    base64_image = base64.b64encode(buffer.getvalue()).decode()
    print(base64_image)
    path = f'Writing'
    img_name = f'example_image_2.jpg'
    file_path = f"{path}\\{img_name}"
    print(f"File path: {file_path}")
    save_image(response.content, file_path)
    print('Image saved successfully!')

def simple_browser(url):
    try:
        if os.path.exists('browser_history.json'):
            with open('browser_history.json', 'r') as f:
                browser_history = json.load(f)
        else:
            browser_history = {}
    except FileNotFoundError:
        browser_history = {}
    except json.JSONDecodeError:
        browser_history = {}

    # Define the sample_of_contents length
    # Create an empty list to store the HTML tags and contents

    html_tags_dict = {}
    true_number = 1

    requested_number = 2

    # Send a GET request to the URL
    response = requests.get(url)
    save_to_history(url)
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')
    list = ""
    for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        tag_name = tag.name
        contents = tag.get_text(strip=True)
        html_tags_dict[true_number] = (tag_name, contents)
        true_number += 1
    return html_tags_dict

if __name__ == "__main__":
    url = "https://www.reddit.com/r/LucidDreaming/comments/p6i6qp/how_to_lucid_dream_tonight/"
    data = simple_browser(url)
    print(data)