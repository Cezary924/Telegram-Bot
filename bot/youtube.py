import os
from pytube import YouTube

import func, downloader

# handle Youtube URLs
def start_youtube(message, bot):
    url = message.text
    downloader.send_start_message(bot, message, 'youtube')

    # downloading vid
    downloader.send_processing_message(bot, message, 'youtube')
    vid_name = str(message.chat.id) + str(message.message_id) + ".mp4"
    try:
        YouTube(url).streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first().download(filename=vid_name)
    except Exception as err:
        func.print_log("ERROR: Module error - YouTube.")
        downloader.send_error_message(bot, message, 'youtube')
        return

    # sending vid
    try:
        with open(vid_name, 'rb') as f:
            bot.send_video(message.chat.id, f, timeout=10000)
    except Exception as err:
        func.print_log("ERROR: Open error - Could not open the \'.mp4\' file.")
        downloader.send_error_message(bot, message, 'youtube')
    finally:
        os.remove(vid_name)