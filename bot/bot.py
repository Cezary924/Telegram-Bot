import telebot, os, TikTokApi

# get path of the directory containing the bot script
dir = os.path.dirname(os.path.realpath(__file__)) + "/"

# change current working directory to 'dir'
os.chdir(dir)

# open file containing the token and read from it
try:
    with open("../secret.txt") as f:
        token = f.readlines()
    f.close()
except OSError:
    print("Open error: Could not open the \'secret.txt\' file.")

# prepare token
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

# handle /help command
@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id, "Oto lista dostępnych poleceń 📃:\n\n" + 
                     "/start - Zaczęcie rozmowy z botem 🤖\n" + 
                     "/help - Lista dostępnych komend 📃")

# handle tik tok links
@bot.message_handler(func=lambda message: message.content_type == 'text' and 'vm.tiktok.com' in message.text)
def echo_tiktok(message):
    bot.send_message(message.chat.id, "Odebrano link z TikToka.")

# handle any other message
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.send_message(message.chat.id, "Niestety, nie rozumiem Twojej wiadomości... 💔")

# infinite loop
print("Cezary924-Telegram-Bot has been started.")
bot.infinity_polling()
