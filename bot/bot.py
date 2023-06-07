import telebot, os, sys, signal

# get path of directory containing bot script
dir = os.path.dirname(os.path.realpath(__file__)) + "/"

# change current working directory to 'dir'
os.chdir(dir)

import func, logger

# write stdout & stdeer to file only
# sys.stdout = func.write_file('stdout.txt', '../stdout.txt', 1)
# sys.stderr = func.write_file('stderr.txt', '../stderr.txt', 1)

# write stdout & stdeer to both console and file
sys.stdout = logger.LoggerStdout()
sys.stderr = logger.LoggerStderr()

# open file containing Telegram token and read from it
if len(sys.argv) == 2 and sys.argv[1] == "beta":
    func.suffix = 1
    token = func.read_file("telegram-beta.txt", "../files/telegram-beta.txt")
    token = str(token[0])
else:
    token = func.read_file("telegram.txt", "../files/telegram.txt")
    token = str(token[0])

import admin, basic_commands, database, tiktok, twitter

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

# create State table if it does not exist
database.create_table_state()

# create Last_Bot_Message table if it does not exist
database.create_table_last_bot_message()

# send permission denied message
def permission_denied(message):
    func.print_log("Permission denied: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    markup = telebot.types.InlineKeyboardMarkup()
    contact_button = telebot.types.InlineKeyboardButton(text = "🧑‍🔬 Kontakt z administratorem", callback_data = "command_contact")
    markup.add(contact_button)
    mess = bot.send_message(message.chat.id, "Niestety, nie możesz skorzystać z tego polecenia... 😭\n\n"
                     + "Aby dostać wyższe uprawnienia skontaktuj się z administratorem 🧑‍🔬",
                     reply_markup=markup)
    database.register_last_message(mess)

# send info about buttons not working anymore
def not_working_buttons(message):
    mess = bot.send_message(message.chat.id, "Niestety, ten przycisk już nie działa... 😥")
    database.register_last_message(mess)

# handle callback queries
@bot.callback_query_handler(func=lambda call: True)
def test_callback(call):
    func.print_log("Callback query: " + call.message.chat.first_name + " (" + str(call.message.chat.id) + ").")
    if "command_dataprocessing_" in str(call.data):
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.id, inline_message_id=call.inline_message_id, reply_markup=None)
    globals()[str(call.data)](call.message)

# handle data processing check callback queries
def command_dataprocessing_yes(message):
    bot.send_message(message.chat.id, "Cieszę się, że to nie koniec naszej wspólnej przygody 💞 \n"
                     + "Od teraz mogę wykonywać Twoje polecenia 🫡")
    database.register_last_message(message, 1)
def command_dataprocessing_no(message):
    bot.send_message(message.chat.id, "Dobrze, rozumiem 😞 \n"
                     + "Miło mi było Cię poznać 😄")

# handle /admin command
@bot.message_handler(commands=['admin'])
def command_admin(message):
    func.print_log("/admin: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.save_current_state(message, "admin")
    if database.admin_check(message):
        update = False
        if basic_commands.info_about_version(ver)[0] > ver:
            update = True
        admin.command_admin(message, bot, update)
    else:
        permission_denied(message)
def command_admin_update_bot(message):
    func.print_log("/admin_update_bot: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "admin" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.save_current_state(message, "admin_update_bot")
    admin.command_admin_update_bot(message, bot)
def command_admin_update_bot_yes(message):
    func.print_log("/admin_update_bot_yes: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "admin_update_bot" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.save_current_state(message, "admin_update_bot_yes")
    admin.command_admin_update_bot_yes(message, bot)
def command_admin_shutdown_bot(message):
    func.print_log("/admin_shutdown_bot: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "admin" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.save_current_state(message, "admin_shutdown_bot")
    admin.command_admin_shutdown_bot(message, bot)
def command_admin_shutdown_bot_yes(message):
    func.print_log("/admin_shutdown_bot_yes: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "admin_shutdown_bot" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.save_current_state(message, "admin_shutdown_bot_yes")
    admin.command_admin_shutdown_bot_yes(message, bot)
def command_admin_shutdown_device(message):
    func.print_log("/admin_shutdown_device: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "admin" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.save_current_state(message, "admin_shutdown_device")
    admin.command_admin_shutdown_device(message, bot)
def command_admin_shutdown_device_yes(message):
    func.print_log("/admin_shutdown_device_yes: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "admin_shutdown_device" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.save_current_state(message, "admin_shutdown_device_yes")
    admin.command_admin_shutdown_device_yes(message, bot)
def command_admin_restart_bot(message):
    func.print_log("/admin_restart_bot: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "admin" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.save_current_state(message, "admin_restart_bot")
    admin.command_admin_restart_bot(message, bot)
def command_admin_restart_bot_yes(message):
    func.print_log("/admin_restart_bot_yes: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "admin_restart_bot" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.save_current_state(message, "admin_restart_bot_yes")
    admin.command_admin_restart_bot_yes(message, bot)
def command_admin_restart_device(message):
    func.print_log("/admin_restart_device: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "admin" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.save_current_state(message, "admin_restart_device")
    admin.command_admin_restart_device(message, bot)
def command_admin_restart_device_yes(message):
    func.print_log("/admin_restart_device_yes: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "admin_restart_device" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.save_current_state(message, "admin_restart_device_yes")
    admin.command_admin_restart_device_yes(message, bot)
def command_admin_return(message):
    if "admin" == database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
        mess = bot.send_message(message.chat.id, "🛠️ *Panel Administratora:*\n\nOpuszczono panel _/admin_ ❌", parse_mode='Markdown')
        database.register_last_message(mess)
    elif "admin_" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
        command_admin(message)
    else:
        not_working_buttons(message)

# handle /help command
@bot.message_handler(commands=['help'])
def command_help(message):
    func.print_log("/help: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.save_current_state(message, "help")
    basic_commands.command_help(message, bot)
def command_help_main(message):
    func.print_log("/help_main: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "help" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.save_current_state(message, "help_main")
    basic_commands.command_help_main(message, bot)
def command_help_downloader(message):
    func.print_log("/help_downloader: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "help" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.save_current_state(message, "help_downloader")
    basic_commands.command_help_downloader(message, bot)
def command_help_contact(message):
    func.print_log("/help_contact: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "help" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.save_current_state(message, "help_contact")
    basic_commands.command_help_contact(message, bot)
def command_help_settings(message):
    func.print_log("/help_settings: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "help" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.save_current_state(message, "help_settings")
    basic_commands.command_help_settings(message, bot)
def command_help_return(message):
    if "help" == database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
        mess = bot.send_message(message.chat.id, "📃 *Pomoc:*\n\nOpuszczono menu _/help_ ❌", parse_mode='Markdown')
        database.register_last_message(mess)
    elif "help_" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
        command_help(message)
    else:
        not_working_buttons(message)

# handle /start command
@bot.message_handler(commands=['start'])
def command_start(message):
    func.print_log("/start: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    basic_commands.command_start(message, bot)

# handle /contact command
@bot.message_handler(commands=['contact'])
def command_contact(message):
    func.print_log("/contact: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.save_current_state(message, "contact")
    basic_commands.command_contact(message, bot)

# handle /report command
@bot.message_handler(commands=['report'])
def command_report(message):
    func.print_log("/report: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.save_current_state(message, "report")
    basic_commands.command_report(message, bot)

# handle /deletedata command
@bot.message_handler(commands=['deletedata'])
def command_deletedata(message):
    func.print_log("/deletedata: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.save_current_state(message, "deletedata")
    basic_commands.command_deletedata(message, bot)
def command_deletedata_yes(message):
    if database.get_current_state(message) == "deletedata":
        database.deletedata(message)
        basic_commands.command_deletedata_yes(message, bot)
    else:
        not_working_buttons(message)
def command_deletedata_no(message):
    if database.get_current_state(message) == "deletedata":
        database.save_current_state(message, "0")
        basic_commands.command_deletedata_no(message, bot)
    else:
        not_working_buttons(message)

# handle /about command
@bot.message_handler(commands=['about'])
def command_about(message):
    func.print_log("/about: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.save_current_state(message, "about")
    basic_commands.command_about(message, bot, ver)

# handle /tiktok command
@bot.message_handler(commands=['tiktok'])
def command_tiktok(message):
    func.print_log("/tiktok: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.save_current_state(message, "tiktok")
    if database.user_check(message):
        basic_commands.command_tiktok(message, bot)
    else:
        permission_denied(message)

# handle /twitter command
@bot.message_handler(commands=['twitter'])
def command_twitter(message):
    func.print_log("/twitter: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.save_current_state(message, "twitter")
    if database.user_check(message):
        basic_commands.command_twitter(message, bot)
    else:
        permission_denied(message)

# handle TikTok urls
@bot.message_handler(func=lambda message: tiktok.check_tiktok_url(message))
def echo_tiktok(message):
    func.print_log("TikTok URL: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.save_current_state(message, "tiktok_url")
    if database.user_check(message):
        tiktok.start_tiktok(message, bot)
    else:
        permission_denied(message)

# handle Twitter urls
@bot.message_handler(func=lambda message: twitter.check_twitter_url(message))
def echo_twitter(message):
    func.print_log("Twitter URL: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.save_current_state(message, "twitter_url")
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
    if database.guest_check(message, bot) != True:
        return
    database.save_current_state(message, "0")
    mess = bot.send_message(message.chat.id, "Niestety, nie znam takiej komendy... 💔")
    database.register_last_message(mess)

# handle any other message
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    func.print_log("Misunderstood message: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.save_current_state(message, "0")
    mess = bot.send_message(message.chat.id, "Niestety, nie rozumiem Twojej wiadomości... 💔")
    database.register_last_message(mess)

# handle CTRL + C
def ctrl_c(signal, frame):
    func.print_log("", basic_commands.bot_name, 0)
    bot.stop_polling()
    database.commit_close()
    sys.exit(0)
signal.signal(signal.SIGINT, ctrl_c)

# infinite loop
func.print_log("", basic_commands.bot_name, 1)
bot.polling(non_stop = True)