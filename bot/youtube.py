import os
from pytube import YouTube
from urllib.parse import urlparse

import database

# handle Youtube URLs
    url = message.text

    text = database.get_message_text(message, 'youtube_url_start')
    bot.send_message(message.chat.id, text)

    vid_name = str(message.chat.id) + str(message.message_id) + ".mp4"
    YouTube(url).streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first().download(filename=vid_name)
    
    text = database.get_message_text(message, 'youtube_url_processing')
    bot.send_message(message.chat.id, text)

    try:
        with open(vid_name, 'rb') as f:
            bot.send_video(message.chat.id, f, timeout=10000)
    except Exception as err:
        text = database.get_message_text(message, 'youtube_url_error')
        bot.send_message(message.chat.id, text)
    finally:
        os.remove(vid_name)

def start_youtube(message, bot):
    echo_youtube(message, bot)
