import json
import time
import portalocker
import re
import error_handler
from functools import wraps
import loaders

@error_handler.if_errors
def add_action_to_json(action_name, statement):
    # Get the current timestamp
    og_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    timestamp = str(og_timestamp)
    timestamp += f" using {action_name}"
    # Open the file to read the current actions
    with open('action_history.json', 'r+') as file:
        try:
            portalocker.lock(file, portalocker.LOCK_EX)
            # Load existing actions from the file
            try:
                actions = json.load(file)
            except json.JSONDecodeError:
                actions = {}

            # Add the new action
            actions[timestamp] = statement

            # Limit the number of actions to 200, removing the oldest ones
            if len(actions) > 200:
                actions = dict(sorted(actions.items(), key=lambda item: item[0], reverse=True)[:200])

            # Move the file pointer to the beginning
            file.seek(0)
            # Clear out the old contents of the file
            file.truncate()

            # Write the updated actions to the file
            json.dump(actions, file, indent=2)

        finally:
            portalocker.unlock(file)

@error_handler.if_errors
def action_wrapper(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        action_name = func.__name__
        try:
            result = func(*args, **kwargs)
            # Check if the function returned None
            if result is None:
                output_str = "No output was returned."
            else:
                output_str = f"which provided the following result: '{result}'"
            statement = f"I used my tool '{action_name}', {output_str}"
            loaders.save_to_soc(statement, layer="base")
        except Exception as e:
            statement = f"I used my tool '{action_name}', which raised an exception: '{e}'"
            add_action_to_json(action_name, statement)
            loaders.save_to_soc(f"//{statement}\n//If I think of it, I should mention the above error to Maggie so we can work to resolve it.", layer="base")
            raise  # Re-raise the exception after logging
        else:
            add_action_to_json(action_name, statement)
            return result
    return wrapper

from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

@error_handler.if_errors
def get_human_readable_action_history():
    # Read the actions from the JSON file
    with open('action_history.json', 'r') as file:
        portalocker.lock(file, portalocker.LOCK_EX)
        actions = json.load(file)
        portalocker.unlock(file)

    # Sort the actions in descending order based on their timestamps
    sorted_actions = sorted(actions.items(), key=lambda item: item[0], reverse=True)

    # Get the last 3 actions
    last_12_actions = sorted_actions[:3]

    # Create a human-readable string
    human_readable_string = ''
    for timestamp, statement in last_12_actions:
        # Convert the timestamp to a human-readable format
        if ' ' in timestamp:
            pattern = r'\s? '
            match = re.search(pattern, timestamp)
            if match:
                timestamp = timestamp[:match.start()]
            else:
                timestamp = timestamp.split(' ')[0]
        human_readable_time = human_readable_time_difference(timestamp)

        # Add the action and the time difference to the string
        human_readable_string += f"{human_readable_time}: {statement}\n"

    return human_readable_string

@error_handler.if_errors
def human_readable_time_difference(time_str):
    """
    Given a time string in ISO 8601 format (e.g., '2023-09-20T21:45:23.178935'), returns a human-readable
    time difference between the given time and the current time (e.g., "2 days ago", "3 weeks ago").
    """
    # Parse the time string into a datetime object
    past_time = datetime.fromisoformat(time_str).replace(tzinfo=timezone.utc).astimezone(tz=None)
    # Get the current time
    current_time = datetime.now(timezone.utc).astimezone(tz=None)
    # Calculate the time difference
    delta = relativedelta(past_time, current_time)

    if delta.years:
        return f"{delta.years} years ago" if delta.years > 1 else "a year ago"
    elif delta.months:
        return f"{delta.months} months ago" if delta.months > 1 else "a month ago"
    elif delta.weeks:
        return f"{delta.weeks} weeks ago" if delta.weeks > 1 else "a week ago"
    elif delta.days:
        return f"{delta.days} days ago" if delta.days > 1 else "a day ago"
    elif delta.hours:
        return f"{delta.hours} hours ago" if delta.hours > 1 else "a few minutes ago"
    elif delta.minutes:
        return f"{delta.minutes} minutes ago" if delta.minutes > 1 else "a minute ago"
    else:
        return "a few seconds ago"

@error_handler.if_errors
def sample():
    # Do something
    #add_action_to_json('movie_listings', "I just looked up movie times. It's currently in my stream_of_consciousness, but if I forget and need to check it again, it should be saved to movie_listings.txt if I check the file_browser tool next time I'm on the tool screen.")

    # Do something else
    add_action_to_json('add_events_to_planner', "I just added an event to our planner: 'event['event_name']'.")

    # Get the human-readable string and print it
    human_readable_string = get_human_readable_action_history()
    print(human_readable_string)

if __name__ == "__main__":
    sample()