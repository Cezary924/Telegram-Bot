import telebot, requests
from urllib.parse import parse_qs, urlparse

import func, database

# open file containing bot name and read from it
bot_name = func.read_file("bot_name.txt", "../files/bot_name.txt")
bot_name = str(bot_name[0])
if func.suffix == 1:
    bot_name = "Beta" + bot_name

# open file containing GitHub username and read from it
github_username = func.read_file("github_username.txt", "../files/github_username.txt")
github_username = str(github_username[0])

# open file containing GitHub repo and read from it
github_repo = func.read_file("github_repo.txt", "../files/github_repo.txt")
github_repo = str(github_repo[0])

# get commits number from GitHub
def info_about_version(ver, message = None):
    response = requests.get("https://api.github.com/repos/" + github_username + "/" + github_repo + "/commits?per_page=1")
    if message == None:
        if response.status_code != 200:
            return (0, "Błąd. Spróbuj później.")
        online_ver = int(parse_qs(urlparse(response.links["last"]["url"]).query)["page"][0])
        if ver > online_ver:
            return (online_ver, "Beta (Stabilna: " + str(online_ver) + ")")
        elif ver == online_ver:
            return (online_ver, "Aktualna")
        else:
            return (online_ver, "Przestarzała (Aktualna: " + str(online_ver) + ")")
    else:
        if response.status_code != 200:
            text = database.get_message_text(message, 'error')
            return (0, text)
        online_ver = int(parse_qs(urlparse(response.links["last"]["url"]).query)["page"][0])
        if ver > online_ver:
            text = database.get_message_text(message, 'beta_ver')
            return (online_ver, text + ": " + str(online_ver) + ")")
        elif ver == online_ver:
            text = database.get_message_text(message, 'up-to-date_ver')
            return (online_ver, text)
        else:
            text = database.get_message_text(message, 'old_ver')
            return (online_ver, text + ": " + str(online_ver) + ")")

# delete previously sent message by bot
def delete_previous_bot_message(message, bot):
    # func.print_log("Delete previous message: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    bot.delete_message(message.chat.id, database.get_last_message(message))

# handle /start command
def command_start(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'help')
    help_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_help")
    markup.add(help_button)
    text = database.get_message_text(message, 'about')
    about_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_about")
    markup.add(about_button)
    text1 = database.get_message_text(message, 'hi')
    text2 = database.get_message_text(message, 'command_start')
    mess = bot.send_message(message.chat.id, "*👋 " + text1 + "!*\n\n" + text2 + " " + bot_name + "! 🤖",
                      parse_mode = 'Markdown', reply_markup = markup)
    if database.guest_check(message, bot) != True:
        return
    database.save_current_state(message, "start")
    database.register_last_message(mess)

# handle /help command
def command_help(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'main')
    main_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_help_main")
    markup.add(main_button)
    text = database.get_message_text(message, 'downloader')
    downloader_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_help_downloader")
    markup.add(downloader_button)
    text = database.get_message_text(message, 'contact')
    contact_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_help_contact")
    markup.add(contact_button)
    text = database.get_message_text(message, 'settings')
    settings_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_help_settings")
    markup.add(settings_button)
    text = database.get_message_text(message, 'exit')
    exit_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_help_return")
    markup.add(exit_button)
    text1 = database.get_message_text(message, 'help')
    text2 = database.get_message_text(message, 'command_help')
    mess = bot.send_message(message.chat.id, "*" + text1 + ":*\n\n" + text2,
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_help_main(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'return')
    help_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_help_return")
    markup.add(help_button)
    text1 = database.get_message_text(message, 'help')
    text2 = database.get_message_text(message, 'main')
    text3 = database.get_message_text(message, 'command_help_main')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + ":*\n\n" + text3, parse_mode= 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_help_downloader(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'return')
    help_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_help_return")
    markup.add(help_button)
    text1 = database.get_message_text(message, 'help')
    text2 = database.get_message_text(message, 'downloader')
    text3 = database.get_message_text(message, 'command_help_downloader')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + ":*\n\n" + text3, parse_mode= 'Markdown', reply_markup = markup) 
    database.register_last_message(mess)
def command_help_contact(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'return')
    help_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_help_return")
    markup.add(help_button)
    text1 = database.get_message_text(message, 'help')
    text2 = database.get_message_text(message, 'contact')
    text3 = database.get_message_text(message, 'command_help_contact')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + ":*\n\n" + text3, parse_mode= 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_help_settings(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'return')
    help_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_help_return")
    markup.add(help_button)
    text1 = database.get_message_text(message, 'help')
    text2 = database.get_message_text(message, 'settings')
    text3 = database.get_message_text(message, 'command_help_settings')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + ":*\n\n" + text3, parse_mode= 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_help_return(message, bot):
    text = database.get_message_text(message, 'command_help_return')
    mess = bot.send_message(message.chat.id, text, parse_mode='Markdown')
    database.register_last_message(mess)

# handle /contact command
def command_contact(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'report')
    report_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_report")
    markup.add(report_button)
    text = database.get_message_text(message, 'command_contact')
    mess = bot.send_message(message.chat.id, text, 
                     parse_mode = 'Markdown',
                     reply_markup = markup)
    database.register_last_message(mess)

# handle /report command
def command_report(message, bot):
    text = database.get_message_text(message, 'command_report')
    mess = bot.send_message(message.chat.id, text, parse_mode= 'Markdown')
    database.register_last_message(mess)

# handle /deletedata command
def command_deletedata(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'yes')
    yes_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_deletedata_yes")
    markup.add(yes_button)
    text = database.get_message_text(message, 'no')
    no_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_deletedata_no")
    markup.add(no_button)
    text = database.get_message_text(message, 'command_deletedata')
    mess = bot.send_message(message.chat.id, text, 
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_deletedata_yes(message, bot):
    database.deletedata(message)
    text = database.get_message_text(message, 'command_deletedata_yes')
    mess = bot.send_message(message.chat.id, text, parse_mode='Markdown')
    database.register_last_message(mess)
def command_deletedata_no(message, bot):
    text = database.get_message_text(message, 'command_deletedata_no')
    mess = bot.send_message(message.chat.id, text, parse_mode='Markdown')
    database.register_last_message(mess)

# handle /language command
def command_language(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    pl_button = telebot.types.InlineKeyboardButton(text = "🇵🇱 Polski", callback_data = "command_language_pl")
    markup.add(pl_button)
    en_button = telebot.types.InlineKeyboardButton(text = "🇬🇧 English (not fully translated 😞)", callback_data = "command_language_en")
    markup.add(en_button)
    text = database.get_message_text(message, 'exit')
    cancel_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_language_cancel")
    markup.add(cancel_button)
    text = database.get_message_text(message, 'command_language')
    mess = bot.send_message(message.chat.id, text, 
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_language_pl(message, bot):
    database.set_user_language(message, 'pl')
    mess = bot.send_message(message.chat.id, "🌐 *Zmiana języka:*\n\nGotowe 🇵🇱", parse_mode='Markdown')
    database.register_last_message(mess)
def command_language_en(message, bot):
    database.set_user_language(message, 'en')
    mess = bot.send_message(message.chat.id, "🌐 *Language:*\n\nDone 🇬🇧", parse_mode='Markdown')
    database.register_last_message(mess)
def command_language_cancel(message, bot):
    text = database.get_message_text(message, 'command_language_cancel')
    mess = bot.send_message(message.chat.id, text, parse_mode='Markdown')
    database.register_last_message(mess)

# handle /about command
def command_about(message, bot, ver):
    #text1 = database.get_message_text(message, 'command_about_year')
    text2 = database.get_message_text(message, 'command_about_ver_status')
    text3 = database.get_message_text(message, 'command_about_ver')
    text4 = database.get_message_text(message, 'command_about_github_username')
    text5 = database.get_message_text(message, 'description')
    text6 = database.get_message_text(message, 'command_about_description')
    text7 = database.get_message_text(message, 'command_about')
    mess = bot.send_message(message.chat.id, "*ℹ️ " + text7 + ":*\n\n"
                    + "*" + bot_name + "*\n"
                    + text5 + ": _" + text6 + "_\n"
                    + text4 + ": _@" + github_username + "_\n"
                    + text3 + ": _" + str(ver) + "_\n"
                    + text2 + ": _" + info_about_version(ver, message)[1] + "_\n"
                    #+ text1 + ": _2023_", parse_mode= 'Markdown')
                    + "© _2023_", parse_mode= 'Markdown')
    database.register_last_message(mess)

# handle /tiktok command
def command_tiktok(message, bot):
    text = database.get_message_text(message, 'command_tiktok')
    mess = bot.send_message(message.chat.id, text, parse_mode= 'Markdown')
    database.register_last_message(mess)

# handle /twitter command
def command_twitter(message, bot):
    text = database.get_message_text(message, 'command_twitter')
    mess = bot.send_message(message.chat.id, text, parse_mode= 'Markdown')
    database.register_last_message(mess)

# handle /reddit command
def command_reddit(message, bot):
    text = database.get_message_text(message, 'command_reddit')
    mess = bot.send_message(message.chat.id, text, parse_mode= 'Markdown')
    database.register_last_message(mess)

# handle /tumblr command
def command_tumblr(message, bot):
    text = database.get_message_text(message, 'command_tumblr')
    mess = bot.send_message(message.chat.id, text, parse_mode= 'Markdown')
    database.register_last_message(mess)
    