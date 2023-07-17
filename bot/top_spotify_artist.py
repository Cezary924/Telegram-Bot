import random, requests, telebot
from bs4 import BeautifulSoup

import database, basic_commands

# list with artists data
artists = []

# fill artists list with artists data
def fill_artists():
    response = requests.request('GET', 'https://kworb.net/spotify/listeners.html')
    if response.status_code != 200:
        return -1
    soup = BeautifulSoup(response.content, "html.parser")
    soup = soup.find(class_ = 'addpos sortable')
    i = 1
    for row in soup.select('tbody tr'):
        artists.append([row.find(class_ = "text").select('a')[0].get_text(), row.find(class_ = "text").select('a')[0].get('href')])
        i += 1
        if i > 200:
            break
    return 0

# get index of artist named 'text'
def get_artist_index(text):
    for artist in artists:
        if text in artist:
            return artists.index(artist)
    return -1

def artist_text(number):
    return "Pseudonim: _" + artists[number][0] + "_\nMies. słuchacze: _#" + str(number + 1) + "_"
 
def victory(message, bot):
    artist = int(database.get_current_state(message).split("_")[2])
    text1 = database.get_message_text(message, 'topspotifyartist')
    text2 = database.get_message_text(message, 'command_topspotifyartist_victory')
    text = "*" + text1 + "*\n\n" + text2
    mess = bot.send_message(message.chat.id, text, parse_mode = 'Markdown')
    database.register_last_message(mess)
    database.save_current_state(message)

def defeat(message, bot):
    artist = int(database.get_current_state(message).split("_")[2])
    text1 = database.get_message_text(message, 'topspotifyartist')
    text2 = database.get_message_text(message, 'command_topspotifyartist_defeat')
    text = "*" + text1 + "*\n\n" + text2
    mess = bot.send_message(message.chat.id, text + artist_text(artist), parse_mode = 'Markdown')
    database.register_last_message(mess)
    database.save_current_state(message)

# handle /topspotifyartist command
def command_topspotifyartist(message, bot):
    state = database.get_current_state(message)
    if len(artists) == 0:
            if fill_artists() == -1:
                text1 = database.get_message_text(message, 'topspotifyartist')
                text2 = database.get_message_text(message, 'error')
                text = "*" + text1 + "*\n\n" + text2
                mess = bot.send_message(message.chat.id, text, 
                                parse_mode = 'Markdown')
    listeners = random.randint(0, 199)
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
    database.save_current_state(message, str(listeners) + "_topspotifyartist")
    #print(str(listeners) + ": " + str(artists[listeners]))

def topspotifyartist(message, bot):
    state = database.get_current_state(message)
    if "_topspotifyartist" in state:
        basic_commands.delete_previous_bot_message(message, bot)
        text1 = database.get_message_text(message, 'topspotifyartist')
        text2 = database.get_message_text(message, 'command_topspotifyartist_start')
        text = "*" + text1 + "*\n\n" + text2
        mess = bot.send_message(message.chat.id, text, parse_mode = 'Markdown')
        database.register_last_message(mess)
        text = "topspotifyartist_1_" + state.split('_')[0]
        database.save_current_state(message, text)
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
            if artist == int(state.split("_")[2]):
                text1 = database.get_message_text(message, 'topspotifyartist')
                text2 = database.get_message_text(message, 'command_topspotifyartist_correct')
                text = "*" + text1 + "*\n\n" + text2
                mess = bot.send_message(message.chat.id, text + "\n" + artist_text(artist) + " 🆗", parse_mode = 'Markdown')
                database.register_last_message(mess)
                victory(message, bot)
            else:
                text1 = database.get_message_text(message, 'topspotifyartist')
                text2 = database.get_message_text(message, 'command_topspotifyartist_wrong')
                if artist > int(state.split("_")[2]):
                    text3 = " ⬆️"
                else:
                    text3 = " ⬇️"
                text = "*" + text1 + "*\n\n" + text2
                mess = bot.send_message(message.chat.id, text + "\n" + artist_text(artist) + text3, parse_mode = 'Markdown')
                database.register_last_message(mess)
                text = state.split('_')[0] + "_" + str(int(state.split('_')[1]) + 1) + "_" + state.split('_')[2]
                database.save_current_state(message, text)
                state = text
                if "_6_" in state:
                    defeat(message, bot)