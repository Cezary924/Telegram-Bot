import telebot, requests, os

import func, downloader

# handle TikTok URLs
def start_tiktok(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    url = "https://tiktok-full-info-without-watermark.p.rapidapi.com/vid/index"
    querystring = {"url": message.text}
    headers = {
        "X-RapidAPI-Key": func.tokens['rapidapi'],
        "X-RapidAPI-Host": "tiktok-full-info-without-watermark.p.rapidapi.com"
    }
    downloader.send_start_message(bot, message, 'tiktok')

    # downloading vid
    response = requests.request("GET", url, headers=headers, params=querystring)
    if response.status_code != 200:
        func.print_log("ERROR: Module error - TikTok.")
        downloader.send_error_message(bot, message, 'tiktok')
        return
    vid_url = response.json()['video'][0]
    response = requests.request("GET", vid_url, headers=headers, params=querystring)
    if response.status_code != 200:
        func.print_log("ERROR: Module error - TikTok.")
        downloader.send_error_message(bot, message, 'tiktok')
        return
    vid_name = str(message.chat.id) + str(message.message_id) + ".mp4"
    try:
        with open(vid_name, "wb") as f:
            f.write(response.content)
    except OSError:
        func.print_log("ERROR: Open error - Could not open the \'.mp4\' file.")
        downloader.send_error_message(bot, message, 'tiktok')
        return
    
    # sending vid
    try:
        with open(vid_name, "rb") as f:
            bot.send_video(message.chat.id, f)
    except OSError:
        func.print_log("ERROR: Open error - Could not open the \'.mp4\' file.")
        downloader.send_error_message(bot, message, 'tiktok')
    finally:
        os.remove(vid_name)
