import requests, os

import func, downloader

# handle Twitter URLs
def start_twitter(message, bot):
    url = "https://twitter65.p.rapidapi.com/api/twitter/links"
    payload = { "url": message.text }
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": func.tokens['twitter'],
        "X-RapidAPI-Host": "twitter65.p.rapidapi.com"
    }
    downloader.send_start_message(bot, message, 'twitter')

    # downloading vid
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        func.print_log("ERROR: Module error - Twitter.")
        downloader.send_error_message(bot, message, 'twitter')
        return
    try:
        response = response.json()
    except Exception as err:
        func.print_log("ERROR: Module error - Twitter.")
        downloader.send_error_message(bot, message, 'twitter')
        return
    best_vid = None
    for vid in response[0]['urls']:
        if 'quality' in vid.keys():
            if best_vid == None or int(best_vid['quality']) < vid['quality']:
                best_vid = vid
    response = requests.request("GET", best_vid['url'], headers=headers)
    if response.status_code != 200:
        func.print_log("ERROR: Module error - Twitter.")
        downloader.send_error_message(bot, message, 'twitter')
        return
    vid_name = str(message.chat.id) + str(message.message_id) + ".mp4"
    try:
        with open(vid_name, "wb") as f:
            f.write(response.content)
    except OSError:
        func.print_log("ERROR: Open error - Could not open the \'.mp4\' file.")
        downloader.send_error_message(bot, message, 'twitter')
        return
    
    # sending vid
    try:
        with open(vid_name, "rb") as f:
            bot.send_video(message.chat.id, f)
    except OSError:
        func.print_log("ERROR: Open error - Could not open the \'.mp4\' file.")
        downloader.send_error_message(bot, message, 'twitter')
    finally:
        os.remove(vid_name)