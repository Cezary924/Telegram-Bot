import telebot

with open("../secret.txt") as f:
    token = f.readlines()

token = str(token[0])

bot = telebot.TeleBot(token)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Cześć, z tej strony Cezary924Bot!")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
	bot.send_message(message.chat.id, "Niestety, nie rozumiem Twojej wiadomości...")

bot.infinity_polling()