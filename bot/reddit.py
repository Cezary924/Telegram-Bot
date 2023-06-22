import requests, os
from urllib.parse import urlparse
import moviepy.editor as mpe

import database

# check Reddit url
def check_reddit_url(message):
    if "http" in message.text:
        url = urlparse(message.text)
        if url.scheme == "https":
            if url.hostname == "www.reddit.com":
                return True
    return False

# handle Reddit urls
def echo_reddit(message, bot):
    if "?" in message.text:
        url = message.text.split("?")[0]
    else:
        url = message.text
    if url[len(url) - 1] == "/":
        url = url[:-1] + ".json"
    else:
        url = url + ".json"

    text = database.get_message_text(message, 'reddit_url_start')
    bot.send_message(message.chat.id, text)

    response = requests.request("GET", url, headers = {'User-agent': 'Reddit-Downloader'})
    if response.status_code != 200:
        text = database.get_message_text(message, 'reddit_url_error')
        bot.send_message(message.chat.id, text)
        return

    response = response.json()

    if response[0]["data"]["children"][0]["data"]["secure_media"]["reddit_video"] is None:
        text = database.get_message_text(message, 'reddit_url_error')
        bot.send_message(message.chat.id, text)
        return

    vid_url = response[0]["data"]["children"][0]["data"]["secure_media"]["reddit_video"]["fallback_url"]
    audio_url = response[0]["data"]["children"][0]["data"]["secure_media"]["reddit_video"]["fallback_url"].split("DASH_")[0] + "DASH_audio.mp4" + response[0]["data"]["children"][0]["data"]["secure_media"]["reddit_video"]["fallback_url"].split(".mp4")[1]

    audio = response[0]["data"]["children"][0]["data"]["secure_media"]["reddit_video"]["has_audio"]
    
    response = requests.request("GET", vid_url, headers = {'User-agent': 'Reddit-Downloader'})
    if response.status_code != 200:
        text = database.get_message_text(message, 'reddit_url_error')
        bot.send_message(message.chat.id, text)
        return
    vid_name = str(message.chat.id) + str(message.message_id) + "_vid.mp4"
    try:
        with open(vid_name, "wb") as f:
            f.write(response.content)
            f.close()
    except OSError:
        print("Open error: Could not open the \'.mp4\' file.")
        text = database.get_message_text(message, 'reddit_url_error')
        bot.send_message(message.chat.id, text)
        return

    if audio == False:
        bot.send_video(message.chat.id, open(vid_name, 'rb'))
        os.remove(vid_name)
        return
    
    response = requests.request("GET", audio_url, headers = {'User-agent': 'Reddit-Downloader'})
    if response.status_code != 200:
        text = database.get_message_text(message, 'reddit_url_error')
        bot.send_message(message.chat.id, text)
        return
    audio_name = str(message.chat.id) + str(message.message_id) + "_audio.mp3"
    try:
        with open(audio_name, "wb") as f:
            f.write(response.content)
            f.close()
    except OSError:
        print("Open error: Could not open the \'.mp4\' file.")
        text = database.get_message_text(message, 'reddit_url_error')
        bot.send_message(message.chat.id, text)
        return

    text = database.get_message_text(message, 'reddit_url_processing')
    bot.send_message(message.chat.id, text)

    final_name = str(message.chat.id) + str(message.message_id) + "_final.mp4"
    my_clip = mpe.VideoFileClip(vid_name)
    audio_background = mpe.AudioFileClip(audio_name)
    final_clip = my_clip.set_audio(audio_background)
    final_clip.write_videofile(final_name, fps=60, logger=None)
    
    bot.send_video(message.chat.id, open(final_name, 'rb'))

    os.remove(vid_name)
    os.remove(audio_name)
    os.remove(final_name)

def start_reddit(message, bot):
    echo_reddit(message, bot)
