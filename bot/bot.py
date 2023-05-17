import telebot, os, sys, signal

# get path of directory containing bot script
dir = os.path.dirname(os.path.realpath(__file__)) + "/"

# change current working directory to 'dir'
os.chdir(dir)

# write stdout & stdeer to files
sys.stdout = open('../stdout.txt', 'w')
sys.stderr = open('../stderr.txt', 'w')

import func

# open file containing Telegram token and read from it
if len(sys.argv) == 2 and sys.argv[1] == "beta":
    func.suffix = 1
    token = func.read_file("telegram-beta.txt", "../files/telegram-beta.txt")
    token = str(token[0])
else:
    token = func.read_file("telegram.txt", "../files/telegram.txt")
    token = str(token[0])

import basic_commands, database, tiktok, twitter

# open file containing version number and write/read to/from it
os.system('git rev-list --count master > ../version.txt')
ver = func.read_file("version.txt", "../version.txt")
os.remove('../version.txt')
ver = str(ver[0])
ver = int(ver)

# create bot instance
bot = telebot.TeleBot(token)

# create People table if it does not exist
database.create_table_people()

# create People table if it does not exist
database.create_table_state()

# send permission denied message
def permission_denied(message):
    func.print_log("Permission denied: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    markup = telebot.types.InlineKeyboardMarkup()
    contact_button = telebot.types.InlineKeyboardButton(text = "🧑‍🔬 Kontakt z administratorem", callback_data = "command_contact")
    markup.add(contact_button)
    bot.send_message(message.chat.id, "Niestety, nie możesz skorzystać z tego polecenia... 😭\n\n"
                     + "Aby dostać wyższe uprawnienia skontaktuj się z administratorem 🧑‍🔬",
                     reply_markup=markup)

# send info about buttons not working anymore
def not_working_buttons(message):
    bot.send_message(message.chat.id, "Niestety, ten przycisk już nie działa... 😥")

# handle callback queries
@bot.callback_query_handler(func=lambda call: True)
def test_callback(call):
    func.print_log("Callback query: " + call.message.chat.first_name + " (" + str(call.message.chat.id) + ").")
    globals()[str(call.data)](call.message)

# handle /start command
@bot.message_handler(commands=['start'])
def command_start(message):
    func.print_log("/start: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    database.guest_check(message)
    database.save_current_state(message, "start")
    basic_commands.command_start(message, bot)

# handle /help command
@bot.message_handler(commands=['help'])
def command_help(message):
    func.print_log("/help: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    database.guest_check(message)
    database.save_current_state(message, "help")
    basic_commands.command_help(message, bot)

# handle /contact command
@bot.message_handler(commands=['contact'])
def command_contact(message):
    func.print_log("/contact: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    database.guest_check(message)
    database.save_current_state(message, "contact")
    basic_commands.command_contact(message, bot)

# handle /report command
@bot.message_handler(commands=['report'])
def command_report(message):
    func.print_log("/report: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    database.guest_check(message)
    database.save_current_state(message, "report")
    basic_commands.command_report(message, bot)

# handle /delete_data command
@bot.message_handler(commands=['delete_data'])
def command_delete_data(message):
    func.print_log("/delete-data: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    database.guest_check(message)
    database.save_current_state(message, "delete_data")
    basic_commands.command_delete_data(message, bot)
def command_delete_data_yes(message):
    if database.get_current_state(message) == "delete_data":
        database.delete_data(message)
        basic_commands.command_delete_data_yes(message, bot)
    else:
        not_working_buttons(message)
def command_delete_data_no(message):
    if database.get_current_state(message) == "delete_data":
        database.save_current_state(message, "0")
        basic_commands.command_delete_data_no(message, bot)
    else:
        not_working_buttons(message)

# handle /about command
@bot.message_handler(commands=['about'])
def command_about(message):
    func.print_log("/about: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    database.guest_check(message)
    database.save_current_state(message, "about")
    basic_commands.command_about(message, bot, ver)

# handle /tiktok command
@bot.message_handler(commands=['tiktok'])
def command_tiktok(message):
    func.print_log("/tiktok: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    database.guest_check(message)
    database.save_current_state(message, "tiktok")
    if database.user_check(message):
        basic_commands.command_tiktok(message, bot)
    else:
        permission_denied(message)

# handle /twitter command
@bot.message_handler(commands=['twitter'])
def command_twitter(message):
    func.print_log("/twitter: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    database.guest_check(message)
    database.save_current_state(message, "twitter")
    if database.user_check(message):
        basic_commands.command_twitter(message, bot)
    else:
        permission_denied(message)

# handle TikTok urls
@bot.message_handler(func=lambda message: tiktok.check_tiktok_url(message))
def echo_tiktok(message):
    func.print_log("TikTok URL: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    database.guest_check(message)
    database.save_current_state(message, "tiktok-url")
    if database.user_check(message):
        tiktok.start_tiktok(message, bot)
    else:
        permission_denied(message)

# handle Twitter urls
@bot.message_handler(func=lambda message: twitter.check_twitter_url(message))
def echo_twitter(message):
    func.print_log("Twitter URL: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    database.guest_check(message)
    database.save_current_state(message, "twitter-url")
    if database.user_check(message):
        twitter.start_twitter(message, bot)
    else:
        permission_denied(message)

# handle messages to admin
@bot.message_handler(func=lambda message: database.get_current_state(message) == "report")
def forward_message_to_admin(message):
    func.print_log("Report to admin: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    database.forward_message_to_admin(message, bot)

# handle any other message
@bot.message_handler(func=lambda message: message.text.startswith("/"))
def echo_unknown_command(message):
    func.print_log("Unknown command: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    database.guest_check(message)
    database.save_current_state(message, "0")
    bot.send_message(message.chat.id, "Niestety, nie znam takiej komendy... 💔")

# handle any other message
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    func.print_log("Misunderstood message: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    database.guest_check(message)
    database.save_current_state(message, "0")
    bot.send_message(message.chat.id, "Niestety, nie rozumiem Twojej wiadomości... 💔")

# handle CTRL + C
def ctrl_c(signal, frame):
    func.print_log("", basic_commands.bot_name, 0)
    bot.stop_polling()
    os.remove('../stdout.txt')
    os.remove('../stderr.txt')
    sys.exit(0)
signal.signal(signal.SIGINT, ctrl_c)

# infinite loop
func.print_log("", basic_commands.bot_name, 1)
bot.polling(non_stop = True)