import telebot, requests, os

import func, downloader

# handle TikTok URLs
def start_tiktok(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    url = "https://tiktok-scraper7.p.rapidapi.com/"
    querystring = {"url": message.text, "hd": "1"}
    headers = {
        "X-RapidAPI-Key": func.tokens['rapidapi'],
        "X-RapidAPI-Host": "tiktok-scraper7.p.rapidapi.com"
    }
    downloader.send_start_message(bot, message, 'tiktok')

    # downloading vid/pics
    response = requests.request("GET", url, headers=headers, params=querystring)
    if response.status_code != 200:
        func.print_log(message.text, "ERROR: Module error - TikTok.")
        downloader.send_error_message(bot, message, 'tiktok')
        return
    try:
        data = response.json()['data']
        folder_name = str(message.chat.id) + str(message.message_id)
        func.create_directory(folder_name)
        if data['duration'] == 0 and data['play'] == data['music']:
            images_urls = data['images']
            i = 0
            for image_url in images_urls:
                response = requests.request("GET", image_url, headers=headers, params=querystring)
                if response.status_code != 200:
                    func.print_log(message.text, "ERROR: Module error - TikTok.")
                    downloader.send_error_message(bot, message, 'tiktok')
                    return
                img_name = str(message.chat.id) + str(message.message_id) + '_' + str(i) + ".jpg"
                i += 1
                try:
                    with open(folder_name + '/' + img_name, "wb") as f:
                        f.write(response.content)
                except OSError:
                    func.print_log(message.text, "ERROR: Open error - Could not open the \'.jpg\' file.")
                    downloader.send_error_message(bot, message, 'tiktok')
                    return
        else:
            vid_url = data['hdplay']
            response = requests.request("GET", vid_url, headers=headers, params=querystring)
            if response.status_code != 200:
                func.print_log(message.text, "ERROR: Module error - TikTok.")
                downloader.send_error_message(bot, message, 'tiktok')
                return
            vid_name = str(message.chat.id) + str(message.message_id) + ".mp4"
            try:
                with open(folder_name + '/' + vid_name, "wb") as f:
                    f.write(response.content)
            except OSError:
                func.print_log(message.text, "ERROR: Open error - Could not open the \'.mp4\' file.")
                downloader.send_error_message(bot, message, 'tiktok')
                return
    except:
        func.print_log(message.text, "ERROR: Module error - TikTok.")
        downloader.send_error_message(bot, message, 'tiktok')
        return
    
    # sending vid/pics
    downloaded_files = os.listdir("./" + folder_name)
    for file in downloaded_files:
        if file.endswith('.mp4'):
            try:
                with open(folder_name + '/' + file, "rb") as f:
                    bot.send_video(message.chat.id, f)
            except OSError:
                func.print_log(message.text, "ERROR: Open error - Could not open the \'.mp4\' file.")
                downloader.send_error_message(bot, message, 'tiktok')
        else:
            try:
                with open(folder_name + '/' + file, "rb") as f:
                    bot.send_photo(message.chat.id, f)
            except OSError:
                func.print_log(message.text, "ERROR: Open error - Could not open the \'.jpg\' file.")
                downloader.send_error_message(bot, message, 'tiktok')
    func.remove_directory(folder_name, os.curdir + "\\" + folder_name)
    