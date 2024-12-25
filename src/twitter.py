import telebot, requests, os

import func, downloader

# handle Twitter URLs
def start_twitter(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    url = "https://twitter-downloader-download-twitter-videos-gifs-and-images.p.rapidapi.com/status"
    querystring = {"url" : message.text}
    headers = {
        "X-RapidAPI-Key": func.tokens['rapidapi'],
        "X-RapidAPI-Host": "twitter-downloader-download-twitter-videos-gifs-and-images.p.rapidapi.com"
    }
    downloader.send_start_message(bot, message, 'twitter')

    # downloading vid
    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code != 200:
        func.print_log(message.text, "ERROR: Module error - Twitter.")
        downloader.send_error_message(bot, message, 'twitter')
        return
    try:
        response = response.json()
    except Exception as err:
        func.print_log(message.text, "ERROR: Module error - Twitter.")
        downloader.send_error_message(bot, message, 'twitter')
        return
    best_vid = None
    if 'media' not in response or response['media'] is None or response['media']['video'] is None:
        func.print_log(message.text, "ERROR: Module error - Twitter.")
        downloader.send_error_message(bot, message, 'twitter')
        return
    for vid in response['media']['video']['videoVariants']:
        if 'bitrate' in vid.keys():
            if best_vid == None or int(best_vid['bitrate']) < vid['bitrate']:
                best_vid = vid
    response = requests.request("GET", best_vid['url'], headers=headers)
    if response.status_code != 200:
        func.print_log(message.text, "ERROR: Module error - Twitter.")
        downloader.send_error_message(bot, message, 'twitter')
        return
    vid_name = str(message.chat.id) + str(message.message_id) + ".mp4"
    try:
        with open(vid_name, "wb") as f:
            f.write(response.content)
    except OSError:
        func.print_log(message.text, "ERROR: Open error - Could not open the \'.mp4\' file.")
        downloader.send_error_message(bot, message, 'twitter')
        return
    
    # sending vid
    try:
        with open(vid_name, "rb") as f:
            bot.send_video(message.chat.id, f)
    except OSError:
        func.print_log(message.text, "ERROR: Open error - Could not open the \'.mp4\' file.")
        downloader.send_error_message(bot, message, 'twitter')
    finally:
        os.remove(vid_name)