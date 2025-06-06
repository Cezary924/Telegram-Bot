import random, requests, telebot
from bs4 import BeautifulSoup
import base64

import database, basic_commands, func

# list with artists data
artists = []

# variable storing Spotify token
spotify_token = ""

# fill artists list with artists data
def fill_artists() -> int:
    response = requests.request('GET', 'https://kworb.net/spotify/listeners.html')
    if response.status_code != 200:
        return -1
    soup = BeautifulSoup(response.content, "html.parser")
    soup = soup.find(class_ = 'sortable')
    i = 1
    for row in soup.select('tbody tr'):
        try:
            artist_name = row.find(class_ = "text").select('a')[0].get_text()
            artist_kworb_link = 'https://kworb.net/spotify/' + row.find(class_ = "text").select('a')[0].get('href')
        except:
            pass
        else:
            artist_song_name = None
            artist_song_link = None
            artist_genre = None
            artists.append([artist_name, artist_kworb_link, artist_song_name, artist_song_link, artist_genre])
        i += 1
        if i > 200:
            break
    return 0

# get Spotify Bearer token
def get_spotify_token() -> int:
    headers = {'Authorization': 'Basic %s' % base64.b64encode(str(func.tokens['spotify_id'] + ':' + func.tokens['spotify_secret']).encode('ascii')).decode('ascii')}
    data = {
        'grant_type': 'client_credentials',
        'json': True
        }
    response = requests.request('POST', 'https://accounts.spotify.com/api/token', data=data, headers=headers)
    if response.status_code != 200:
        return -1
    else:
        response = response.json()
        global spotify_token
        spotify_token = response['access_token']
        return 0

# get more info about specific artist
def add_info_about_artist(listeners: int) -> int:
    response = requests.request('GET', artists[listeners][1])
    if response.status_code != 200:
        return -1
    soup = BeautifulSoup(response.content, "html.parser")
    soup = soup.select('tbody tr td div')[0]
    try:
        artists[listeners][2] = soup.get_text()
        artists[listeners][3] = soup.find('a', href=True)['href']
    except:
        pass
    headers = {
        "Authorization": "Bearer " + spotify_token,
        "Content-Type": "application/json"
        }
    response = requests.request('GET', 'https://api.spotify.com/v1/artists/' + artists[listeners][1].split('/artist/')[1].split('_songs')[0], headers=headers)
    if response.status_code != 200:
        if get_spotify_token() == -1:
            return -1
        headers = {
            "Authorization": "Bearer " + spotify_token,
            "Content-Type": "application/json"
            }
        response = requests.request('GET', 'https://api.spotify.com/v1/artists/' + artists[listeners][1].split('/artist/')[1].split('_songs')[0], headers=headers)
        if response.status_code != 200:
            return -1
    response = response.json()
    try:
        artists[listeners][4] = response['genres'][0].capitalize()
    except:
        pass
    return 0

# get index of artist named 'text'
def get_artist_index(text: str) -> int:
    for artist in artists:
        if text in artist:
            index = artists.index(artist)
            if add_info_about_artist(index) == -1:
                return -1
            return index
    return -1

# get string with details about artist
def artist_text(message: telebot.types.Message, number: int, final_number: int = None) -> str:
    if final_number == None:
        return database.get_message_text(message, 'nickname') + ": _" + artists[number][0] + "_\n" + database.get_message_text(message, 'genre') + ": _" + str(artists[number][4]) + "_\n" + database.get_message_text(message, 'monthly_listeners') + ": _#" + str(number + 1) + "_"
    else:
        if number > final_number:
            text1 = " ⬆️"
        elif number == final_number:
            text1 = " 🆗"
        else:
            text1 = " ⬇️"
        if artists[number][0] > artists[final_number][0]:
            text2 = " ⬆️"
        elif artists[number][0] == artists[final_number][0]:
            text2 = " 🆗"
        else:
            text2 = " ⬇️"
        if artists[number][4] == artists[final_number][4]:
            text3 = " 🆗"
        else:
            text3 = " 🆖"
        return database.get_message_text(message, 'nickname') + ": _" + artists[number][0] + "_" + text2 + "\n" + database.get_message_text(message, 'genre') + ": _" + str(artists[number][4] if artists[number][4] else '???') + "_" + text3 + "\n" + database.get_message_text(message, 'monthly_listeners') + ": _#" + str(number + 1) + "_" + text1
    
# get string with artist's most streamed song
def song_text(message: telebot.types.Message, number: int) -> str:
    return database.get_message_text(message, 'command_topspotifyartist_most_streamed_song') + ": _" + artists[number][2] + " (" + artists[number][3] + ")_\n"

# end function of Top Spotify Artist loop, start when artist has been guessed
def victory(message: telebot.types.Message, bot: telebot.TeleBot, artist: int) -> None:
    text1 = database.get_message_text(message, 'topspotifyartist')
    text2 = database.get_message_text(message, 'command_topspotifyartist_victory')
    text = "*" + text1 + "*\n\n" + text2
    mess = bot.send_message(message.chat.id, text, parse_mode = 'Markdown')
    database.register_last_message(mess)
    database.set_current_state(message)

# end function of Top Spotify Artist loop, start when artist has not been guessed
def defeat(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    artist = int(database.get_current_state(message).split("_")[2])
    text1 = database.get_message_text(message, 'topspotifyartist')
    text2 = database.get_message_text(message, 'command_topspotifyartist_defeat')
    text = "*" + text1 + "*\n\n" + text2
    mess = bot.send_message(message.chat.id, text + artist_text(message, artist) + "\n" + song_text(message, artist), parse_mode = 'Markdown')
    database.register_last_message(mess)
    database.set_current_state(message)

# handle /topspotifyartist command
def command_topspotifyartist(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    state = database.get_current_state(message)
    if len(artists) == 0:
            if fill_artists() == -1:
                text1 = database.get_message_text(message, 'topspotifyartist')
                text2 = database.get_message_text(message, 'error')
                text = "*" + text1 + "*\n\n" + text2
                mess = bot.send_message(message.chat.id, text, 
                                parse_mode = 'Markdown')
                database.set_current_state(mess)
                return
    listeners = random.randint(0, 199)
    if add_info_about_artist(listeners) == -1:
        text1 = database.get_message_text(message, 'topspotifyartist')
        text2 = database.get_message_text(message, 'error')
        text = "*" + text1 + "*\n\n" + text2
        mess = bot.send_message(message.chat.id, text, 
                                parse_mode = 'Markdown')
        database.set_current_state(mess)
        return
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'start')
    start_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "topspotifyartist")
    markup.add(start_button)
    text1 = database.get_message_text(message, 'topspotifyartist')
    text2 = database.get_message_text(message, 'command_topspotifyartist')
    text = "*" + text1 + "*\n\n" + text2
    mess = bot.send_message(message.chat.id, text, 
                    parse_mode = 'Markdown',
                    reply_markup = markup)
    database.register_last_message(mess)
    database.set_current_state(message, str(listeners) + "_topspotifyartist")

# main function
def topspotifyartist(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    state = database.get_current_state(message)
    if "_topspotifyartist" in state:
        basic_commands.delete_previous_bot_message(message, bot)
        text1 = database.get_message_text(message, 'topspotifyartist')
        text2 = database.get_message_text(message, 'command_topspotifyartist_start')
        text = "*" + text1 + "*\n\n" + text2
        mess = bot.send_message(message.chat.id, text, parse_mode = 'Markdown')
        database.register_last_message(mess)
        text = "topspotifyartist_1_" + state.split('_')[0]
        database.set_current_state(message, text)
        state = text
    elif "_1_" in state or "_2_" in state or "_3_" in state or "_4_" in state or "_5_" in state:
        artist = get_artist_index(message.text)
        if artist == -1:
            text1 = database.get_message_text(message, 'topspotifyartist')
            text2 = database.get_message_text(message, 'command_topspotifyartist_unknown')
            text = "*" + text1 + "*\n\n" + text2
            mess = bot.send_message(message.chat.id, text, parse_mode = 'Markdown')
            database.register_last_message(mess)
        else:
            if artists[artist][4] is None:
                if add_info_about_artist(artist) == -1:
                    text1 = database.get_message_text(message, 'topspotifyartist')
                    text2 = database.get_message_text(message, 'error')
                    text = "*" + text1 + "*\n\n" + text2
                    mess = bot.send_message(message.chat.id, text, 
                                            parse_mode = 'Markdown')
                    database.set_current_state(mess)
                    return
            if artist == int(state.split("_")[2]):
                text1 = database.get_message_text(message, 'topspotifyartist')
                text2 = database.get_message_text(message, 'command_topspotifyartist_correct')
                text = "*" + text1 + "*\n\n" + text2
                mess = bot.send_message(message.chat.id, text + "\n" + artist_text(message, artist, int(state.split("_")[2])) + "\n" + song_text(message, artist), parse_mode = 'Markdown')
                database.register_last_message(mess)
                victory(message, bot, artist)
            else:
                text1 = database.get_message_text(message, 'topspotifyartist')
                text2 = database.get_message_text(message, 'command_topspotifyartist_wrong')
                text = "*" + text1 + "*\n\n" + text2
                mess = bot.send_message(message.chat.id, text + "\n" + artist_text(message, artist, int(state.split("_")[2])), parse_mode = 'Markdown')
                database.register_last_message(mess)
                text = state.split('_')[0] + "_" + str(int(state.split('_')[1]) + 1) + "_" + state.split('_')[2]
                database.set_current_state(message, text)
                state = text
                if "_6_" in state:
                    defeat(message, bot)