import telebot, os, requests

import func, downloader

# handle Tumblr URLs
def start_tumblr(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    url = message.text
    downloader.send_start_message(bot, message, 'tumblr')

    # downloading vid
    response = requests.request("GET", url)
    if response.status_code != 200:
        downloader.send_error_message(bot, message, 'tumblr')
        return
    if "<meta data-rh=\"\" property=\"og:video\" content=\"" not in response.text:
        downloader.send_error_message(bot, message, 'tumblr')
        return
    vid_url = response.text.split("<meta data-rh=\"\" property=\"og:video\" content=\"")[1]
    vid_url = vid_url.split("\"/>")[0]
    response = requests.request("GET", vid_url)
    if response.status_code != 200:
        downloader.send_error_message(bot, message, 'tumblr')
        return
    vid_name = str(message.chat.id) + str(message.message_id) + ".mp4"
    try:
        with open(vid_name, "wb") as f:
            f.write(response.content)
    except OSError:
        func.print_log(message.text, "ERROR: Open error - Could not open the \'.mp4\' file.")
        downloader.send_error_message(bot, message, 'tumblr')
    
    # sending vid
    try:
        with open(vid_name, "rb") as f:
            bot.send_video(message.chat.id, f)
    except OSError:
        func.print_log(message.text, "ERROR: Open error - Could not open the \'.mp4\' file.")
        downloader.send_error_message(bot, message, 'tumblr')
    finally:
        os.remove(vid_name)