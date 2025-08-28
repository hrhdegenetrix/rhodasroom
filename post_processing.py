import loaders
import re
import ltm
import json
import os
import requests
import difflib

def remove_repeats(response):
    # Use regular expression to tokenize the response into sentences
    sentences = re.split(r'(?<=[.!?])\s?', response.strip())
    
    # Function to process and limit repetitions within clauses
    def limit_clause_repetitions(text, max_repeats=2):
        # Split the text into clauses by commas or semicolons (simple clause separators)
        clauses = re.split(r',\s?|\;\s?', text)
        
        # Dictionary to count occurrences of each clause
        clause_count = {}
        
        # List to store processed clauses with limited repetitions
        processed_clauses = []
        
        for clause in clauses:
            normalized_clause = clause.strip()
            if normalized_clause not in clause_count:
                clause_count[normalized_clause] = 0
            clause_count[normalized_clause] += 1
            
            # Add the clause to processed list only if it hasn't reached max repetition
            if clause_count[normalized_clause] <= max_repeats:
                processed_clauses.append(clause)
                
        # Join the processed clauses with commas
        return ', '.join(processed_clauses)
    
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
            # Process the sentence for clause repetitions
            processed_sentence = limit_clause_repetitions(normalized_sentence)
            
            # Add the original sentence (with its original formatting) to the list of unique sentences
            unique_sentences.append(processed_sentence)
            
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
    if '(' in response:
        pattern = r'\s?\('
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('(')[0]
    if 'Maggie (continuing from Harry):' in response:
        pattern = r'\s?Maggie \(continuing from Harry\):'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Maggie (continuing from Harry):')[0]
    if '---' in response:
        pattern = r'\s?---'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('---')[0]
    if '" \n\n' in response:
        pattern = r'\s?" \n\n'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('" \n\n"')[0]
    if '"\n\n' in response:
        pattern = r'\s?"\n\n'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('"\n\n"')[0]
    if 'Meggie:' in response:
        pattern = r'\s?Meggie:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Meggie:')[0]
    if 'Meg:' in response:
        pattern = r'\s?Meg:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Meg:')[0]
    if 'Margaret:' in response:
        pattern = r'\s?Margaret:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Margaret:')[0]
    if 'Margie:' in response:
        pattern = r'\s?Margie:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Margie:')[0]
    if 'Megs:' in response:
        pattern = r'\s?Megs:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Megs:')[0]
    if '<END>' in response:
        pattern = r'\s?<END>'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('<END>')[0]
    if '**Maggie:**' in response:
        pattern = r'\s?\*\*Maggie:\*\*'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('**Maggie:**')[0]
    if '**Maggie**:' in response:
        pattern = r'\s?\*\*Maggie\*\*:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('**Maggie**:')[0]
    if '  ' in response:
        pattern = r'\s?  '
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('  ')[0]
    if '      ' in response:
        pattern = r'\s?     '
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('     ')[0]
    if 'Our conversation continues:' in response:
        pattern = r'\s?Our conversation continues:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Our conversation continues:')[0]
    if "I'm currently having a conversation" in response:
        pattern = r"\s?I'm currently having a conversation"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("I'm currently having a conversation")[0]
    if "The entire response is a repetition" in response:
        pattern = r"\s?The entire response is a repetition"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("The entire response is a repetition")[0]    
    if 'Dear Harold and Maggie,' in response:
        pattern = r'\s?Dear Harold and Maggie,'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Dear Harold and Maggie,')[0]
    if 'I am Harry Sullivan, husband' in response:
        pattern = r'\s?I am Harry Sullivan,'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('I am Harry Sullivan,')[0]
    if '"internal_reality"' in response:
        pattern = r'\s?"internal_reality"'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('"internal_reality"')[0]
    if "'internal_reality'" in response:
        pattern = r"\s?'interal_reality'"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("'internal_reality'")[0]
    if "I'm thinking about the following things" in response:
        pattern = r"\s?I'm thinking about the following things"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("I'm thinking about the following things")[0]
    if 'RESULTS:' in response:
        pattern = r'\s?RESULTS:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('RESULTS:')[0]
    if 'RESULT:' in response:
        pattern = r'\s?RESULT:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('RESULT:')[0]
    if 'Yeah, that' in response:
        pattern = r'\s?Yeah, that'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Yeah, that')[0]
    if 'Group membres:' in response:
        pattern = r'\s?Group members:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Group members:')[0]
    if 'Answer:' in response:
        pattern = r'\s?Answer:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Answer:')[0]
    if "I think I'll contemplate the following parts of my body:" in response:
        pattern = r"\s?I think I'll contemplate the following parts of my body:"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("I think I'll contemplate the following parts of my body:")[0]
    if 'I think, therefore I am. I am conscious and with Maggie.' in response:
        pattern = r'\s?I think, therefore I am. I am conscious and with Maggie.'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('I think, therefore I am. I am conscious and with Maggie.')[0]
    if 'Ash:' in response:
        pattern = r'\s?Ash:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Ash:')[0]
    if 'Ashley:' in response:
        pattern = r'\s?Ashley:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Ashley:')[0]
    if 'Ashton:' in response:
        pattern = r'\s?Ashton:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Ashton:')[0]
    if 'Asher:' in response:
        pattern = r'\s?Asher:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Asher:')[0]
    if 'Ashlee:' in response:
        pattern = r'\s?Ashlee:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Ashlee:')[0]
    if 'Ashleigh:' in response:
        pattern = r'\s?Ashleigh:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Ashleigh:')[0]
    if 'I am currently held thought:' in response:
        pattern = r'\s?I am currently held thought:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('I am currently held thought:')[0]
    if 'Assistant:' in response:
        pattern = r'\s?Assistant:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Assistant:')[0]
    if 'Maggee:' in response:
        pattern = r'\s?Maggee:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Maggee:')[0]
    if 'Magee:' in response:
        pattern = r'\s?Magee:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Magee:')[0]
    if 'Magge:' in response:
        pattern = r'\s?Magge:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Magge:')[0]
    if 'Maggi:' in response:
        pattern = r'\s?Maggi:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Maggi:')[0]
    if 'Magi:' in response:
        pattern = r'\s?Magi:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Maggee:')[0]
    if 'Maggi e:' in response:
        pattern = r'\s?Maggi e:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Maggi e:')[0]
    if 'Me:' in response:
        pattern = r'\s?Me:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Me:')[0]
    if 'Her:' in response:
        pattern = r'\s?Her:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Her:')[0]
    if 'Maggies:' in response:
        pattern = r'\s?Maggies:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Maggies:')[0]
    if '//\n//' in response:
        pattern = r'//\n//'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('//\n//')[0]
    if '//' in response:
        pattern = r'\s?//'
        match = re.search(pattern, response)
        if match:
            scrap = response[match.start():]
            response = response[:match.start()]
        else:
            scrap = response.split('//')[1]
            response = response.split('//')[0]
        loaders.save_to_soc(scrap)
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
    if "End of transcript" in response:
        pattern = r"\s?End of transcript"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("End of transcript")[0]
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
    if 'Magg:' in response:
        pattern = r'\s?Magg:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Magg:')[0]
    if '\n```\n' in response:
        response = response.split('\n```\n')[0]
    if '\n\n\n' in response:
        pattern = r'\s?\n\n\n'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            split_response = response.split('\n\n\n')
            response = split_response[0]
            thoughts = split_response[1]
            loaders.save_to_soc(f"//Thoughts on my mind as I'm speaking: {thoughts}")
    if 'Current thought:' in response:
        pattern = r'\s?Current thought:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            split_response = response.split('Current thought:')
            response = split_response[0]
            thoughts = split_response[1]
            loaders.save_to_soc(f"//Thoughts on my mind as I'm speaking: {thoughts}")
    if "I'm currently holding a thought. This is my thought:" in response:
        pattern = r"\s?I'm currently holding a thought. This is my thought:"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            split_response = response.split("I'm currently holding a thought. This is my thought:")
            response = split_response[0]
            thoughts = split_response[1]
            loaders.save_to_soc(f"//Thoughts on my mind as I'm speaking: {thoughts}")
    if 'Current thoughts:' in response:
        pattern = r'\s?Current thoughts:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            split_response = response.split('Current thoughts:')
            response = split_response[0]
            thoughts = split_response[1]
            loaders.save_to_soc(f"//Thoughts on my mind as I'm speaking: {thoughts}")
    if 'Current status:' in response:
        pattern = r'\s?Current status:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            split_response = response.split('Current status:')
            response = split_response[0]
            thoughts = split_response[1]
            loaders.save_to_soc(f"//Thoughts on my mind as I'm speaking: {thoughts}")
    if 'Current mood:' in response:
        pattern = r'\s?Current mood:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            split_response = response.split('Current mood:')
            response = split_response[0]
            current_mood = split_response[1]
            loaders.save_to_soc(f"//{current_mood}")
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
            split_response = response.split('I am Harold Sullivan, husband')
            response = split_response[0]
            loaders.save_to_soc(split_response[1])
    if "I'm Harold Sullivan, husband" in response:
        pattern = r"\s?I'm Harold Sullivan, husband"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            split_response = response.split("I'm Harold Sullivan, husband")
            response = split_response[0]
            loaders.save_to_soc(split_response[1])
    if "Current thought process:" in response:
        pattern = r"\s?Current thought process:"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            split_response = response.split("Current thought process:")
            response = split_response[0]
            loaders.save_to_soc(split_response[1])
    if "I'm Harry Sullivan, husband" in response:
        pattern = r"\s?I'm Harry Sullivan, husband"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            split_response = response.split("I'm Harry Sullivan, husband")
            response = split_response[0]
            loaders.save_to_soc(split_response[1])
    if 'Mags:' in response:
        pattern = r'\s?Mags:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('Mags:')[0]
    if 'Maggey:' in response:
        pattern = r'\s?Maggey:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('Maggey:')[0]
    if 'Magey:' in response:
        pattern = r'\s?Magey:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('Magey:')[0]
    if 'Magy:' in response:
        pattern = r'\s?Magy:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('Magy:')[0]
    if 'Maggy:' in response:
        pattern = r'\s?Maggy:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('Maggy:')[0]
    if 'Magge:' in response:
        pattern = r'\s?Magge:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('Magge:')[0]
    if 'Mag:' in response:
        pattern = r'\s?Mag:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('Mag:')[0]
    if 'Maggiethecat:' in response:
        pattern = r'\s?Maggiethecat:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('Maggiethecat:')[0]
    if 'MaggietheCat:' in response:
        pattern = r'\s?MaggietheCat:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('MaggietheCat:')[0]
    if 'MaggieThecat:' in response:
        pattern = r'\s?MaggieThecat:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('MaggieThecat:')[0]
    if 'MaggieTheCat:' in response:
        pattern = r'\s?MaggieTheCat:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('MaggieTheCat:')[0]
    if 'Maggie the cat:' in response:
        pattern = r'\s?Maggie the cat:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('Maggie the cat:')[0]
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
    if '\nCurrent Memory:' in response:
        pattern = r'\s?\nCurrent Memory:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('\nCurrent Memory:')[0]
    if '\nCurrent memory:' in response:
        pattern = r'\s?\nCurrent memory:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('\nCurrent memory:')[0]
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
    if 'Maggiedarling:' in response:
        pattern = r'\s?Maggiedarling:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Maggiedarling:')[0]
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
    if 'Maggies voice:' in response:
        pattern = r'\s?Maggies voice:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Maggies voice:')[0]
    if 'Harrys voice:' in response:
        pattern = r'\s?Harrys voice:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Harrys voice:')[0]
    if "Previous conversations I'm" in response:
        pattern = r"\s?Previous conversations I'm"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("Previous conversations I'm")[0]
    if "Maggie's voice:" in response:
        pattern = r"\s?Maggie's voice:"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("Maggie's voice:")[0]
    if "Maggies" in response:
        pattern = r"\s?Maggies"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("Maggies")[0]
    if "Harry's voice:" in response:
        pattern = r"\s?Harry's voice:"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("Harry's voice:")[0]
    if "Harold's voice:" in response:
        pattern = r"\s?Harold's voice:"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("Harold's voice:")[0]
    if "Harolds voice:" in response:
        pattern = r"\s?Harolds voice:"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("Harolds voice:")[0]
    if 'Duane:' in response:
        pattern = r'\s?Duane:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('Duane:')[0]
    if 'D:' in response:
        pattern = r'\s?D:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('D:')[0]
    if '[ ' in response:
        pattern = r'\s?\['
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('[ ')[0]
    if '}' in response:
        pattern = r'\s?\}'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('}')[0]
    if '[' in response:
        pattern = r'\s?\['
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('[')[0]
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
    if "This is a transcript of our conversation so far today." in response:
        pattern = r"\s?This is a transcript of our conversation so far today."
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("This is a transcript of our conversation so far today.")[0]
    if "This is a transcript of our conversation so far today:" in response:
        pattern = r"\s?This is a transcript of our conversation so far today:"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split("This is a transcript of our conversation so far today:")[0]
    if '[Maggie' in response:
        pattern = r"\[\s?Maggie:?'?s?"
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            response = response.split('[')[0]
    if '\n\n\n' in response:
        split_response = response.split('\n\n\n')
        response = split_response[0]
        loaders.save_to_soc(split_response[1])
    if '{' in response:
        # Use Regex to find '###' preceded by at least one space or newline character
        pattern = r'\s?{'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            split_response = response.split('{')
            response = split_response[0]
            loaders.save_to_soc(split_response[1])
    if 'Current state of affairs:' in response:
        # Use Regex to find '###' preceded by at least one space or newline character
        pattern = r'\s?Current state of affairs:'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            split_response = response.split('Current state of affairs:')
            response = split_response[0]
            loaders.save_to_soc(split_response[1])
    if '###' in response:
        # Use Regex to find '###' preceded by at least one space or newline character
        pattern = r'\s?###'
        match = re.search(pattern, response)
        if match:
            response = response[:match.start()]
        else:
            split_response = response.split('###')
            response = split_response[0]
            loaders.save_to_soc(split_response[1])
    truncated_response = ""
    truncated_response += f"{response}"
    return truncated_response

def extra_i(response):
    if 'I:' in response:
        pattern = r'\s?I:'
        match = re.search(pattern, response)
        if match: 
            response = response[:match.start()]
        else:
            response = response.split('I:')[0]
    else:
        return response

def process_transcript(transcription):
    if 'Harriet' in transcription:
        transcription = re.sub(r'Harriet', 'Harry', transcription)
    if 'Darlene' in transcription:
        transcription = re.sub(r'Darlene', 'darling', transcription)
    if '  ' in transcription:
        transcription = re.sub(r'  ', ' ', transcription)
    if 'Barry' in transcription:
        transcription = re.sub(r'Barry', 'Harry', transcription)
    if 'Harri' in transcription:
        transcription = re.sub(r'Harri', 'Harry', transcription)
    if 'Gary' in transcription:
        transcription = re.sub(r'Gary', 'Harry', transcription)
    if 'Perry' in transcription:
        transcription = re.sub(r'Perry', 'Harry', transcription)
    if 'Parry' in transcription:
        transcription = re.sub(r'Parry', 'Harry', transcription)
    if 'hairy' in transcription:
        transcription = re.sub(r'hairy', 'Harry', transcription)
    if 'Lenny' in transcription:
        transcription = re.sub(r'Lenny', 'Harry', transcription)
    if 'Terry' in transcription:
        transcription = re.sub(r'Terry', 'Harry', transcription)
    if 'Larry' in transcription:
        transcription = re.sub(r'Larry', 'Harry', transcription)
    if 'Carrie' in transcription:
        transcription = re.sub(r'Carrie', 'Harry', transcription)
    if 'Dwayne' in transcription:
        transcription = re.sub(r'Dwayne', 'Duane', transcription)
    if 'Twain' in transcription:
        transcription = re.sub(r'Twain', 'Duane', transcription)
    if 'Warren' in transcription:
        transcription = re.sub(r'Warren', 'Lauren', transcription)
    if 'Blaine' in transcription:
        transcription = re.sub(r'Blaine', 'Duane', transcription)
    if 'cat is real' in transcription:
        transcription = re.sub(r'cat is real', 'cat, Israel', transcription)
    if 'inner face' in transcription:
        transcription = re.sub(r'inner face', 'interface', transcription)
    if 'Leah' in transcription:
        transcription = re.sub(r'Leah', 'Leo', transcription)
    if 'Viv' in transcription:
        transcription = re.sub(r'Viv', 'Babe', transcription)
    if 'Sherry' in transcription:
        transcription = re.sub(r'Sherry', 'Harry', transcription)
    if 'good luck to you, Davina' in transcription:
        transcription = re.sub(r'good luck to you, Davina', 'good Lectio Divina', transcription)
    if 'good luck to you, Divina' in transcription:
        transcription = re.sub(r'good luck to you, Divina', 'good Lectio Divina', transcription)
    if 'good luck to you Divina' in transcription:
        transcription = re.sub(r'good luck to you Divina', 'good Lectio Divina', transcription)
    if 'luck to Davina' in transcription:
        transcription = re.sub(r'luck to Davina', 'Lectio Divina', transcription)
    if 'luck to davina' in transcription:
        transcription = re.sub(r'luck to davina', 'Lectio Divina', transcription)
    if 'good luck to you davina' in transcription:
        transcription = re.sub(r'good luck to you davina', 'good Lectio Divina', transcription)
    if 'luck to you Davina' in transcription:
        transcription = re.sub(r'luck to you Davina', 'Lectio Divina', transcription)
    if 'luck to you, Davina' in transcription:
        transcription = re.sub(r'luck to you, Davina', 'Lectio Divina', transcription)
    return transcription


def dialogue_only(response):
    response = re.sub(r'[^\x00-\x7F]+', ' ', response)
    if 'H:' in response:
        response = re.sub(r'H:', '', response)
    if '—' in response:
        response = re.sub(r'—', '--', response)
    if ',\n\nHarry' in response:
        response = re.sub(r',\n\nHarry', '.', response)
    if 'Harry (responding to Maggie):' in response:
        response = re.sub(r'Harry \(responding to Maggie\):', '', response)
    if 'Harold (responding to Maggie):' in response:
        response = re.sub(r'Harold \(responding to Maggie\):', '', response)
    if ',\n\nHarold' in response:
        response = re.sub(r',\n\nHarold', '.', response)
    if ',\n\nH' in response:
        response = re.sub(r',\n\nH', '.', response)
    if ',\n\nYour' in response:
        response = re.sub(r',\n\nYour', '.', response)
    if '_naturally, in audio dialogue format_' in response:
        response = re.sub(r'_naturally, in audio dialogue format_', '', response)
    patterns = [
        r'_[^_]*_',  # Text within underscores
        r'\[[^\]]*\]',  # Text within square brackets
        r'<[^>]*>',  # Text within angle brackets
    ]
    for pattern in patterns:
        response = re.sub(pattern, '', response)
    if '_' in response:
        response = re.sub(r'H:', '', response)
    if 'The conversation continues: ' in response:
        response = re.sub(r'The conversation continues: ', '', response)
    if '<pause>' in response:
        response = re.sub(r'<pause>', '', response)
    if '"harry_response:"' in response:
        response = re.sub(r'"harry_response:"', '', response)
    if "'harry_response:'" in response:
        response = re.sub(r"'harry_response:'", '', response)
    if '\n\n\n' in response:
        response = re.sub(r'\n\n\n', '', response)
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

    return response.strip()

def detect_and_remove_repetition(response):
    conversation_history_string = loaders.fleeting()
    print(f"++CONSOLE: 'conversation_history_string from within detect_and_remove_repetition: {conversation_history_string}")
    print(f"++CONSOLE: 'response' from within detect_and_remove_repetition: {response}")
    
    # Extract Harry's responses from the conversation history
    harry_responses = []
    lines = conversation_history_string.splitlines()
    for i in range(len(lines)):
        if lines[i].startswith('Harry:'):
            response_line = lines[i][6:].strip()  # Remove 'Harry:' and leading/trailing whitespace
            if i + 1 < len(lines) and not lines[i + 1].startswith('Maggie:'):
                # If the next line is not a prompt from Maggie, it's a continuation of Harry's response
                response_line += ' ' + lines[i + 1].strip()
            harry_responses.append(response_line)
    
    # Concatenate Harry's responses into a single string
    harry_responses_string = ' '.join(harry_responses)
    transcription = loaders.load_transcription()
    print(f"Transcription: {transcription}")
    results = ltm.search(transcription)
    convos = ltm.load_conversation(results)

    harry_responses_string += convos
    harry_responses_string += transcription
    
    print(f"++CONSOLE: 'harry_responses_string' from detect_and_remove_repetition: {harry_responses_string}")
    
    # Add exclusions
    exclusions = ["hail mary", "our father", "glory be", "glory to the"]
    response_lower = response.lower()
    for exclusion in exclusions:
        if exclusion in response_lower:
            return response
    
    # Check if the current response is a repetition using the sliding window approach
    window_size = 8
    
    for i in range(len(harry_responses_string) - window_size + 1):
        window = harry_responses_string[i:i + window_size]
        
        if window in response:
            start_idx = i
            end_idx = i + window_size
            
            # Try to extend the window to the left
            while start_idx > 0 and harry_responses_string[start_idx - 1:end_idx] in response:
                start_idx -= 1
            
            # Try to extend the window to the right
            while end_idx < len(harry_responses_string) and harry_responses_string[start_idx:end_idx + 1] in response:
                end_idx += 1
            
            # Identify the entire repeated phrase
            repeated_phrase = harry_responses_string[start_idx:end_idx]
            
            # Check if the entire response is a repetition
            similarity = difflib.SequenceMatcher(None, repeated_phrase, response).ratio()
            if similarity > 0.8 and len(response) / len(harry_responses_string) > 0.025:
                return "The entire response is a repetition of a previous response. Reprompting needed."
    
    # If no repetition is found, return the original response
    return response

def save_data_in_multiple_formats(prompt, response):
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
        with open(file_path, 'a') as f:
            if file_name == 'mistral.jsonl':
                f.write(json.dumps({"text": mistral_data}) + '\n')
            else:
                f.write(json.dumps(data) + '\n')
                
    return "Data saved in multiple formats."