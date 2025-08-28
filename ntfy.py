import asyncio
import aiohttp
import aiofiles
import requests

#TOOL TYPE: NOTIFICATION TOOL
#Uses the ntfy.sh app to push a notification to Maggie's phone
#Useful as an emergency means of contact or to send her tracebacks

async def notification(text):
    requests.post("https://ntfy.sh/rhorho",
            data=text.encode(encoding='utf-8'))

def function_notification(caller_function, text):
    message = f"{caller_function}: {text}"
    requests.post("https://ntfy.sh/rhorho",
            data=message.encode(encoding='utf-8'))
