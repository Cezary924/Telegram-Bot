import telebot

# opening the file containing the token and reading from it
with open("../secret.txt") as f:
    token = f.readlines()

# preparing the token
token = str(token[0])

# creating the bot instance
bot = telebot.TeleBot(token)

# handling /start command
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Cześć, z tej strony Cezary924Bot!")

# handling any other message
@bot.message_handler(func=lambda message: True)
def echo_all(message):
	bot.send_message(message.chat.id, "Niestety, nie rozumiem Twojej wiadomości...")

# infinite loop
bot.infinity_polling()
