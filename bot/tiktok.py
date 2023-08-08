import requests, os
from urllib.parse import urlparse

import database, func

rapidapi = None

# open file containing RapidAPI key and read from it
def read_rapidapi():
    global rapidapi
    rapidapi = func.tokens['tiktok']

# handle TikTok URLs
def echo_tiktok(message, bot):
    url = "https://tiktok-full-info-without-watermark.p.rapidapi.com/vid/index"
    querystring = {"url": message.text}
    headers = {
        "X-RapidAPI-Key": rapidapi,
        "X-RapidAPI-Host": "tiktok-full-info-without-watermark.p.rapidapi.com"
    }

    text = database.get_message_text(message, 'tiktok_url_start')
    bot.send_message(message.chat.id, text)

    response = requests.request("GET", url, headers=headers, params=querystring)
    if response.status_code != 200:
        text = database.get_message_text(message, 'tiktok_url_error')
        bot.send_message(message.chat.id, text)
        return
    
    vid_url = response.json()['video'][0]
    response = requests.request("GET", vid_url, headers=headers, params=querystring)
    if response.status_code != 200:
        text = database.get_message_text(message, 'tiktok_url_error')
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

def start_tiktok(message, bot):
    if rapidapi == None:
        read_rapidapi()
    if rapidapi != None:
        echo_tiktok(message, bot)
    else:
        text = database.get_message_text(message, 'tiktok_url_error')
        bot.send_message(message.chat.id, text)
