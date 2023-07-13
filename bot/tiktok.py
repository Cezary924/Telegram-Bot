import requests, os
from urllib.parse import urlparse

import database, func

rapidapi = None

# open file containing RapidAPI key and read from it
def read_rapidapi():
    global rapidapi
    rapidapi = func.tokens['tiktok']

# check TikTok url
def check_tiktok_url(message):
    if "http" in message.text:
        url = urlparse(message.text)
        if url.scheme == "http" or url.scheme == "https":
            if url.hostname == "vm.tiktok.com" or url.hostname == "www.tiktok.com":
                return True
    return False

# handle TikTok urls
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
            f.close()
    except OSError:
        func.print_log("ERROR: Open error - Could not open the \'.mp4\' file.")
    bot.send_video(message.chat.id, open(vid_name, 'rb'))
    os.remove(vid_name)

def start_tiktok(message, bot):
    if rapidapi == None:
        read_rapidapi()
    if rapidapi != None:
        echo_tiktok(message, bot)
    else:
        text = database.get_message_text(message, 'tiktok_url_error')
        bot.send_message(message.chat.id, text)
