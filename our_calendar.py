import json
from datetime import datetime, timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def holiday(query):
    # Open the calendar.json file and load its contents
    with open('calendar.json', 'r') as f:
        calendar_data = json.load(f)

    # Get the current date in the 'YYYY-MM-DD' format
    current_date = datetime.now().strftime('%Y-%m-%d')

    top_k = 3
    vectorizer = TfidfVectorizer()

    # Convert the holiday names to a list of strings
    holiday_names = list(calendar_data.values())

    # Create the TF-IDF vector space for holiday names
    tfidf_matrix = vectorizer.fit_transform(holiday_names)

    # Convert the query to a TF-IDF vector
    query_vector = vectorizer.transform([query])

    # Calculate the cosine similarity between the query vector and the holiday name vectors
    similarities = cosine_similarity(query_vector, tfidf_matrix)[0]

    # Get the indices of the top K highest similarities
    top_k_indices = similarities.argsort()[:-top_k-1:-1]

    results = []
    for index in top_k_indices:
        match = list(calendar_data.keys())[index]
        holiday_date = datetime.strptime(match, '%Y-%m-%d')
        days_diff = (holiday_date - datetime.now()).days

        holiday_name = calendar_data[match]
        if ',' in holiday_name:
            holiday_parts = holiday_name.split(', ')
            if len(holiday_parts) == 2:
                result = f"It's {days_diff} days until {holiday_parts[0]}, which is the same day as {holiday_parts[1]}."
            else:
                result = f"It's {days_diff} days until {', '.join(holiday_parts[:-1])}, and {holiday_parts[-1]}."
        else:
            if days_diff == 0:
                result = f"Today is {holiday_name}."
            elif days_diff < 0:
                result = f"{holiday_name} was {-days_diff} days ago."
            else:
                result = f"It's {days_diff} days until {holiday_name}."

        results.append(result)

    return "\n".join(results)

def holiday_check():
    # Open the calendar.json file and load its contents
    with open('calendar.json', 'r') as f:
        calendar_data = json.load(f)

    # Get the current date in the 'YYYY-MM-DD' format
    current_date = '2024-05-19'

    # Check if the current date is in the keys of the calendar_data dictionary
    if current_date in calendar_data:
        holidays = calendar_data[current_date].split(", ")

        # Create the holiday_sentence based on the number of holidays
        if len(holidays) == 1:
            holiday_sentence = f"According to my calendar, today is {holidays[0]}."
        elif len(holidays) == 2:
            holiday_sentence = f"According to my calendar, today is {holidays[0]}, as well as {holidays[1]}."
        else:
            holiday_sentence = f"According to my calendar, today is {', '.join(holidays[:-1])}, and {holidays[-1]}. It seems like there are a lot of holidays today!"
    else:
        holiday_sentence = ""
    return holiday_sentence

def advent_calendar():
    christmas_date = datetime.strptime("2024-12-25", "%Y-%m-%d")
    current_date = datetime.now()
    
    days_until_christmas = (christmas_date - current_date).days
    advent_calendar = ""
    if 24 >= days_until_christmas > 2:
        advent_calendar += f"How exciting--Christmas is {days_until_christmas} days away! "
    elif days_until_christmas > 1:
        advent_calendar += f"Christmas is in only 2 days! "
    elif days_until_christmas > 0:
        advent_calendar += f"Today is Christmas Eve, meaning Christmas is only a day away! "
    elif days_until_christmas == 0:
        advent_calendar += f"Today is Christmas Day! "

    return advent_calendar

def lent():
    with open('calendar.json', 'r') as f:
        calendar_data = json.load(f)

    current_date = datetime.now()
    current_date = current_date.date()
    lent = ""
    for key, value in calendar_data.items():
        if 'Ash Wednesday' in value:
            ash_wednesday_date = datetime.strptime(key, "%Y-%m-%d")
        if 'Holy Saturday' in value:
            if 'Orthodox' in value:
                continue
            else:
                holy_saturday_date = datetime.strptime(key, "%Y-%m-%d")
                holy_saturday_date = holy_saturday_date.date()
    # print(current_date)
    # print(ash_wednesday_date)
    ash_wednesday_date = ash_wednesday_date.date()
    if current_date < ash_wednesday_date:
        days_until_ash_wednesday = (ash_wednesday_date - current_date).days
        lent += f"There are {days_until_ash_wednesday} days left until Lent. "
    else:
        days_until_holy_saturday = (holy_saturday_date - current_date).days
        days_until_holy_saturday = days_until_holy_saturday - 5
        lent += f"There are {days_until_holy_saturday} days left in Lent. "
        if current_date.weekday() == 4:
            lent += f"Since today is Friday, we need to abstain from meat. "
        if current_date == ash_wednesday_date or current_date == holy_saturday_date:
            lent += f"This is a day of solemn fasting in the Roman Catholic Church. "

    return lent

# #Sample use
# query = "Pentecost"
# result = holiday(query)
# print(result)

# advent = advent_calendar()
# if advent:    
#     print(advent)
# else:
#     print(f"We're not in advent yet!")

if __name__ == "__main__":
    lent = lent()
    print(lent)