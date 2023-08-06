import requests, os
from urllib.parse import urlparse

import database, func

# check Tumblr url
def check_tumblr_url(message):
    if "http" in message.text:
        url = urlparse(message.text)
        if url.scheme == "https":
            if url.hostname == "www.tumblr.com":
                return True
    return False

# handle Tumblr urls
def echo_tumblr(message, bot):
    url = message.text

    text = database.get_message_text(message, 'tumblr_url_start')
    bot.send_message(message.chat.id, text)

    response = requests.request("GET", url)
    if response.status_code != 200:
        text = database.get_message_text(message, 'tumblr_url_error')
        bot.send_message(message.chat.id, text)
        return

    if "<meta data-rh=\"\" property=\"og:video\" content=\"" not in response.text:
        text = database.get_message_text(message, 'tumblr_url_error')
        bot.send_message(message.chat.id, text)
        return
        
    vid_url = response.text.split("<meta data-rh=\"\" property=\"og:video\" content=\"")[1]
    vid_url = vid_url.split("\"/>")[0]

    response = requests.request("GET", vid_url)
    if response.status_code != 200:
        text = database.get_message_text(message, 'tumblr_url_error')
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

def start_tumblr(message, bot):
    echo_tumblr(message, bot)
