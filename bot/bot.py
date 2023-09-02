import telebot, os, sys, signal, time, subprocess
from threading import Thread

# get path of directory containing bot script
dir = os.path.dirname(os.path.realpath(__file__)) + "/"

# change current working directory to 'dir'
os.chdir(dir)

import func

# create LoadingString object & run its 'run' function in new thread
loading = func.LoadingString()
thread = Thread(target = loading.run, daemon = True)
thread.start()

# get Telegram token from tokens dict in func.py
if len(sys.argv) == 2 and sys.argv[1] == "beta":
    func.suffix = 1
    try:
        token = func.tokens['telegram_beta']
    except Exception as err:
        print('ERROR: No telegram_beta token in tokens.yaml!')
        sys.exit(1)
else:
    token = func.tokens['telegram']

import admin, basic_commands, database, logger
import crystal_ball, top_spotify_artist, reminder
import downloader, tiktok, twitter, tumblr, reddit, youtube, instagram

# get commit count & current tag name
commit_count = int(subprocess.check_output('git rev-list --count master').decode("utf-8").replace('\n', ''))
version_tag = subprocess.check_output('git describe --abbrev=0 --tags').decode("utf-8").replace('\n', '')

# create bot instance
bot = telebot.TeleBot(token)

# create People table if it does not exist
database.create_table_people()

# create State table if it does not exist
database.create_table_state()

# create Last_Bot_Message table if it does not exist
database.create_table_last_bot_message()

# create Language table if it does not exist
database.create_table_language()

# create Reminder table if it does not exist
database.create_table_reminder()

# send permission denied message
def permission_denied(message: telebot.types.Message) -> None:
    func.print_log("Permission denied: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'permission_denied_contact_button')
    contact_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_contact")
    markup.add(contact_button)
    text = database.get_message_text(message, 'permission_denied')
    mess = bot.send_message(message.chat.id, text, reply_markup=markup)
    database.register_last_message(mess)

# send banned info message
def banned_info(message: telebot.types.Message) -> None:
    func.print_log("Banned info: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    text = database.get_message_text(message, 'banned_info')
    mess = bot.send_message(message.chat.id, text)
    database.register_last_message(mess)

# send info about buttons not working anymore
def not_working_buttons(message: telebot.types.Message) -> None:
    text = database.get_message_text(message, 'not_working_buttons')
    mess = bot.send_message(message.chat.id, text)
    database.register_last_message(mess)

# handle callback queries
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call: telebot.types.CallbackQuery) -> None:
    func.print_log("Callback query: " + call.message.chat.first_name + " (" + str(call.message.chat.id) + ").")
    if database.banned_check(call.message) == True:
        banned_info(call.message)
        return
    if "command_dataprocessing_pl_yes" in str(call.data) or "command_dataprocessing_pl_no" in str(call.data) or "command_dataprocessing_en_yes" in str(call.data) or "command_dataprocessing_en_no" in str(call.data):
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.id, inline_message_id=call.inline_message_id, reply_markup=None)
    if str(call.data) in ['test', 'text']:
        return
    if str(call.data).split('_')[-1].isnumeric():
        database.set_current_state(call.message, str(call.data))
        call.data = str(call.data).replace('_' + str(call.data).split('_')[-1], '')
        globals()[str(call.data)](call.message)
        return
    globals()[str(call.data)](call.message)

# handle data processing check callback queries
def command_dataprocessing_pl(message: telebot.types.Message) -> None:
    func.print_log("/dataprocessing_pl: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.banned_check(message) == True:
        banned_info(message)
        return
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'command_dataprocessing_lang_switch', 'pl')
    en_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_dataprocessing_en")
    markup.add(en_button)
    text = database.get_message_text(message, 'command_dataprocessing_yes_button', 'pl')
    yes_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_dataprocessing_pl_yes")
    markup.add(yes_button)
    text = database.get_message_text(message, 'command_dataprocessing_no_button', 'pl')
    no_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_dataprocessing_pl_no")
    markup.add(no_button)
    text = database.get_message_text(message, 'command_dataprocessing', 'pl')
    bot.edit_message_text(text, message.chat.id, message.id, parse_mode = 'Markdown', reply_markup = markup)
def command_dataprocessing_en(message: telebot.types.Message) -> None:
    func.print_log("/dataprocessing_en: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.banned_check(message) == True:
        banned_info(message)
        return
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'command_dataprocessing_lang_switch', 'en')
    pl_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_dataprocessing_pl")
    markup.add(pl_button)
    text = database.get_message_text(message, 'command_dataprocessing_yes_button', 'en')
    yes_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_dataprocessing_en_yes")
    markup.add(yes_button)
    text = database.get_message_text(message, 'command_dataprocessing_no_button', 'en')
    no_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_dataprocessing_en_no")
    markup.add(no_button)
    text = database.get_message_text(message, 'command_dataprocessing', 'en')
    bot.edit_message_text(text, message.chat.id, message.id, parse_mode = 'Markdown', reply_markup = markup)
def command_dataprocessing_pl_yes(message: telebot.types.Message) -> None:
    func.print_log("/dataprocessing_pl_yes: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.guest_check(message, bot, 1)
    database.register_last_message(message, 1)
    database.set_user_language(message, 'pl')
    text = database.get_message_text(message, 'command_dataprocessing_yes', 'pl')
    bot.send_message(message.chat.id, text)
def command_dataprocessing_pl_no(message: telebot.types.Message) -> None:
    func.print_log("/dataprocessing_pl_no: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.banned_check(message) == True:
        banned_info(message)
        return
    text = database.get_message_text(message, 'command_dataprocessing_no', 'pl')
    bot.send_message(message.chat.id, text)
def command_dataprocessing_en_yes(message: telebot.types.Message) -> None:
    func.print_log("/dataprocessing_en_yes: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.guest_check(message, bot, 1)
    database.register_last_message(message, 1)
    database.set_user_language(message, 'en')
    text = database.get_message_text(message, 'command_dataprocessing_yes', 'en')
    bot.send_message(message.chat.id, text)
def command_dataprocessing_en_no(message: telebot.types.Message) -> None:
    func.print_log("/dataprocessing_en_no: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.banned_check(message) == True:
        banned_info(message)
        return
    text = database.get_message_text(message, 'command_dataprocessing_no', 'en')
    bot.send_message(message.chat.id, text)

# handle /admin command
@bot.message_handler(commands=['admin'])
def command_admin(message: telebot.types.Message) -> None:
    func.print_log("/admin: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "admin")
    if database.admin_check(message):
        admin.command_admin(message, bot)
    else:
        permission_denied(message)
def command_admin_users(message: telebot.types.Message) -> None:
    func.print_log("/admin_users: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "admin" == database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_users")
    if database.admin_check(message):
        admin.command_admin_users(message, bot)
    else:
        permission_denied(message)
def command_admin_bot(message: telebot.types.Message) -> None:
    func.print_log("/admin_bot: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "admin" == database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_bot")
    if database.admin_check(message):
        update = False
        if basic_commands.info_about_version(commit_count, message)[0] > commit_count:
            update = True
        admin.command_admin_bot(message, bot, update)
    else:
        permission_denied(message)
def command_admin_device(message: telebot.types.Message) -> None:
    func.print_log("/admin_device: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "admin" == database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_device")
    if database.admin_check(message):
        admin.command_admin_device(message, bot)
    else:
        permission_denied(message)
def command_admin_update_bot(message: telebot.types.Message) -> None:
    func.print_log("/admin_update_bot: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "admin" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_update_bot")
    admin.command_admin_update_bot(message, bot)
def command_admin_update_bot_yes(message: telebot.types.Message) -> None:
    func.print_log("/admin_update_bot_yes: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "admin_update_bot" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_update_bot_yes")
    admin.command_admin_update_bot_yes(message, bot)
def command_admin_shutdown_bot(message: telebot.types.Message) -> None:
    func.print_log("/admin_shutdown_bot: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "admin" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_shutdown_bot")
    admin.command_admin_shutdown_bot(message, bot)
def command_admin_shutdown_bot_yes(message: telebot.types.Message) -> None:
    func.print_log("/admin_shutdown_bot_yes: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "admin_shutdown_bot" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_shutdown_bot_yes")
    admin.command_admin_shutdown_bot_yes(message, bot)
def command_admin_shutdown_device(message: telebot.types.Message) -> None:
    func.print_log("/admin_shutdown_device: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "admin" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_shutdown_device")
    admin.command_admin_shutdown_device(message, bot)
def command_admin_shutdown_device_yes(message: telebot.types.Message) -> None:
    func.print_log("/admin_shutdown_device_yes: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "admin_shutdown_device" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_shutdown_device_yes")
    admin.command_admin_shutdown_device_yes(message, bot)
def command_admin_restart_bot(message: telebot.types.Message) -> None:
    func.print_log("/admin_restart_bot: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "admin" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_restart_bot")
    admin.command_admin_restart_bot(message, bot)
def command_admin_restart_bot_yes(message: telebot.types.Message) -> None:
    func.print_log("/admin_restart_bot_yes: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "admin_restart_bot" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_restart_bot_yes")
    admin.command_admin_restart_bot_yes(bot, message)
def command_admin_restart_device(message: telebot.types.Message) -> None:
    func.print_log("/admin_restart_device: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "admin" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_restart_device")
    admin.command_admin_restart_device(message, bot)
def command_admin_restart_device_yes(message: telebot.types.Message) -> None:
    func.print_log("/admin_restart_device_yes: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "admin_restart_device" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_restart_device_yes")
    admin.command_admin_restart_device_yes(message, bot)
def command_admin_return(message: telebot.types.Message) -> None:
    func.print_log("/admin_return: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "admin" == database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
        admin.command_admin_return(message, bot)
    elif database.get_current_state(message) in ['admin_users', 'admin_bot', 'admin_device']:
        basic_commands.delete_previous_bot_message(message, bot)
        command_admin(message)
    elif '_users' in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
        command_admin_users(message)
    elif '_bot' in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
        command_admin_bot(message)
    elif '_device' in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
        command_admin_device(message)
    else:
        not_working_buttons(message)

# handle /help command
@bot.message_handler(commands=['help'])
def command_help(message: telebot.types.Message) -> None:
    func.print_log("/help: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "help")
    basic_commands.command_help(message, bot)
def command_help_main(message: telebot.types.Message) -> None:
    func.print_log("/help_main: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "help" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "help_main")
    basic_commands.command_help_main(message, bot)
def command_help_features(message: telebot.types.Message) -> None:
    func.print_log("/help_features: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "help" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "help_features")
    basic_commands.command_help_features(message, bot)
def command_help_contact(message: telebot.types.Message) -> None:
    func.print_log("/help_contact: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "help" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "help_contact")
    basic_commands.command_help_contact(message, bot)
def command_help_settings(message: telebot.types.Message) -> None:
    func.print_log("/help_settings: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "help" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "help_settings")
    basic_commands.command_help_settings(message, bot)
def command_help_return(message: telebot.types.Message) -> None:
    func.print_log("/help_return: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "help" == database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
        basic_commands.command_help_return(message, bot)
    elif "help_" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
        command_help(message)
    else:
        not_working_buttons(message)

# handle /start command
@bot.message_handler(commands=['start'])
def command_start(message: telebot.types.Message) -> None:
    func.print_log("/start: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.banned_check(message) == True:
        banned_info(message)
        return
    basic_commands.command_start(message, bot)

# handle /features command
@bot.message_handler(commands=['features'])
def command_features(message: telebot.types.Message) -> None:
    func.print_log("/features: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    basic_commands.command_features(message, bot)

# handle /contact command
@bot.message_handler(commands=['contact'])
def command_contact(message: telebot.types.Message) -> None:
    func.print_log("/contact: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "contact")
    basic_commands.command_contact(message, bot)

# handle /report command
@bot.message_handler(commands=['report'])
def command_report(message: telebot.types.Message) -> None:
    func.print_log("/report: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "report")
    basic_commands.command_report(message, bot)

# handle /deletedata command
@bot.message_handler(commands=['deletedata'])
def command_deletedata(message: telebot.types.Message) -> None:
    func.print_log("/deletedata: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "deletedata")
    basic_commands.command_deletedata(message, bot)
def command_deletedata_yes(message: telebot.types.Message) -> None:
    func.print_log("/deletedata_yes: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if database.get_current_state(message) == "deletedata":
        basic_commands.delete_previous_bot_message(message, bot)
        basic_commands.command_deletedata_yes(message, bot)
    else:
        not_working_buttons(message)
def command_deletedata_no(message: telebot.types.Message) -> None:
    func.print_log("/deletedata_no: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if database.get_current_state(message) == "deletedata":
        basic_commands.delete_previous_bot_message(message, bot)
        database.set_current_state(message, "0")
        basic_commands.command_deletedata_no(message, bot)
    else:
        not_working_buttons(message)

# handle /language command
@bot.message_handler(commands=['language'])
def command_language(message: telebot.types.Message) -> None:
    func.print_log("/language: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "language")
    basic_commands.command_language(message, bot)
def command_language_pl(message: telebot.types.Message) -> None:
    func.print_log("/language_pl: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if database.get_current_state(message) == "language":
        basic_commands.delete_previous_bot_message(message, bot)
        basic_commands.command_language_pl(message, bot)
        database.set_current_state(message, "0")
    else:
        not_working_buttons(message)
def command_language_en(message: telebot.types.Message) -> None:
    func.print_log("/language_en: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if database.get_current_state(message) == "language":
        basic_commands.delete_previous_bot_message(message, bot)
        basic_commands.command_language_en(message, bot)
        database.set_current_state(message, "0")
    else:
        not_working_buttons(message)
def command_language_cancel(message: telebot.types.Message) -> None:
    func.print_log("/language_cancel: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if database.get_current_state(message) == "language":
        basic_commands.delete_previous_bot_message(message, bot)
        basic_commands.command_language_cancel(message, bot)
        database.set_current_state(message, "0")
    else:
        not_working_buttons(message)

# handle /about command
@bot.message_handler(commands=['about'])
def command_about(message: telebot.types.Message) -> None:
    func.print_log("/about: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "about")
    basic_commands.command_about(message, bot, commit_count, version_tag)

# handle /tiktok command
@bot.message_handler(commands=['tiktok'])
def command_tiktok(message: telebot.types.Message) -> None:
    func.print_log("/tiktok: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "tiktok")
    if database.user_check(message):
        basic_commands.command_tiktok(message, bot)
    else:
        permission_denied(message)

# handle /twitter command
@bot.message_handler(commands=['twitter'])
def command_twitter(message: telebot.types.Message) -> None:
    func.print_log("/twitter: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "twitter")
    if database.user_check(message):
        basic_commands.command_twitter(message, bot)
    else:
        permission_denied(message)

# handle /reddit command
@bot.message_handler(commands=['reddit'])
def command_reddit(message: telebot.types.Message) -> None:
    func.print_log("/reddit: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "reddit")
    if database.user_check(message):
        basic_commands.command_reddit(message, bot)
    else:
        permission_denied(message)

# handle /tumblr command
@bot.message_handler(commands=['tumblr'])
def command_tumblr(message: telebot.types.Message) -> None:
    func.print_log("/tumblr: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "tumblr")
    if database.user_check(message):
        basic_commands.command_tumblr(message, bot)
    else:
        permission_denied(message)

# handle /youtube command
@bot.message_handler(commands=['youtube'])
def command_youtube(message: telebot.types.Message) -> None:
    func.print_log("/youtube: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "youtube")
    if database.user_check(message):
        basic_commands.command_youtube(message, bot)
    else:
        permission_denied(message)

# handle /instagram command
@bot.message_handler(commands=['instagram'])
def command_instagram(message: telebot.types.Message) -> None:
    func.print_log("/instagram: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "instagram")
    if database.user_check(message):
        basic_commands.command_instagram(message, bot)
    else:
        permission_denied(message)

# handle TikTok URLs
@bot.message_handler(func=lambda message: downloader.check_url(message, ['https'], ['vm.tiktok.com', 'www.tiktok.com']))
def echo_tiktok(message: telebot.types.Message) -> None:
    func.print_log("TikTok URL: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "tiktok_url")
    if database.user_check(message):
        tiktok.start_tiktok(message, bot)
    else:
        permission_denied(message)

# handle Twitter URLs
@bot.message_handler(func=lambda message: downloader.check_url(message, ['https'], ['twitter.com', 'x.com']))
def echo_twitter(message: telebot.types.Message) -> None:
    func.print_log("Twitter URL: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "twitter_url")
    if database.user_check(message):
        twitter.start_twitter(message, bot)
    else:
        permission_denied(message)

# handle Reddit URLs
@bot.message_handler(func=lambda message: downloader.check_url(message, ['https'], ['www.reddit.com']))
def echo_reddit(message: telebot.types.Message) -> None:
    func.print_log("Reddit URL: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "reddit_url")
    if database.user_check(message):
        reddit.start_reddit(message, bot)
    else:
        permission_denied(message)

# handle Tumblr URLs
@bot.message_handler(func=lambda message: downloader.check_url(message, ['https'], ['www.tumblr.com']))
def echo_tumblr(message: telebot.types.Message) -> None:
    func.print_log("Tumblr URL: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "tumblr_url")
    if database.user_check(message):
        tumblr.start_tumblr(message, bot)
    else:
        permission_denied(message)

# handle YouTube URLs
@bot.message_handler(func=lambda message: downloader.check_url(message, ['https'], ['youtube.com', 'youtu.be']))
def echo_youtube(message: telebot.types.Message) -> None:
    func.print_log("YouTube URL: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "youtube_url")
    if database.user_check(message):
        youtube.start_youtube(message, bot)
    else:
        permission_denied(message)

# handle Instagram URLs
@bot.message_handler(func=lambda message: downloader.check_url(message, ['https'], ['www.instagram.com', 'instagram.com']))
def echo_instagram(message: telebot.types.Message) -> None:
    func.print_log("Instagram URL: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "instagram_url")
    if database.user_check(message):
        instagram.start_instagram(message, bot)
    else:
        permission_denied(message)

# handle /crystalball command
@bot.message_handler(commands=['crystalball'])
def command_crystalball(message: telebot.types.Message) -> None:
    func.print_log("/crystalball: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "crystalball")
    crystal_ball.command_crystalball(message, bot)

# handle /topspotifyartist command
@bot.message_handler(commands=['topspotifyartist'])
def command_topspotifyartist(message: telebot.types.Message) -> None:
    func.print_log("/topspotifyartist: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "topspotifyartist")
    top_spotify_artist.command_topspotifyartist(message, bot)

# handle /reminder command
@bot.message_handler(commands=['reminder'])
def command_reminder(message: telebot.types.Message) -> None:
    func.print_log("/reminder: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "reminder")
    if database.user_check(message):
        reminder.command_reminder(message, bot)
    else:
        permission_denied(message)
def command_reminder_set(message: telebot.types.Message) -> None:
    func.print_log("/reminder_set: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "reminder" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "reminder_set")
    reminder.command_reminder_set(message, bot)
def command_reminder_manage(message: telebot.types.Message) -> None:
    func.print_log("/reminder_manage: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "reminder" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "reminder_manage")
    reminder.command_reminder_manage(message, bot)
def command_reminder_return(message: telebot.types.Message) -> None:
    func.print_log("/reminder_return: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "reminder_manage_menu" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
        number, reminders = database.get_reminders(message)
        if number == 0:
            command_reminder(message)
            return
        reminder.command_reminder_manage(message, bot)
    elif "reminder_" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
        command_reminder(message)
    elif "reminder" == database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
        reminder.command_reminder_return(message, bot)
    else:
        not_working_buttons(message)

# start topspotifyartist loop
def topspotifyartist(message: telebot.types.Message) -> None:
    func.print_log("Top Spotify artist: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if "_topspotifyartist" in database.get_current_state(message):
        top_spotify_artist.topspotifyartist(message, bot)
    else:
        not_working_buttons(message)

# handle messages to admin
@bot.message_handler(func=lambda message: database.get_current_state(message) == "report")
def forward_message_to_admin(message: telebot.types.Message) -> None:
    func.print_log("Report to admin: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.forward_message_to_admin(message, bot)

# handle topspotifyartist messages
@bot.message_handler(func=lambda message: "topspotifyartist_" in database.get_current_state(message))
def echo_topspotifyartist(message: telebot.types.Message) -> None:
    func.print_log("Top Spotify artist guess: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    top_spotify_artist.topspotifyartist(message, bot)

# handle reminder_edit_date messages
@bot.message_handler(func=lambda message: "reminder_manage_menu_edit_date_" in database.get_current_state(message))
def command_reminder_manage_menu_edit_date(message: telebot.types.Message) -> None:
    func.print_log("Reminder editing: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if len(database.get_current_state(message).split('_')) <= 7:
        basic_commands.delete_previous_bot_message(message, bot)
    reminder.command_reminder_set_date(message, bot)

# handle reminder_edit_content messages
@bot.message_handler(func=lambda message: "reminder_manage_menu_edit_content_" in database.get_current_state(message))
def command_reminder_manage_menu_edit_content(message: telebot.types.Message) -> None:
    func.print_log("Reminder editing: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    if len(database.get_current_state(message).split('_')) <= 7:
        basic_commands.delete_previous_bot_message(message, bot)
    reminder.command_reminder_set(message, bot)

# handle reminder_delete messages
@bot.message_handler(func=lambda message: "reminder_manage_menu_delete_" in database.get_current_state(message))
def command_reminder_manage_menu_delete(message: telebot.types.Message) -> None:
    func.print_log("Reminder deleting: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    basic_commands.delete_previous_bot_message(message, bot)
    reminder.command_reminder_manage_menu_delete(message, bot)
def command_reminder_manage_menu_delete_yes(message: telebot.types.Message) -> None:
    func.print_log("Reminder deleting: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    basic_commands.delete_previous_bot_message(message, bot)
    reminder.command_reminder_manage_menu_delete_yes(message, bot)

# handle command_reminder_manage_menu messages
@bot.message_handler(func=lambda message: "reminder_manage_menu_" in database.get_current_state(message))
def echo_reminder_manage_menu(message: telebot.types.Message) -> None:
    func.print_log("Reminder managing: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    basic_commands.delete_previous_bot_message(message, bot)
    reminder.command_reminder_manage_menu(message, bot)

# handle reminder_set_date messages
@bot.message_handler(func=lambda message: "reminder_set_" in database.get_current_state(message))
def echo_reminder_set_date(message: telebot.types.Message) -> None:
    func.print_log("Reminder setting: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    reminder.command_reminder_set_date(message, bot)

# handle reminder_set messages
@bot.message_handler(func=lambda message: "reminder_set" in database.get_current_state(message))
def echo_reminder_set(message: telebot.types.Message) -> None:
    func.print_log("Reminder setting: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    reminder.command_reminder_set_date(message, bot)

# handle unknown command
@bot.message_handler(func=lambda message: message.text.startswith("/"))
def echo_unknown_command(message: telebot.types.Message) -> None:
    func.print_log("Unknown command: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "0")
    text = database.get_message_text(message, 'echo_unknown_command')
    mess = bot.send_message(message.chat.id, text)
    database.register_last_message(mess)

# handle any other message
@bot.message_handler(func=lambda message: True)
def echo_all(message: telebot.types.Message) -> None:
    func.print_log("Misunderstood message: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.banned_check(message) == True:
        banned_info(message)
        return
    database.set_current_state(message, "0")
    text = database.get_message_text(message, 'echo_all')
    mess = bot.send_message(message.chat.id, text)
    database.register_last_message(mess)

# handle CTRL + C
def ctrl_c(signal, frame) -> None:
    database.send_stop_info(bot)
    time.sleep(1)
    func.print_log("", basic_commands.bot_name, 0)
    bot.stop_polling()
    database.commit_close()
    sys.exit(0)
signal.signal(signal.SIGINT, ctrl_c)

# fill artists list
top_spotify_artist.fill_artists()

# stop LoadingString object loop
loading.stop()
time.sleep(1)

# write stdout to both console and file
sys.stdout = logger.Logger()

# starting log message
func.print_log("", basic_commands.bot_name, 1)

# execute func sending info about restart
database.send_start_info(bot)

# create new thread for reminders checker
thread = Thread(target = reminder.check_reminders, args = (bot, ), daemon = True)
thread.start()

# infinite loop
if func.suffix == 0:
    try:
        bot.polling(non_stop = True, timeout = 60)
    except KeyboardInterrupt as keyint:
        sys.exit()
    except Exception as err:
        func.print_log('ERROR: Telebot error.')
        print(err)
        database.send_error_info(bot, str(type(err).__name__))
        database.set_admins_state(bot, 'err_' + str(type(err).__name__))
        sys.exit()
        #admin.command_admin_restart_bot_yes(bot, send_mess = 0)
else:
    bot.polling(non_stop = True)