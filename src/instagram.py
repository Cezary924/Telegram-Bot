import telebot, os
import instaloader

import func, downloader

# handle Instagram URLs
def start_instagram(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    url = message.text
    downloader.send_start_message(bot, message, 'instagram')

    # downloading pics & vids
    loader = instaloader.Instaloader(quiet = True)
    try:
        post = instaloader.Post.from_shortcode(loader.context, url.split("/")[-2])
    except Exception as err:
        func.print_log(message.text, "ERROR: Module error - Instagram.")
        downloader.send_error_message(bot, message, 'instagram')
        return
    folder_name = str(message.chat.id) + str(message.message_id)
    if loader.download_post(post, folder_name) != True:
        func.print_log(message.text, "ERROR: Module error - Instagram.")
        downloader.send_error_message(bot, message, 'instagram')
    downloaded_files = os.listdir("./" + folder_name)
    downloaded_files = [val for val in downloaded_files if not val.endswith(".txt") and not val.endswith(".json.xz")]
    downloaded_files.sort()

    # sending pics & vids
    while(len(downloaded_files) > 0):
        if len(downloaded_files) > 1:
            if downloaded_files[0].split('.')[0] + '.mp4' == downloaded_files[1]:
                media_name = downloaded_files[1]
                try:
                    with open(folder_name + "\\" + media_name, 'rb') as f:
                        bot.send_video(message.chat.id, f, timeout=10000)
                except Exception as err:
                    func.print_log(message.text, "ERROR: Open error - Could not open the \'.mp4\' file.")
                    downloader.send_error_message(bot, message, 'instagram')
                finally:
                    downloaded_files.remove(media_name)
                    downloaded_files.remove(downloaded_files[0])
                continue
        media_name = downloaded_files[0]
        try:
            with open(folder_name + "\\" + media_name, 'rb') as f:
                bot.send_photo(message.chat.id, f)
        except Exception as err:
            func.print_log(message.text, "ERROR: Open error - Could not open the \'.jpg\' file.")
            downloader.send_error_message(bot, message, 'instagram')
        finally:
            downloaded_files.remove(media_name)
        
    func.remove_directory(folder_name, os.curdir + "/" + folder_name)
