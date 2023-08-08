import requests, os
from urllib.parse import urlparse

import database, func

rapidapi = None

# open file containing RapidApi key and read from it
def read_rapidapi():
    global rapidapi
    rapidapi = func.tokens['twitter']

# handle Twitter URLs
def echo_twitter(message, bot):
    url = "https://twitter65.p.rapidapi.com/api/twitter/links"
    payload = { "url": message.text }
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": rapidapi,
        "X-RapidAPI-Host": "twitter65.p.rapidapi.com"
    }

    text = database.get_message_text(message, 'twitter_url_start')
    bot.send_message(message.chat.id, text)

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        text = database.get_message_text(message, 'twitter_url_error')
        bot.send_message(message.chat.id, text)
        return
    
    response = response.json()

    best_vid = None
    for vid in response[0]['urls']:
        if 'quality' in vid.keys():
            if best_vid == None or int(best_vid['quality']) < vid['quality']:
                best_vid = vid

    response = requests.request("GET", best_vid['url'], headers=headers)
    if response.status_code != 200:
        text = database.get_message_text(message, 'twitter_url_error')
        bot.send_message(message.chat.id, text)
        return
    
    vid_name = str(message.chat.id) + str(message.message_id) + ".mp4"
    try:
        with open(vid_name, "wb") as f:
            f.write(response.content)
    except OSError:
        func.print_log("ERROR: Open error - Could not open the \'.mp4\' file.")
    try:
        with open(vid_name, "rb") as f:
            bot.send_video(message.chat.id, f)
    except OSError:
        func.print_log("ERROR: Open error - Could not open the \'.mp4\' file.")
    finally:
        os.remove(vid_name)

def start_twitter(message, bot):
    if rapidapi == None:
        read_rapidapi()
    if rapidapi != None:
        echo_twitter(message, bot)
    else:
        text = database.get_message_text(message, 'twitter_url_error')
        bot.send_message(message.chat.id, text)
