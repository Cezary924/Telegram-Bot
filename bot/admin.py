import telebot, os, signal, sys, subprocess, time
import database

# handle /admin command
def command_admin(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'admin_users')
    users_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_users")
    markup.add(users_button)
    text = database.get_message_text(message, 'admin_bot')
    bot_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_bot")
    markup.add(bot_button)
    text = database.get_message_text(message, 'admin_device')
    device_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_device")
    markup.add(device_button)
    text = database.get_message_text(message, 'exit')
    exit_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_return")
    markup.add(exit_button)
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'admin_menu')
    mess = bot.send_message(message.chat.id, "*" + text1 + ":*\n\n" + text2,
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)

# handle Admin Users menu
def command_admin_users(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'shutdown')
    shutdown_bot_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_shutdown_bot")
    markup.add(shutdown_bot_button)
    text = database.get_message_text(message, 'shutdown')
    shutdown_device_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_shutdown_device")
    markup.add(shutdown_device_button)
    text = database.get_message_text(message, 'restart')
    restart_bot_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_restart_bot")
    markup.add(restart_bot_button)
    text = database.get_message_text(message, 'restart')
    restart_device_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_restart_device")
    markup.add(restart_device_button)
    text = database.get_message_text(message, 'return')
    exit_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_return")
    markup.add(exit_button)
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'admin_users')
    text3 = database.get_message_text(message, 'admin_menu')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + ":*\n\n" + text3,
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)

# handle Admin Bot menu
def command_admin_bot(message: telebot.types.Message, bot: telebot.TeleBot, update: bool) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    if update:
        text = database.get_message_text(message, 'update')
        update_bot_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_update_bot")
        markup.add(update_bot_button)
    text = database.get_message_text(message, 'shutdown')
    shutdown_bot_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_shutdown_bot")
    markup.add(shutdown_bot_button)
    text = database.get_message_text(message, 'restart')
    restart_bot_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_restart_bot")
    markup.add(restart_bot_button)
    text = database.get_message_text(message, 'return')
    exit_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_return")
    markup.add(exit_button)
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'admin_bot')
    text3 = database.get_message_text(message, 'admin_menu')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + ":*\n\n" + text3,
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)

# handle Admin Device menu
def command_admin_device(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'shutdown')
    shutdown_device_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_shutdown_device")
    markup.add(shutdown_device_button)
    text = database.get_message_text(message, 'restart')
    restart_device_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_restart_device")
    markup.add(restart_device_button)
    text = database.get_message_text(message, 'return')
    exit_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_return")
    markup.add(exit_button)
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'admin_device')
    text3 = database.get_message_text(message, 'admin_menu')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + ":*\n\n" + text3,
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)

# handle Bot shutdown command
def command_admin_shutdown_bot(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'yes')
    yes_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_shutdown_bot_yes")
    markup.add(yes_button)
    text = database.get_message_text(message, 'no')
    no_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_return")
    markup.add(no_button)
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'admin_device')
    text3 = database.get_message_text(message, 'shutdown')
    text4 = database.get_message_text(message, 'command_admin_shutdown_bot')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + " > " + text3 + ":*\n\n" + text4,
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_admin_shutdown_bot_yes(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'admin_device')
    text3 = database.get_message_text(message, 'shutdown')
    text4 = database.get_message_text(message, 'command_admin_shutdown_bot_yes')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + " > " + text3 + ":*\n\n" + text4,
                     parse_mode = 'Markdown')
    os.kill(os.getpid(), signal.SIGINT)

# handle device shutdown command
def command_admin_shutdown_device(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'yes')
    yes_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_shutdown_device_yes")
    markup.add(yes_button)
    text = database.get_message_text(message, 'no')
    no_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_return")
    markup.add(no_button)
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'admin_device')
    text3 = database.get_message_text(message, 'shutdown')
    text4 = database.get_message_text(message, 'command_admin_shutdown_device')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + " > " + text3 + ":*\n\n" + text4,
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_admin_shutdown_device_yes(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'admin_device')
    text3 = database.get_message_text(message, 'shutdown')
    text4 = database.get_message_text(message, 'command_admin_shutdown_device_yes')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + " > " + text3 + ":*\n\n" + text4,
                     parse_mode = 'Markdown')
    os.system("shutdown /s /t 1")

# handle Bot restart
def command_admin_restart_bot(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'yes')
    yes_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_restart_bot_yes")
    markup.add(yes_button)
    text = database.get_message_text(message, 'no')
    no_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_return")
    markup.add(no_button)
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'admin_device')
    text3 = database.get_message_text(message, 'shutdown')
    text4 = database.get_message_text(message, 'command_admin_restart_bot')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + " > " + text3 + ":*\n\n" + text4,
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_admin_restart_bot_yes(bot: telebot.TeleBot, message: telebot.types.Message = None, send_mess: bool = 1) -> None:
    if send_mess:
        text1 = database.get_message_text(message, 'admin')
        text2 = database.get_message_text(message, 'admin_device')
        text3 = database.get_message_text(message, 'shutdown')
        text4 = database.get_message_text(message, 'command_admin_restart_bot_yes')
        mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + " > " + text3 + ":*\n\n" + text4,
                        parse_mode = 'Markdown')
    subprocess.Popen([os.path.join(sys.path[0], __file__)[: (0 - len('bot/admin.py'))] + 'run.vbs'] + sys.argv[1:], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
    os.kill(os.getpid(), signal.SIGINT)

# handle device restart
def command_admin_restart_device(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'yes')
    yes_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_restart_device_yes")
    markup.add(yes_button)
    text = database.get_message_text(message, 'no')
    no_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_return")
    markup.add(no_button)
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'admin_device')
    text3 = database.get_message_text(message, 'shutdown')
    text4 = database.get_message_text(message, 'command_admin_restart_device')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + " > " + text3 + ":*\n\n" + text4,
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_admin_restart_device_yes(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'admin_device')
    text3 = database.get_message_text(message, 'shutdown')
    text4 = database.get_message_text(message, 'command_admin_restart_device_yes')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + " > " + text3 + ":*\n\n" + text4,
                     parse_mode = 'Markdown')
    os.system("shutdown /r /t 1")

# handle Bot update
def command_admin_update_bot(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'yes')
    yes_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_update_bot_yes")
    markup.add(yes_button)
    text = database.get_message_text(message, 'no')
    no_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_return")
    markup.add(no_button)
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'admin_device')
    text3 = database.get_message_text(message, 'shutdown')
    text4 = database.get_message_text(message, 'command_admin_update_bot')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + " > " + text3 + ":*\n\n" + text4,
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_admin_update_bot_yes(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'admin_device')
    text3 = database.get_message_text(message, 'shutdown')
    text4 = database.get_message_text(message, 'command_admin_update_bot_yes')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + " > " + text3 + ":*\n\n" + text4,
                     parse_mode = 'Markdown')
    subprocess.Popen([os.path.join(sys.path[0], __file__)[: (0 - len('bot/admin.py'))] + 'update.vbs'], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
    time.sleep(15)
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'restart_bot')
    restart_bot_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_restart_bot")
    markup.add(restart_bot_button)
    text = database.get_message_text(message, 'shutdown_bot')
    restart_device_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_shutdown_bot")
    markup.add(restart_device_button)
    text = database.get_message_text(message, 'exit')
    exit_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_return")
    markup.add(exit_button)
    text = database.get_message_text(message, 'command_admin_update_bot_yes_finish')
    mess = bot.send_message(message.chat.id, text, parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)

# handle checking userid of message creator
def command_admin_users_id_check(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'admin_users')
    text3 = database.get_message_text(message, 'command_admin_users_id_check')
    text4 = database.get_message_text(message, 'command_admin_users_id_check_mess')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + " > " + text3 + ":*\n\n" + text4,
                     parse_mode = 'Markdown')
    database.register_last_message(mess)
def command_admin_users_id_check_received_message(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'return')
    exit_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_return")
    markup.add(exit_button)
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'admin_users')
    text3 = database.get_message_text(message, 'command_admin_users_id_check')
    try:
        userid = message.forward_from.id
        first_name = message.forward_from.first_name
    except:
        text4 = database.get_message_text(message, 'command_admin_users_id_check_received_message_wrong')
        mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + " > " + text3 + ":*\n\n" + text4,
                        parse_mode = 'Markdown', reply_markup = markup)
    else:
        text4 = database.get_message_text(message, 'command_admin_users_id_check_received_message')
        mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + " > " + text3 + ":*\n\n" + text4 + " " + first_name + " (" + str(userid) + ").",
                        parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)

def command_admin_return(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text = database.get_message_text(message, 'command_admin_return')
    mess = bot.send_message(message.chat.id, text, parse_mode='Markdown')
    database.register_last_message(mess)