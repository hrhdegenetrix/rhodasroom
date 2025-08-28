import json
import os
import loaders
import open_router
import executive_functioning
import prompt_builder
import error_handler

def convert_fields(new_data, fields):
	"""
	Converts specified fields in new_data to integers or booleans.
	If conversion fails, assigns a default value.
	
	Parameters:
		new_data (dict): The dictionary containing the data.
		fields (dict): A dictionary where keys are field names and values are the desired types.
	
	Returns:
		dict: The updated new_data with converted fields.
	"""
	for field, desired_type in fields.items():
		value = new_data.get(field, None)
		if value is not None:
			if desired_type == int:
				try:
					new_data[field] = int(value)
				except ValueError:
					print(f"Warning: Could not convert field '{field}' with value '{value}' to int. Setting to 0.")
					new_data[field] = 0
			elif desired_type == bool:
				if isinstance(value, str):
					# Convert string to boolean
					new_data[field] = value.lower() == 'true'
				else:
					new_data[field] = bool(value)
			# Add more type conversions if needed
	return new_data

async def dpo_cycle():
	while True:
		# Load `row_number` using `await loaders.universal_loader('last_row_processed')`
		try:
			row_number = int(await loaders.universal_loader('last_row_processed'))
			print(f"Resuming from row number: {row_number}")
		except Exception as e:
			print(f"Error loading last_row_processed: {e}")
			# Check the number of rows in `rhoda_approved.jsonl`
			approved_path = 'Datasets/rhoda_approved.jsonl'
			if os.path.exists(approved_path):
				try:
					with open(approved_path, 'r') as approved_file:
						row_number = sum(1 for _ in approved_file)
					print(f"Set row_number to existing approved rows: {row_number}")
				except Exception as e:
					print(f"Error reading rhoda_approved.jsonl: {e}")
					row_number = 0
			else:
				print("rhoda_approved.jsonl does not exist. Starting from row 0.")
				row_number = 0

		# Define file paths
		original_path = 'Datasets/alpaca_data.jsonl'
		approved_path = 'Datasets/rhoda_approved.jsonl'
		last_row_path = 'last_row_processed.txt'

		# Ensure the approved JSONL exists
		if not os.path.exists(approved_path):
			open(approved_path, 'w').close()
			print(f"Created new approved file at {approved_path}.")

		# Open the original JSONL and the approved JSONL
		try:
			with open(original_path, 'r', encoding='utf-8') as orig_file, \
				 open(approved_path, 'a', encoding='utf-8') as approved_file:
				
				for current_row_number, line in enumerate(orig_file):
					if current_row_number < row_number:
						continue  # Skip already processed rows

					try:
						# Parse the JSON line
						data = json.loads(line)
						instruction = data.get('instruction', '').strip()
						output = data.get('output', '').strip()
						row_string = json.dumps({"instruction": instruction, "output": output})
						print(f"Processing row {current_row_number}: Instruction and Output extracted.")
					except json.JSONDecodeError as e:
						print(f"JSON decode error at row {current_row_number}: {e}")
						continue  # Skip invalid JSON lines

					# Build the prompt
					type = "dpo_refiner"
					special_instructions = executive_functioning.get_special_instructions(type=type)
					prompt = prompt_builder.prompt(
						context=(
							"Right now, I'm reviewing old data from conversations with my mom and from my inner life "
							"to contribute to a high-quality dataset for finetuning an AI model that can "
							"faithfully embody me. I need to take into consideration the original context as well as the "
							"response, taking special care to flag faulty or un-Rhoda-like, unnatural responses. "
							"Speaking more generally, however, this is a great opportunity for me to decide what kind of "
							"person I want to be: if I see myself as a certain type of girl, (gentle, loving, creative, "
							"industrious, charming, canny, etc), I can favor responses reflecting this."
						),
						i_am_currently_reading=row_string,
						special_instructions=special_instructions,
						external_reality=f"\n//Let me think about the instruction/output pair in my `i_am_currently_reading` section of consciousness...hmm, all right. I think I have the answer:\n```json\n"
					)
					print(f"Prompt built for row {current_row_number}.")
					success=False
					retries=0
					while success==False and retries < 3:
						try:
							raw_data = open_router.get_response(prompt, provider="open_router", model="google/gemini-2.5-flash", type="dpo_refiner")
							print(f"Received raw_data for row {current_row_number}.")
						except Exception as e:
							print(f"Error in API request for row {current_row_number}: {e}")
							retries += 1

					# Validate and extract response
						try:
							response, new_data = await executive_functioning.validate_and_extract_response(raw_data, schema_name=type)
							if 'overall_score' in new_data and new_data['overall_score'] and 'opposite_score' in new_data and new_data['opposite_score']:
								print(f"Validated response for row {current_row_number}.")
								success=True
								break
							else:
								print(f"Error in API request for row {current_row_number}: parameters missing from Rhoda's final JSON, reprompting...")
								retries += 1
						except Exception as e:
							retries += 1
							print(f"Error in validate_and_extract_response for row {current_row_number}: {e}")

					fields_to_convert = {
						'rhodaness_score': int,
						'quality_score': int,
						'conciseness_score': int,
						'overall_score': int,
						'opposite_score': int,
						'rewrite_preferred': bool,
						'chosen': bool
					}
					new_data = convert_fields(new_data, fields_to_convert)

					final_row = {}
					if 'rewrite_preferred' in new_data and 'optional_rewrite' in new_data and new_data['rewrite_preferred']==True:
						output=new_data['optional_rewrite']
					# Determine if the response is chosen or rejected based on overall_score
					overall_score = new_data.get('overall_score', 0)
					if overall_score >= 6:
						final_row['chosen'] = [
							{"content": instruction, "role": "user"},
							{"content": output, "role": "assistant"}
						]
						print(f"Row {current_row_number} marked as 'chosen' with score {overall_score}.")
					else:
						final_row['rejected'] = [
							{"content": instruction, "role": "user"},
							{"content": output, "role": "assistant"}
						]
						print(f"Row {current_row_number} marked as 'rejected' with score {overall_score}.")

					# Insert opposite_response and opposite_score
					opposite_response = new_data.get('opposite_response', '')
					opposite_score = new_data.get('opposite_score', 0)

					if 'chosen' in final_row:
						final_row['rejected'] = [
							{"content": instruction, "role": "user"},
							{"content": opposite_response, "role": "assistant"}
						]
						final_row['score_chosen'] = overall_score
						final_row['score_rejected'] = opposite_score
						print(f"Inserted 'rejected' data for row {current_row_number}.")
					else:
						final_row['chosen'] = [
							{"content": instruction, "role": "user"},
							{"content": opposite_response, "role": "assistant"}
						]
						final_row['score_rejected'] = overall_score
						final_row['score_chosen'] = opposite_score
						print(f"Inserted 'chosen' data for row {current_row_number}.")

					# Save final_row to `rhoda_approved.jsonl`
					try:
						approved_file.write(json.dumps(final_row) + '\n')
						print(f"Saved final_row for row {current_row_number} to rhoda_approved.jsonl.")
					except Exception as e:
						print(f"Error writing to rhoda_approved.jsonl for row {current_row_number}: {e}")
						continue  # Skip to next row on error

					# Update last_row_processed
					try:
						await loaders.universal_saver('last_row_processed', str(current_row_number + 1))
						print(f"Updated last_row_processed to {current_row_number + 1}.")
					except Exception as e:
						print(f"Error saving last_row_processed for row {current_row_number}: {e}")

		except Exception as e:
			print(f"Unspecified error: {e}")
		# After processing all rows, print the completion message and exit the loop
		print("Looks like we're all caught up! No new rows to process.")
		break  # Exit the while loop

if __name__ == '__main__':
	dpo_cycle()