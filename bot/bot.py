import telebot, os

import tiktok, twitter

# get path of directory containing bot script
dir = os.path.dirname(os.path.realpath(__file__)) + "/"

# change current working directory to 'dir'
os.chdir(dir)

# open file containing token and read from it
try:
    with open("../files/telegram.txt") as f:
        token = f.readlines()
    f.close()
except OSError:
    print("Open error: Could not open the \'telegram.txt\' file.")

# prepare token and key
token = str(token[0])

# create bot instance
bot = telebot.TeleBot(token)

# handle callback queries
@bot.callback_query_handler(func=lambda call: True)
def test_callback(call):
    globals()[str(call.data)](call.message)

# handle /start command
@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.InlineKeyboardMarkup()
    help_button = telebot.types.InlineKeyboardButton(text = "Lista komend 📃", callback_data = "help")
    markup.add(help_button)
    bot.send_message(message.chat.id, "Cześć, z tej strony Cezary924Bot! 🤖👋", reply_markup = markup)

# handle /tiktok command
@bot.message_handler(commands=['tiktok'])
def tiktok(message):
    bot.send_message(message.chat.id, "Aby pobrać wideo z serwisu TikTok wystarczy, że wyślesz mi do niego link 🎵")

# handle /twitter command
@bot.message_handler(commands=['twitter'])
def twitter(message):
    bot.send_message(message.chat.id, "Aby pobrać wideo z serwisu Twitter wystarczy, że wyślesz mi do niego link 🐦")


# handle /help command
@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id, "Oto lista dostępnych poleceń 📃:\n\n" + 
                     "/start - Zaczęcie rozmowy z botem 🤖\n" + 
                     "/help - Lista dostępnych komend 📃\n" +
                     "/about - Informacje o bocie ℹ️\n" +
                     "/tiktok - Pobieranie wideo z serwisu TikTok 🎵\n" +
                     "/twitter - Pobieranie wideo z serwisu Twitter 🐦")

# handle /about command
@bot.message_handler(commands=['about'])
def about(message):
    bot.send_message(message.chat.id, "*Cezary924Bot*\n"
                    + "Opis: _Wielofunkcyjny bot na platformie Telegram_\n"
                    + "Autor: _Cezary924_\n"
                    + "Rok powstania: _2023_\n"
                    + "Lata rozwijania: _2023-nadal_", parse_mode= 'Markdown')

# handle TikTok urls
@bot.message_handler(func=lambda message: tiktok.check_tiktok_url(message))
def echo_tiktok(message):
    if tiktok.rapidapi == None:
        tiktok.read_rapidapi()
    if tiktok.rapidapi != None:
        tiktok.echo_tiktok(message, bot)
    else:
        bot.send_message(message.chat.id, "Niestety, pobranie filmiku z TikToka nie jest teraz możliwe... Spróbuj poźniej 😞")

# handle Twitter urls
@bot.message_handler(func=lambda message: twitter.check_twitter_url(message))
def echo_twitter(message):
    if twitter.bearer_token == None:
        twitter.read_bearer_token()
    if twitter.bearer_token != None:
        twitter.echo_twitter(message, bot)
    else:
        bot.send_message(message.chat.id, "Niestety, pobranie filmiku z Twittera nie jest teraz możliwe... Spróbuj poźniej 😞")

# handle any other message
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.send_message(message.chat.id, "Niestety, nie rozumiem Twojej wiadomości... 💔")

# infinite loop
print("Cezary924-Telegram-Bot has been started.")
bot.infinity_polling()