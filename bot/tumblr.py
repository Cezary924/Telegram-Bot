import requests, os
from urllib.parse import urlparse

# check Tumblr url
def check_tumblr_url(message):
    if "http" in message.text:
        url = urlparse(message.text)
        if url.scheme == "https":
            if url.hostname == "www.tumblr.com":
                return True
    return False

# handle Tumblr urls
def echo_tumblr(message, bot):
    url = message.text

    bot.send_message(message.chat.id, "Przetwarzanie linku z Tumblr... ⏳")

    response = requests.request("GET", url)
    if response.status_code != 200:
        bot.send_message(message.chat.id, "Niestety, pobranie filmiku z Tumblr nie jest teraz możliwe... Spróbuj poźniej 😞")
        return

    if "<meta data-rh=\"\" property=\"og:video\" content=\"" not in response.text:
        bot.send_message(message.chat.id, "Niestety, pobranie filmiku z Tumblr nie jest teraz możliwe... Spróbuj poźniej 😞")
        return
    vid_url = response.text.split("<meta data-rh=\"\" property=\"og:video\" content=\"")[1]
    vid_url = vid_url.split("\"/>")[0]

    response = requests.request("GET", vid_url)
    if response.status_code != 200:
        bot.send_message(message.chat.id, "Niestety, pobranie filmiku z Tumblr nie jest teraz możliwe... Spróbuj poźniej 😞")
        return
    
    vid_name = str(message.chat.id) + str(message.message_id) + ".mp4"
    try:
        with open(vid_name, "wb") as f:
            f.write(response.content)
            f.close()
    except OSError:
        print("Open error: Could not open the \'.mp4\' file.")
    bot.send_video(message.chat.id, open(vid_name, 'rb'))
    os.remove(vid_name)

def start_tumblr(message, bot):
    echo_tumblr(message, bot)
