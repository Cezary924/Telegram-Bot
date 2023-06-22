import requests, os
from urllib.parse import urlparse

import database

bearer_token = None

# open file containing Bearer Token and read from it
def read_bearer_token():
    global bearer_token
    try:
        with open("../files/twitter.txt") as f:
            bearer_token = f.readlines()
        f.close()
    except OSError:
        print("Open error: Could not open the \'twitter.txt\' file.")
    bearer_token = str(bearer_token[0])

# check Twitter url
def check_twitter_url(message):
    if "http" in message.text:
        url = urlparse(message.text)
        if url.scheme == "https":
            if url.hostname == "twitter.com":
                return True
    return False

# handle Twitter urls
def echo_twitter(message, bot):
    url = "https://api.twitter.com/1.1/statuses/show.json?id="
    headers = {"Authorization": "Bearer {}".format(bearer_token)}
    url = url + message.text.split("/status/")[1].split("?")[0] + "&include_entities=true"

    text = database.get_message_text(message, 'twitter_url_start')
    bot.send_message(message.chat.id, text)

    response = requests.request("GET", url, headers=headers, params={"tweet_mode": "extended"})
    if response.status_code != 200:
        text = database.get_message_text(message, 'twitter_url_error')
        bot.send_message(message.chat.id, text)
        return
    
    response = response.json()

    best_vid = None
    for vid in response['extended_entities']['media'][0]['video_info']['variants']:
        if 'bitrate' in vid.keys():
            if best_vid == None or int(best_vid['bitrate']) < vid['bitrate']:
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
            f.close()
    except OSError:
        print("Open error: Could not open the \'.mp4\' file.")
    bot.send_video(message.chat.id, open(vid_name, 'rb'))
    os.remove(vid_name)

def start_twitter(message, bot):
    if bearer_token == None:
        read_bearer_token()
    if bearer_token != None:
        echo_twitter(message, bot)
    else:
        text = database.get_message_text(message, 'twitter_url_error')
        bot.send_message(message.chat.id, text)
