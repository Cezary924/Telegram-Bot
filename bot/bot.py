import telebot, os, sys, signal, time

# get path of directory containing bot script
dir = os.path.dirname(os.path.realpath(__file__)) + "/"

# change current working directory to 'dir'
os.chdir(dir)

import func, logger

# write stdout & stdeer to both console and file
sys.stdout = logger.LoggerStdout()
sys.stderr = logger.LoggerStderr()

# get Telegram token from tokens dict in func.py
if len(sys.argv) == 2 and sys.argv[1] == "beta":
    func.suffix = 1
    token = func.tokens['telegram_beta']
else:
    token = func.tokens['telegram']

import admin, basic_commands, database, crystal_ball, top_spotify_artist
import downloader, tiktok, twitter, tumblr, reddit, youtube

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

# create Language table if it does not exist
database.create_table_language()

# send permission denied message
def permission_denied(message):
    func.print_log("Permission denied: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'permission_denied_contact_button')
    contact_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_contact")
    markup.add(contact_button)
    text = database.get_message_text(message, 'permission_denied')
    mess = bot.send_message(message.chat.id, text, reply_markup=markup)
    database.register_last_message(mess)

# send info about buttons not working anymore
def not_working_buttons(message):
    text = database.get_message_text(message, 'not_working_buttons')
    mess = bot.send_message(message.chat.id, text)
    database.register_last_message(mess)

# handle callback queries
@bot.callback_query_handler(func=lambda call: True)
def test_callback(call):
    func.print_log("Callback query: " + call.message.chat.first_name + " (" + str(call.message.chat.id) + ").")
    if "command_dataprocessing_pl_yes" in str(call.data) or "command_dataprocessing_pl_no" in str(call.data) or "command_dataprocessing_en_yes" in str(call.data) or "command_dataprocessing_en_no" in str(call.data):
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.id, inline_message_id=call.inline_message_id, reply_markup=None)
    globals()[str(call.data)](call.message)

# handle data processing check callback queries
def command_dataprocessing_pl(message):
    func.print_log("/dataprocessing_pl: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
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
def command_dataprocessing_en(message):
    func.print_log("/dataprocessing_en: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
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
def command_dataprocessing_pl_yes(message):
    func.print_log("/dataprocessing_pl_yes: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    database.guest_check(message, bot, 1)
    database.register_last_message(message, 1)
    database.set_user_language(message, 'pl')
    text = database.get_message_text(message, 'command_dataprocessing_yes', 'pl')
    bot.send_message(message.chat.id, text)
def command_dataprocessing_pl_no(message):
    func.print_log("/dataprocessing_pl_no: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    text = database.get_message_text(message, 'command_dataprocessing_no', 'pl')
    bot.send_message(message.chat.id, text)
def command_dataprocessing_en_yes(message):
    func.print_log("/dataprocessing_en_yes: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    database.guest_check(message, bot, 1)
    database.register_last_message(message, 1)
    database.set_user_language(message, 'en')
    text = database.get_message_text(message, 'command_dataprocessing_yes', 'en')
    bot.send_message(message.chat.id, text)
def command_dataprocessing_en_no(message):
    func.print_log("/dataprocessing_en_no: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    text = database.get_message_text(message, 'command_dataprocessing_no', 'en')
    bot.send_message(message.chat.id, text)

# handle /admin command
@bot.message_handler(commands=['admin'])
def command_admin(message):
    func.print_log("/admin: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.set_current_state(message, "admin")
    if database.admin_check(message):
        update = False
        if basic_commands.info_about_version(ver)[0] > ver:
            update = True
        admin.command_admin(message, bot, update)
    else:
        permission_denied(message)
@bot.message_handler(commands=['admin_update_bot'])
def command_admin_update_bot(message):
    func.print_log("/admin_update_bot: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "admin" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_update_bot")
    admin.command_admin_update_bot(message, bot)
@bot.message_handler(commands=['admin_update_bot_yes'])
def command_admin_update_bot_yes(message):
    func.print_log("/admin_update_bot_yes: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "admin_update_bot" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_update_bot_yes")
    admin.command_admin_update_bot_yes(message, bot)
@bot.message_handler(commands=['admin_shutdown_bot'])
def command_admin_shutdown_bot(message):
    func.print_log("/admin_shutdown_bot: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "admin" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_shutdown_bot")
    admin.command_admin_shutdown_bot(message, bot)
@bot.message_handler(commands=['admin_shutdown_bot_yes'])
def command_admin_shutdown_bot_yes(message):
    func.print_log("/admin_shutdown_bot_yes: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "admin_shutdown_bot" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_shutdown_bot_yes")
    admin.command_admin_shutdown_bot_yes(message, bot)
@bot.message_handler(commands=['admin_shutdown_device'])
def command_admin_shutdown_device(message):
    func.print_log("/admin_shutdown_device: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "admin" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_shutdown_device")
    admin.command_admin_shutdown_device(message, bot)
@bot.message_handler(commands=['admin_shutdown_device_yes'])
def command_admin_shutdown_device_yes(message):
    func.print_log("/admin_shutdown_device_yes: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "admin_shutdown_device" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_shutdown_device_yes")
    admin.command_admin_shutdown_device_yes(message, bot)
@bot.message_handler(commands=['admin_restart_bot'])
def command_admin_restart_bot(message):
    func.print_log("/admin_restart_bot: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "admin" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_restart_bot")
    admin.command_admin_restart_bot(message, bot)
@bot.message_handler(commands=['admin_restart_bot_yes'])
def command_admin_restart_bot_yes(message):
    func.print_log("/admin_restart_bot_yes: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "admin_restart_bot" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_restart_bot_yes")
    admin.command_admin_restart_bot_yes(bot, message)
@bot.message_handler(commands=['admin_restart_device'])
def command_admin_restart_device(message):
    func.print_log("/admin_restart_device: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "admin" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_restart_device")
    admin.command_admin_restart_device(message, bot)
@bot.message_handler(commands=['admin_restart_device_yes'])
def command_admin_restart_device_yes(message):
    func.print_log("/admin_restart_device_yes: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "admin_restart_device" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "admin_restart_device_yes")
    admin.command_admin_restart_device_yes(message, bot)
@bot.message_handler(commands=['admin_return'])
def command_admin_return(message):
    func.print_log("/admin_return: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "admin" == database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
        admin.command_admin_return(message, bot)
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
    database.set_current_state(message, "help")
    basic_commands.command_help(message, bot)
@bot.message_handler(commands=['help_main'])
def command_help_main(message):
    func.print_log("/help_main: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "help" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "help_main")
    basic_commands.command_help_main(message, bot)
@bot.message_handler(commands=['help_features'])
def command_help_features(message):
    func.print_log("/help_features: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "help" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "help_features")
    basic_commands.command_help_features(message, bot)
@bot.message_handler(commands=['help_contact'])
def command_help_contact(message):
    func.print_log("/help_contact: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "help" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "help_contact")
    basic_commands.command_help_contact(message, bot)
@bot.message_handler(commands=['help_settings'])
def command_help_settings(message):
    func.print_log("/help_settings: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if "help" in database.get_current_state(message):
        basic_commands.delete_previous_bot_message(message, bot)
    database.set_current_state(message, "help_settings")
    basic_commands.command_help_settings(message, bot)
@bot.message_handler(commands=['help_return'])
def command_help_return(message):
    func.print_log("/help_return: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
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
def command_start(message):
    func.print_log("/start: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    basic_commands.command_start(message, bot)

# handle /contact command
@bot.message_handler(commands=['contact'])
def command_contact(message):
    func.print_log("/contact: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.set_current_state(message, "contact")
    basic_commands.command_contact(message, bot)

# handle /report command
@bot.message_handler(commands=['report'])
def command_report(message):
    func.print_log("/report: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.set_current_state(message, "report")
    basic_commands.command_report(message, bot)

# handle /deletedata command
@bot.message_handler(commands=['deletedata'])
def command_deletedata(message):
    func.print_log("/deletedata: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.set_current_state(message, "deletedata")
    basic_commands.command_deletedata(message, bot)
@bot.message_handler(commands=['deletedata_yes'])
def command_deletedata_yes(message):
    func.print_log("/deletedata_yes: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.get_current_state(message) == "deletedata":
        basic_commands.delete_previous_bot_message(message, bot)
        basic_commands.command_deletedata_yes(message, bot)
    else:
        not_working_buttons(message)
@bot.message_handler(commands=['deletedata_no'])
def command_deletedata_no(message):
    func.print_log("/deletedata_no: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.get_current_state(message) == "deletedata":
        basic_commands.delete_previous_bot_message(message, bot)
        database.set_current_state(message, "0")
        basic_commands.command_deletedata_no(message, bot)
    else:
        not_working_buttons(message)

# handle /language command
@bot.message_handler(commands=['language'])
def command_language(message):
    func.print_log("/language: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.set_current_state(message, "language")
    basic_commands.command_language(message, bot)
@bot.message_handler(commands=['language_pl'])
def command_language_pl(message):
    func.print_log("/language_pl: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.get_current_state(message) == "language":
        basic_commands.delete_previous_bot_message(message, bot)
        basic_commands.command_language_pl(message, bot)
        database.set_current_state(message, "0")
    else:
        not_working_buttons(message)
@bot.message_handler(commands=['language_en'])
def command_language_en(message):
    func.print_log("/language_en: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.get_current_state(message) == "language":
        basic_commands.delete_previous_bot_message(message, bot)
        basic_commands.command_language_en(message, bot)
        database.set_current_state(message, "0")
    else:
        not_working_buttons(message)
@bot.message_handler(commands=['language_cancel'])
def command_language_cancel(message):
    func.print_log("/language_cancel: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    if database.get_current_state(message) == "language":
        basic_commands.delete_previous_bot_message(message, bot)
        basic_commands.command_language_cancel(message, bot)
        database.set_current_state(message, "0")
    else:
        not_working_buttons(message)

# handle /about command
@bot.message_handler(commands=['about'])
def command_about(message):
    func.print_log("/about: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.set_current_state(message, "about")
    basic_commands.command_about(message, bot, ver)

# handle /tiktok command
@bot.message_handler(commands=['tiktok'])
def command_tiktok(message):
    func.print_log("/tiktok: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.set_current_state(message, "tiktok")
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
    database.set_current_state(message, "twitter")
    if database.user_check(message):
        basic_commands.command_twitter(message, bot)
    else:
        permission_denied(message)

# handle /reddit command
@bot.message_handler(commands=['reddit'])
def command_reddit(message):
    func.print_log("/reddit: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.set_current_state(message, "reddit")
    if database.user_check(message):
        basic_commands.command_reddit(message, bot)
    else:
        permission_denied(message)

# handle /tumblr command
@bot.message_handler(commands=['tumblr'])
def command_tumblr(message):
    func.print_log("/tumblr: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.set_current_state(message, "tumblr")
    if database.user_check(message):
        basic_commands.command_tumblr(message, bot)
    else:
        permission_denied(message)

# handle /youtube command
@bot.message_handler(commands=['youtube'])
def command_youtube(message):
    func.print_log("/youtube: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
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
    database.set_current_state(message, "instagram")
    if database.user_check(message):
        basic_commands.command_instagram(message, bot)
    else:
        permission_denied(message)

# handle TikTok URLs
@bot.message_handler(func=lambda message: downloader.check_url(message, ['https'], ['vm.tiktok.com', 'www.tiktok.com']))
def echo_tiktok(message):
    func.print_log("TikTok URL: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.set_current_state(message, "tiktok_url")
    if database.user_check(message):
        tiktok.start_tiktok(message, bot)
    else:
        permission_denied(message)

# handle Twitter URLs
@bot.message_handler(func=lambda message: downloader.check_url(message, ['https'], ['twitter.com']))
def echo_twitter(message):
    func.print_log("Twitter URL: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.set_current_state(message, "twitter_url")
    if database.user_check(message):
        twitter.start_twitter(message, bot)
    else:
        permission_denied(message)

# handle Reddit URLs
@bot.message_handler(func=lambda message: downloader.check_url(message, ['https'], ['www.reddit.com']))
def echo_reddit(message):
    func.print_log("Reddit URL: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.set_current_state(message, "reddit_url")
    if database.user_check(message):
        reddit.start_reddit(message, bot)
    else:
        permission_denied(message)

# handle Tumblr URLs
@bot.message_handler(func=lambda message: downloader.check_url(message, ['https'], ['www.tumblr.com']))
def echo_tumblr(message):
    func.print_log("Tumblr URL: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.set_current_state(message, "tumblr_url")
    if database.user_check(message):
        tumblr.start_tumblr(message, bot)
    else:
        permission_denied(message)

# handle YouTube URLs
@bot.message_handler(func=lambda message: downloader.check_url(message, ['https'], ['youtube.com', 'youtu.be']))
def echo_youtube(message):
    func.print_log("YouTube URL: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.set_current_state(message, "youtube_url")
    if database.user_check(message):
        youtube.start_youtube(message, bot)
    else:
        permission_denied(message)

# handle /crystalball command
@bot.message_handler(commands=['crystalball'])
def command_crystalball(message):
    func.print_log("/crystalball: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.set_current_state(message, "crystalball")
    crystal_ball.command_crystalball(message, bot)

# handle /topspotifyartist command
@bot.message_handler(commands=['topspotifyartist'])
def command_topspotifyartist(message):
    func.print_log("/topspotifyartist: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.set_current_state(message, "topspotifyartist")
    top_spotify_artist.command_topspotifyartist(message, bot)

# start topspotifyartist loop
def topspotifyartist(message):
    func.print_log("Top Spotify artist: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if "_topspotifyartist" in database.get_current_state(message):
        top_spotify_artist.topspotifyartist(message, bot)
    else:
        not_working_buttons(message)

# handle messages to admin
@bot.message_handler(func=lambda message: database.get_current_state(message) == "report")
def forward_message_to_admin(message):
    func.print_log("Report to admin: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    database.forward_message_to_admin(message, bot)

# handle topspotifyartist messages
@bot.message_handler(func=lambda message: "topspotifyartist_" in database.get_current_state(message))
def echo_topspotifyartist(message):
    func.print_log("Top Spotify artist guess: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    top_spotify_artist.topspotifyartist(message, bot)

# handle unknown command
@bot.message_handler(func=lambda message: message.text.startswith("/"))
def echo_unknown_command(message):
    func.print_log("Unknown command: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.set_current_state(message, "0")
    text = database.get_message_text(message, 'echo_unknown_command')
    mess = bot.send_message(message.chat.id, text)
    database.register_last_message(mess)

# handle any other message
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    func.print_log("Misunderstood message: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    if database.guest_check(message, bot) != True:
        return
    database.set_current_state(message, "0")
    text = database.get_message_text(message, 'echo_all')
    mess = bot.send_message(message.chat.id, text)
    database.register_last_message(mess)

# handle CTRL + C
def ctrl_c(signal, frame):
    database.send_stop_info(bot)
    time.sleep(1)
    func.print_log("", basic_commands.bot_name, 0)
    bot.stop_polling()
    database.commit_close()
    sys.exit(0)
signal.signal(signal.SIGINT, ctrl_c)

# fill artists list
top_spotify_artist.fill_artists()

# starting log message
func.print_log("", basic_commands.bot_name, 1)

# execute func sending info about restart
database.send_start_info(bot)

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