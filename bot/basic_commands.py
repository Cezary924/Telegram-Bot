import telebot, requests, subprocess
from urllib.parse import parse_qs, urlparse

import func, database

# open file containing bot name and read from it
bot_name = func.config['bot_name']
if func.suffix == 1:
    bot_name = "Beta" + bot_name

# open file containing Telegram username and read from it
telegram_username = func.config['telegram_username']

# open file containing GitHub username and read from it
github_username = func.config['github_username']

# open file containing GitHub repo and read from it
github_repo = func.config['github_repo']

# get commits number from GitHub
def info_about_version(ver: int, message: telebot.types.Message = None) -> tuple[int, str]:
    response = requests.get("https://api.github.com/repos/" + github_username + "/" + github_repo + "/commits?per_page=1")
    if response.status_code != 200:
        text = database.get_message_text(message, 'error')
        return (0, text)
    online_ver = int(parse_qs(urlparse(response.links["last"]["url"]).query)["page"][0])
    if ver > online_ver:
        response = requests.get("https://api.github.com/repos/" + github_username + "/" + github_repo + "/releases/latest")
        if response.status_code != 200:
            text = database.get_message_text(message, 'error')
            return (0, text)
        text = database.get_message_text(message, 'beta_ver')
        return (online_ver, (text + ": " + response.json()['tag_name'] + " (" + str(online_ver) + "))").replace('\n', ''))
    elif ver == online_ver:
        text = database.get_message_text(message, 'up-to-date_ver')
        return (online_ver, text.replace('\n', ''))
    else:
        response = requests.get("https://api.github.com/repos/" + github_username + "/" + github_repo + "/releases/latest")
        if response.status_code != 200:
            text = database.get_message_text(message, 'error')
            return (0, text)
        text = database.get_message_text(message, 'old_ver')
        return (online_ver, (text + ": " + response.json()['tag_name'] + " (" + str(online_ver) + "))").replace('\n', ''))

# delete previously sent message by Bot
def delete_previous_bot_message(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    bot.delete_message(message.chat.id, database.get_last_message(message))

# handle /start command
def command_start(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'help')
    help_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_help")
    markup.add(help_button)
    text = database.get_message_text(message, 'features')
    features_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_features")
    markup.add(features_button)
    text = database.get_message_text(message, 'about')
    about_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_about")
    markup.add(about_button)
    text1 = database.get_message_text(message, 'hi')
    text2 = database.get_message_text(message, 'command_start')
    mess = bot.send_message(message.chat.id, "*👋 " + text1 + "!*\n\n" + text2 + " " + bot_name + "! 🤖",
                      parse_mode = 'Markdown', reply_markup = markup)
    if database.guest_check(message, bot) != True:
        return
    database.set_current_state(message, "start")
    database.register_last_message(mess)

# handle /features command
def command_features(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text2 = database.get_message_text(message, 'features')
    text3 = database.get_message_text(message, 'command_help_features')
    mess = bot.send_message(message.chat.id, "*" + text2 + ":*\n\n" + text3, parse_mode= 'Markdown') 
    database.register_last_message(mess)

# handle /help command
def command_help(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'main')
    main_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_help_main")
    markup.add(main_button)
    text = database.get_message_text(message, 'features')
    downloader_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_help_features")
    markup.add(downloader_button)
    text = database.get_message_text(message, 'contact')
    contact_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_help_contact")
    markup.add(contact_button)
    text = database.get_message_text(message, 'exit')
    exit_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_help_return")
    markup.add(exit_button)
    text1 = database.get_message_text(message, 'help')
    text2 = database.get_message_text(message, 'command_help')
    mess = bot.send_message(message.chat.id, "*" + text1 + ":*\n\n" + text2 + ":",
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_help_main(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'return')
    help_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_help_return")
    markup.add(help_button)
    text1 = database.get_message_text(message, 'help')
    text2 = database.get_message_text(message, 'main')
    text3 = database.get_message_text(message, 'command_help_main')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + ":*\n\n" + text3, parse_mode= 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_help_features(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'return')
    help_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_help_return")
    markup.add(help_button)
    text1 = database.get_message_text(message, 'help')
    text2 = database.get_message_text(message, 'features')
    text3 = database.get_message_text(message, 'command_help_features')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + ":*\n\n" + text3, parse_mode= 'Markdown', reply_markup = markup) 
    database.register_last_message(mess)
def command_help_contact(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'return')
    help_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_help_return")
    markup.add(help_button)
    text1 = database.get_message_text(message, 'help')
    text2 = database.get_message_text(message, 'contact')
    text3 = database.get_message_text(message, 'command_help_contact')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + ":*\n\n" + text3, parse_mode= 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_help_return(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text = database.get_message_text(message, 'command_help_return')
    mess = bot.send_message(message.chat.id, text, parse_mode='Markdown')
    database.register_last_message(mess)

# handle /contact command
def command_contact(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'report')
    report_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_report")
    markup.add(report_button)
    text = database.get_message_text(message, 'command_contact')
    text = text.split("@")[0] + "@" + telegram_username + text.split("@")[1]
    mess = bot.send_message(message.chat.id, text, 
                     parse_mode = 'Markdown',
                     reply_markup = markup)
    database.register_last_message(mess)

# handle /report command
def command_report(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text = database.get_message_text(message, 'command_report')
    mess = bot.send_message(message.chat.id, text, parse_mode= 'Markdown')
    database.register_last_message(mess)

# handle /settings command
def command_settings(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    if database.get_user_data(message.chat.id)[3] > 0:
        text = database.get_message_text(message, 'notifications')
        notifications_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_settings_notifications")
        markup.add(notifications_button)
    text = database.get_message_text(message, 'language')
    language_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_settings_language")
    markup.add(language_button)
    text = database.get_message_text(message, 'deletedata')
    deletedata_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_settings_deletedata")
    markup.add(deletedata_button)
    text = database.get_message_text(message, 'exit')
    exit_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_settings_return")
    markup.add(exit_button)
    text1 = database.get_message_text(message, 'settings')
    text2 = database.get_message_text(message, 'command_settings')
    mess = bot.send_message(message.chat.id, "*" + text1 + ":*\n\n" + text2, 
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_settings_notifications(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'yes')
    yes_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_settings_notifications_changed_1")
    markup.add(yes_button)
    text = database.get_message_text(message, 'no')
    no_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_settings_notifications_changed_0")
    markup.add(no_button)
    text1 = database.get_message_text(message, 'settings')
    text2 = database.get_message_text(message, 'notifications')
    text3 = database.get_message_text(message, 'command_settings_notifications')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + ":*\n\n" + text3, parse_mode='Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_settings_notifications_changed(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'return')
    return_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_settings_return")
    markup.add(return_button)
    text1 = database.get_message_text(message, 'settings')
    text2 = database.get_message_text(message, 'notifications')
    if database.get_current_state(message).split('_')[-1] == '1':
        text3 = database.get_message_text(message, 'command_settings_notifications_yes')
        database.set_user_notifications(message, 1)
    else:
        text3 = database.get_message_text(message, 'command_settings_notifications_no')
        database.set_user_notifications(message, 0)
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + ":*\n\n" + text3, parse_mode='Markdown', reply_markup=markup)
    database.register_last_message(mess)
def command_settings_language(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    pl_button = telebot.types.InlineKeyboardButton(text = "🇵🇱 Polski", callback_data = "command_settings_language_changed_1")
    markup.add(pl_button)
    en_button = telebot.types.InlineKeyboardButton(text = "🇬🇧 English", callback_data = "command_settings_language_changed_0")
    markup.add(en_button)
    text = database.get_message_text(message, 'return')
    cancel_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_settings_return")
    markup.add(cancel_button)
    text1 = database.get_message_text(message, 'settings')
    text2 = database.get_message_text(message, 'language')
    text3 = database.get_message_text(message, 'command_settings_language')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + ":*\n\n" + text3, parse_mode='Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_settings_language_changed(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    lang_id = int(database.get_current_state(message).split('_')[-1])
    if lang_id == 1:
        database.set_user_language(message, 'pl')
    else:
        database.set_user_language(message, 'en')
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'return')
    cancel_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_settings_return")
    markup.add(cancel_button)
    text1 = database.get_message_text(message, 'settings')
    text2 = database.get_message_text(message, 'language')
    text3 = database.get_message_text(message, 'command_settings_language_changed')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + ":*\n\n" + text3, parse_mode='Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_settings_deletedata(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'yes')
    yes_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_settings_deletedata_yes")
    markup.add(yes_button)
    text = database.get_message_text(message, 'no')
    no_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_settings_return")
    markup.add(no_button)
    text1 = database.get_message_text(message, 'settings')
    text2 = database.get_message_text(message, 'deletedata')
    text3 = database.get_message_text(message, 'command_settings_deletedata')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + ":*\n\n" + text3, parse_mode='Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_settings_deletedata_yes(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    database.deletedata(message)
    text1 = database.get_message_text(message, 'settings')
    text2 = database.get_message_text(message, 'deletedata')
    text3 = database.get_message_text(message, 'command_settings_deletedata_yes')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + ":*\n\n" + text3, parse_mode='Markdown')
    database.register_last_message(mess)
def command_settings_return(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text1 = database.get_message_text(message, 'settings')
    text2 = database.get_message_text(message, 'command_settings_return')
    mess = bot.send_message(message.chat.id, "*" + text1 + ":*\n\n" + text2, parse_mode='Markdown')
    database.register_last_message(mess)

# handle /about command
def command_about(message: telebot.types.Message, bot: telebot.TeleBot, ver: int, tag: str) -> None:
    text1 = database.get_message_text(message, 'command_about_ver_status')
    text2 = database.get_message_text(message, 'command_about_ver')
    text3 = database.get_message_text(message, 'command_about_github_username')
    text4 = database.get_message_text(message, 'description')
    text5 = database.get_message_text(message, 'command_about_description')
    text6 = database.get_message_text(message, 'command_about')
    mess = bot.send_message(message.chat.id, "*ℹ️ " + text6 + ":*\n\n"
                    + "*" + bot_name + "*\n"
                    + text4 + ": _" + text5 + "_\n"
                    + text3 + ": _@" + github_username + "_\n"
                    + text2 + ": _" + tag + " (" + str(ver) + ")_\n"
                    + text1 + ": _" + info_about_version(ver, message)[1] + "_\n"
                    + "© _2023_", parse_mode= 'Markdown')
    database.register_last_message(mess)

# handle /tiktok command
def command_tiktok(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text1 = database.get_message_text(message, 'command_downloader')
    text2 = database.get_message_text(message, 'tiktok')
    mess = bot.send_message(message.chat.id, text2 + text1, parse_mode= 'Markdown')
    database.register_last_message(mess)

# handle /twitter command
def command_twitter(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text1 = database.get_message_text(message, 'command_downloader')
    text2 = database.get_message_text(message, 'twitter')
    mess = bot.send_message(message.chat.id, text2 + text1, parse_mode= 'Markdown')
    database.register_last_message(mess)

# handle /reddit command
def command_reddit(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text1 = database.get_message_text(message, 'command_downloader')
    text2 = database.get_message_text(message, 'reddit')
    mess = bot.send_message(message.chat.id, text2 + text1, parse_mode= 'Markdown')
    database.register_last_message(mess)

# handle /tumblr command
def command_tumblr(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text1 = database.get_message_text(message, 'command_downloader')
    text2 = database.get_message_text(message, 'tumblr')
    mess = bot.send_message(message.chat.id, text2 + text1, parse_mode= 'Markdown')
    database.register_last_message(mess)

# handle /youtube command
def command_youtube(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text1 = database.get_message_text(message, 'command_downloader')
    text2 = database.get_message_text(message, 'youtube')
    mess = bot.send_message(message.chat.id, text2 + text1, parse_mode= 'Markdown')
    database.register_last_message(mess)

# handle /instagram command
def command_instagram(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text1 = database.get_message_text(message, 'command_downloader')
    text2 = database.get_message_text(message, 'instagram')
    mess = bot.send_message(message.chat.id, text2 + text1, parse_mode= 'Markdown')
    database.register_last_message(mess)

# handle /unitconverter command
def command_unitconverter(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text1 = database.get_message_text(message, 'unitconverter')
    text2 = database.get_message_text(message, 'command_unitconverter')
    mess = bot.send_message(message.chat.id, telebot.telebot.formatting.hbold(text1 + ":\n\n") + text2, parse_mode = 'html')
    database.register_last_message(mess)