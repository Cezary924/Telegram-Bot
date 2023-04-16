import telebot

# open file containing the token and read from it
try:
    with open("../secret.txt") as f:
        token = f.readlines()
    f.close()
except OSError:
    print("Could not open the file.")

# prepare token
token = str(token[0])

# create bot instance
bot = telebot.TeleBot(token)

# handle /start command
@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.InlineKeyboardMarkup()
    help_button = telebot.types.InlineKeyboardButton(text = "Lista komend", callback_data = "help")
    markup.add(help_button)
    bot.send_message(message.chat.id, "Cześć, z tej strony Cezary924Bot!", reply_markup = markup)

# handle /help command
@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id, "Oto lista dostępnych poleceń:\n\n" + 
                     "/start - Zaczęcie rozmowy z botem\n" + 
                     "/help - Lista dostępnych komend")

# handle any other message
@bot.message_handler(func=lambda message: True)
def echo_all(message):
	bot.send_message(message.chat.id, "Niestety, nie rozumiem Twojej wiadomości...")

# infinite loop
bot.infinity_polling()
