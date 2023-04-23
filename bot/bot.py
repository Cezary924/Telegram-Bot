import telebot, os
import tiktok

# get path of directory containing bot script
dir = os.path.dirname(os.path.realpath(__file__)) + "/"

# change current working directory to 'dir'
os.chdir(dir)

# open file containing token and read from it
try:
    with open("../secret.txt") as f:
        token = f.readlines()
    f.close()
except OSError:
    print("Open error: Could not open the \'secret.txt\' file.")

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
def help(message):
    bot.send_message(message.chat.id, "Aby pobrać wideo z serwisu TikTok wystarczy, że wyślesz mi do niego link 🎵")

# handle /help command
@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id, "Oto lista dostępnych poleceń 📃:\n\n" + 
                     "/start - Zaczęcie rozmowy z botem 🤖\n" + 
                     "/help - Lista dostępnych komend 📃\n" +
                     "/tiktok - Pobieranie wideo z serwisu TikTok 🎵")

# handle TikTok urls
@bot.message_handler(func=lambda message: message.content_type == 'text' and 'tiktok.com' in message.text and 'http' in message.text)
def echo_tiktok(message):
    if tiktok.rapidapi == None:
        tiktok.read_rapidapi()
    if tiktok.rapidapi != None:
        tiktok.echo_tiktok(message, bot)
    else:
        bot.send_message(message.chat.id, "Niestety, pobranie filmiku z TikToka nie jest teraz możliwe... Spróbuj poźniej 😞")

# handle any other message
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.send_message(message.chat.id, "Niestety, nie rozumiem Twojej wiadomości... 💔")

# infinite loop
print("Cezary924-Telegram-Bot has been started.")
bot.infinity_polling()