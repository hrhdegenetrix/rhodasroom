# Compromise Module for Natural Language Processing

This module provides Python bindings to the [Compromise](https://github.com/spencermountain/compromise) natural language processing library for JavaScript. It enables text parsing, entity extraction, and grammar manipulation directly from Python.

## Installation

1. Make sure you have Node.js installed
2. Install required npm packages:
```
cd "Grammar Modules"
npm install compromise compromise-dates
```

## Available Functions

### Text Transformation
- `to_past_tense(text)`: Converts text to past tense

### Entity Extraction
- `extract_people(text)`: Extracts names of people from text
- `extract_locations(text)`: Extracts location names from text
- `extract_phone_numbers(text)`: Extracts phone numbers from text
- `extract_dates(text)`: Extracts dates with normalized representations
- `extract_times(text)`: Extracts times with normalized representations

### Text Analysis
- `extract_nouns(text)`: Extracts all nouns from text
- `extract_verbs(text)`: Extracts all verbs from text
- `extract_unique_words(text)`: Extracts potentially unique or rare words from text

### All-in-one Function
- `extract_all(text)`: Extracts people, places, dates, times, nouns, and verbs in a single call (more efficient)

## Usage Examples

```python
from run_compromise import extract_people, extract_locations, to_past_tense, extract_all

# Extract people from text
text = "John and Mary went to Paris last week to meet with Thomas at the Eiffel Tower."
people = extract_people(text)
print(people)  # ['John', 'Mary', 'Thomas']

# Extract locations
locations = extract_locations(text)
print(locations)  # ['Paris', 'Eiffel Tower']

# Convert to past tense
future_text = "Tomorrow I will go to the store and buy some groceries."
past_text = to_past_tense(future_text)
print(past_text)  # "Tomorrow I went to the store and bought some groceries."

# Extract multiple entities at once
all_data = extract_all(text)
print(all_data['people'])  # ['John', 'Mary', 'Thomas']
print(all_data['places'])  # ['Paris', 'Eiffel Tower']
print(all_data['dates'])   # [normalized date objects]
```

## Additional Information

This module wraps the Compromise JavaScript library, allowing Python applications to leverage Compromise's natural language processing capabilities. The module communicates with Node.js using subprocess calls, passing text and receiving structured data back.

For more advanced usage and information about Compromise's capabilities, see the [Compromise documentation](https://github.com/spencermountain/compromise/blob/master/README.md).

## Potential Improvements

- More robust error handling
- Additional Compromise functions like sentiment analysis
- Support for other languages using Compromise language plugins
- Performance optimizations for processing large texts
