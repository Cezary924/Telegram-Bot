import telebot, os

# get path of directory containing bot script
dir = os.path.dirname(os.path.realpath(__file__)) + "/"

# change current working directory to 'dir'
os.chdir(dir)

import basic_commands, database, tiktok, twitter

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

# create People table if it does not exist
database.create_table()

# send permission denied message
def permission_denied(message):
    markup = telebot.types.InlineKeyboardMarkup()
    contact_button = telebot.types.InlineKeyboardButton(text = "🧑‍🔬 Kontakt z administratorem", callback_data = "command_about")
    markup.add(contact_button)
    bot.send_message(message.chat.id, "Niestety, nie możesz skorzystać z tego polecenia... 😭\n\n"
                     + "Aby dostać wyższe uprawnienia skontaktuj się z administratorem 🧑‍🔬",
                     reply_markup=markup)

# handle callback queries
@bot.callback_query_handler(func=lambda call: True)
def test_callback(call):
    globals()[str(call.data)](call.message)

# handle /start command
@bot.message_handler(commands=['start'])
def command_start(message):
    database.guest_check(message)
    basic_commands.command_start(message, bot)

# handle /help command
@bot.message_handler(commands=['help'])
def command_help(message):
    database.guest_check(message)
    basic_commands.command_help(message, bot)

# handle /about command
@bot.message_handler(commands=['about'])
def command_about(message):
    database.guest_check(message)
    basic_commands.command_about(message, bot, ver)

# handle /tiktok command
@bot.message_handler(commands=['tiktok'])
def command_tiktok(message):
    database.guest_check(message)
    if database.user_check(message):
        basic_commands.command_tiktok(message, bot)
    else:
        permission_denied(message)

# handle /twitter command
@bot.message_handler(commands=['twitter'])
def command_twitter(message):
    database.guest_check(message)
    if database.user_check(message):
        basic_commands.command_twitter(message, bot)
    else:
        permission_denied(message)

# handle TikTok urls
@bot.message_handler(func=lambda message: tiktok.check_tiktok_url(message))
def echo_tiktok(message):
    database.guest_check(message)
    if database.user_check(message):
        tiktok.start_tiktok(message, bot)
    else:
        permission_denied(message)

# handle Twitter urls
@bot.message_handler(func=lambda message: twitter.check_twitter_url(message))
def echo_twitter(message):
    database.guest_check(message)
    if database.user_check(message):
        twitter.start_twitter(message, bot)
    else:
        permission_denied(message)

# handle any other message
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    database.guest_check(message)
    bot.send_message(message.chat.id, "Niestety, nie rozumiem Twojej wiadomości... 💔")

# infinite loop
print("Cezary924-Telegram-Bot has been started.")
bot.infinity_polling()