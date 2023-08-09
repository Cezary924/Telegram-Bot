import requests, os
import moviepy.editor as mpe

import func, downloader

# handle Reddit URLs
def start_reddit(message, bot):
    if "?" in message.text:
        url = message.text.split("?")[0]
    else:
        url = message.text
    if url[len(url) - 1] == "/":
        url = url[:-1] + ".json"
    else:
        url = url + ".json"
    downloader.send_start_message(bot, message, 'reddit')

    # downloading vid
    response = requests.request("GET", url, headers = {'User-agent': 'Reddit-Downloader'})
    if response.status_code != 200:
        func.print_log("ERROR: Module error - Reddit.")
        downloader.send_error_message(bot, message, 'reddit')
        return
    try:
        response = response.json()
    except Exception as err:
        func.print_log("ERROR: Module error - Reddit.")
        downloader.send_error_message(bot, message, 'reddit')
        return
    try:
        vid_url = response[0]["data"]["children"][0]["data"]["secure_media"]["reddit_video"]["fallback_url"]
        audio_url = response[0]["data"]["children"][0]["data"]["secure_media"]["reddit_video"]["fallback_url"].split("DASH_")[0] + "DASH_audio.mp4" + response[0]["data"]["children"][0]["data"]["secure_media"]["reddit_video"]["fallback_url"].split(".mp4")[1]
    except Exception as err:
        func.print_log("ERROR: Module error - Reddit.")
        downloader.send_error_message(bot, message, 'reddit')
        return
    response = requests.request("GET", vid_url, headers = {'User-agent': 'Reddit-Downloader'})
    if response.status_code != 200:
        func.print_log("ERROR: Module error - Reddit.")
        downloader.send_error_message(bot, message, 'reddit')
        return
    vid_name = str(message.chat.id) + str(message.message_id) + "_vid.mp4"
    try:
        with open(vid_name, "wb") as f:
            f.write(response.content)
    except OSError:
        func.print_log("ERROR: Open error - Could not open the \'.mp4\' file.")
        downloader.send_error_message(bot, message, 'reddit')
        return
    response = requests.request("GET", audio_url, headers = {'User-agent': 'Reddit-Downloader'})
    if response.status_code != 200:
        audio = False
    else:
        audio = True
    
    # sending vid without audio
    if audio == False:
        try:
            with open(vid_name, "rb") as f:
                bot.send_video(message.chat.id, f)
        except OSError:
            func.print_log("ERROR: Open error - Could not open the \'.mp4\' file.")
            downloader.send_error_message(bot, message, 'reddit')
        finally:
            os.remove(vid_name)
        return

    # downloading audio
    audio_name = str(message.chat.id) + str(message.message_id) + "_audio.mp3"
    try:
        with open(audio_name, "wb") as f:
            f.write(response.content)
    except OSError:
        func.print_log("ERROR: Open error - Could not open the \'.mp4\' file.")
        downloader.send_error_message(bot, message, 'reddit')
        return

    # sending vid+audio
    downloader.send_processing_message(bot, message, 'youtube')
    final_name = str(message.chat.id) + str(message.message_id) + "_final.mp4"
    my_clip = mpe.VideoFileClip(vid_name)
    audio_background = mpe.AudioFileClip(audio_name)
    final_clip = my_clip.set_audio(audio_background)
    final_clip.write_videofile(final_name, fps=60, logger=None)
    try:
        with open(vid_name, "rb") as f:
            bot.send_video(message.chat.id, f)
    except OSError:
        func.print_log("ERROR: Open error - Could not open the \'.mp4\' file.")
        downloader.send_error_message(bot, message, 'reddit')
    finally:
        os.remove(vid_name)
    os.remove(audio_name)
    os.remove(final_name)