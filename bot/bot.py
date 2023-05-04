import telebot, os

import basic_commands, tiktok, twitter

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

# open file containing version number and write/read to/from it
os.system('git rev-list --count master > ../version.txt')
try:
    with open("../version.txt") as f:
        ver = f.readlines()
    f.close()
except OSError:
    print("Open error: Could not open the \'version.txt\' file.")
os.remove('../version.txt')

# prepare version number
ver = str(ver[0])
ver = int(ver)

# create bot instance
bot = telebot.TeleBot(token)

# handle callback queries
@bot.callback_query_handler(func=lambda call: True)
def test_callback(call):
    globals()[str(call.data)](call.message)

# handle /start command
@bot.message_handler(commands=['start'])
def command_start(message):
    basic_commands.command_start(message, bot)

# handle /tiktok command
@bot.message_handler(commands=['tiktok'])
def command_tiktok(message):
    basic_commands.command_tiktok(message, bot)

# handle /twitter command
@bot.message_handler(commands=['twitter'])
def command_twitter(message):
    basic_commands.command_twitter(message, bot)

# handle /help command
@bot.message_handler(commands=['help'])
def command_help(message):
    basic_commands.command_help(message, bot)

# handle /about command
@bot.message_handler(commands=['about'])
def command_about(message):
    basic_commands.command_about(message, bot, ver)

# handle TikTok urls
@bot.message_handler(func=lambda message: tiktok.check_tiktok_url(message))
def echo_tiktok(message):
    tiktok.start_tiktok(message, bot)

# handle Twitter urls
@bot.message_handler(func=lambda message: twitter.check_twitter_url(message))
def echo_twitter(message):
    twitter.start_twitter(message, bot)

# handle any other message
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.send_message(message.chat.id, "Niestety, nie rozumiem Twojej wiadomości... 💔")

# infinite loop
print("Cezary924-Telegram-Bot has been started.")
bot.infinity_polling()