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
    text = database.get_message_text(message, 'command_admin_users_list')
    shutdown_bot_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_users_list")
    markup.add(shutdown_bot_button)
    text = database.get_message_text(message, 'command_admin_users_search')
    shutdown_device_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_users_search")
    markup.add(shutdown_device_button)
    text = database.get_message_text(message, 'command_admin_users_id_check')
    restart_bot_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_users_id_check")
    markup.add(restart_bot_button)
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
    text3 = database.get_message_text(message, 'update')
    text4 = database.get_message_text(message, 'command_admin_update_bot')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + " > " + text3 + ":*\n\n" + text4,
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_admin_update_bot_yes(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'admin_device')
    text3 = database.get_message_text(message, 'update')
    text4 = database.get_message_text(message, 'command_admin_update_bot_yes')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + " > " + text3 + ":*\n\n" + text4,
                     parse_mode = 'Markdown')
    subprocess.Popen([os.path.join(sys.path[0], __file__)[: (0 - len('bot/admin.py'))] + 'update.vbs'], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
    time.sleep(15)
    database.send_update_info_to_users(bot)
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'restart_bot')
    restart_bot_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_restart_bot")
    markup.add(restart_bot_button)
    text = database.get_message_text(message, 'shutdown_bot')
    restart_device_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_shutdown_bot")
    markup.add(restart_device_button)
    text = database.get_message_text(message, 'return')
    exit_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_return")
    markup.add(exit_button)
    text = database.get_message_text(message, 'command_admin_update_bot_yes_finish')
    mess = bot.send_message(message.chat.id, text, parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)

# handle showing user details
def command_admin_user(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    userid = int(database.get_current_state(message).split('_')[-1])
    markup.add(telebot.types.InlineKeyboardButton(text = database.get_message_text(message, 'command_admin_user_role_change'), callback_data = "command_admin_user_role_change_" + str(userid)))
    markup.add(telebot.types.InlineKeyboardButton(text = database.get_message_text(message, 'command_admin_user_deletedata'), callback_data = "command_admin_user_deletedata_" + str(userid)))
    markup.add(telebot.types.InlineKeyboardButton(text = database.get_message_text(message, 'return'), callback_data = "command_admin_return"))
    user = database.get_user_data(userid)
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'admin_users')
    text3 = database.get_message_text(message, 'command_admin_user')
    text4 = database.get_message_text(message, 'command_admin_user_mess')
    if user[0] == None or user[0].isascii() == 0:
        text4 = text4 + ":\n" + database.get_message_text(message, 'first_name') + ": <i>-</i>"
    else:
        text4 = text4 + ":\n" + database.get_message_text(message, 'first_name') + ": <i>" + telebot.telebot.formatting.escape_html(user[0]) + "</i>"
    if user[1] == None or user[1].isascii() == 0:
        text4 = text4 + "\n" + database.get_message_text(message, 'last_name') + ": <i>-</i>"
    else:
        text4 = text4 + "\n" + database.get_message_text(message, 'last_name') + ": <i>" + telebot.telebot.formatting.escape_html(user[1]) + "</i>"
    if user[2] == None or user[2].isascii() == 0:
        text4 = text4 + "\n" + database.get_message_text(message, 'username') + ": <i>-</i>"
    else:
        text4 = text4 + "\n" + database.get_message_text(message, 'username') + ": <i>@" + telebot.telebot.formatting.escape_html(user[2]) + "</i>"
    if user[3] == None:
        role = "-"
    else:
        if user[3] == -1:
            role = database.get_message_text(message, 'role_banned')
        elif user[3] == 0:
            role = database.get_message_text(message, 'role_guest')
        elif user[3] == 1:
            role = database.get_message_text(message, 'role_user')
        else:
            role = database.get_message_text(message, 'role_admin')
    text4 = text4 + "\n" + database.get_message_text(message, 'role') + ": <i>" + role + "</i>"
    text4 = text4 + "\n" + "Telegram ID" + ": <i>" + str(userid) + "</i>"
    mess = bot.send_message(message.chat.id, "<b>" + text1 + " > " + text2 + " > " + text3 + ":</b>\n\n" + text4,
                     parse_mode = 'html', reply_markup = markup)
    database.register_last_message(mess)

# handle editing user role
def command_admin_user_role_change(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    userid = database.get_current_state(message).split('_')[-1]
    user = database.get_user_data(userid)
    for i in range(-1, 3):
        if i != user[3]:
            if i == -1:
                markup.add(telebot.types.InlineKeyboardButton(text = database.get_message_text(message, 'role_banned'), callback_data = "command_admin_user_role_changed_9" + str(userid)))
            elif i == 0:
                markup.add(telebot.types.InlineKeyboardButton(text = database.get_message_text(message, 'role_guest'), callback_data = "command_admin_user_role_changed_0" + str(userid)))
            elif i == 1:
                markup.add(telebot.types.InlineKeyboardButton(text = database.get_message_text(message, 'role_user'), callback_data = "command_admin_user_role_changed_1" + str(userid)))
            elif i == 2:
                markup.add(telebot.types.InlineKeyboardButton(text = database.get_message_text(message, 'role_admin'), callback_data = "command_admin_user_role_changed_2" + str(userid)))
    markup.add(telebot.types.InlineKeyboardButton(text = database.get_message_text(message, 'return'), callback_data = "command_admin_return_" + str(userid)))
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'admin_users')
    text3 = database.get_message_text(message, 'command_admin_user')
    text4 = database.get_message_text(message, 'command_admin_user_role_change')
    text5 = database.get_message_text(message, 'command_admin_user_role_change_mess')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + " > " + text3 + " > " + text4 + ":*\n\n" + text5 + ":",
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)

# handle user data deletion
def command_admin_user_deletedata(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    userid = database.get_current_state(message).split('_')[-1]
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'yes')
    yes_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_user_deletedata_yes_" + userid)
    markup.add(yes_button)
    text = database.get_message_text(message, 'no')
    no_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_return_" + userid)
    markup.add(no_button)
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'admin_users')
    text3 = database.get_message_text(message, 'command_admin_user')
    text4 = database.get_message_text(message, 'command_admin_user_deletedata')
    text5 = database.get_message_text(message, 'command_admin_user_deletedata_mess')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + " > " + text3 + " > " + text4 + ":*\n\n" + text5,
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_admin_user_deletedata_yes(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    userid = database.get_current_state(message).split('_')[-1]
    database.deletedata(database.create_empty_message(int(userid)))
    markup = telebot.types.InlineKeyboardMarkup()
    text = database.get_message_text(message, 'return')
    no_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_return")
    markup.add(no_button)
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'admin_users')
    text3 = database.get_message_text(message, 'command_admin_user')
    text4 = database.get_message_text(message, 'command_admin_user_deletedata')
    text5 = database.get_message_text(message, 'command_admin_user_deletedata_yes_mess')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + " > " + text3 + " > " + text4 + ":*\n\n" + text5,
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)

# handle choosing user from users list
def command_admin_users_list(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    markup = telebot.types.InlineKeyboardMarkup()
    users = database.get_users()
    for user in users:
        markup.add(telebot.types.InlineKeyboardButton(text = user[1] + " (" + str(user[0]) + ")", callback_data = "command_admin_user_" + str(user[0])))
    text = database.get_message_text(message, 'return')
    exit_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_admin_return")
    markup.add(exit_button)
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'admin_users')
    text3 = database.get_message_text(message, 'command_admin_users_list')
    text4 = database.get_message_text(message, 'command_admin_users_list_mess')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + " > " + text3 + ":*\n\n" + text4 + ":",
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)

# handle searching for user with userid
def command_admin_users_search(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'admin_users')
    text3 = database.get_message_text(message, 'command_admin_users_search')
    text4 = database.get_message_text(message, 'command_admin_users_search_mess')
    mess = bot.send_message(message.chat.id, "*" + text1 + " > " + text2 + " > " + text3 + ":*\n\n" + text4 + ":",
                     parse_mode = 'Markdown')
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
        database.set_current_state(message, 'admin_users_id_check_correct')
    database.register_last_message(mess)

def command_admin_return(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text1 = database.get_message_text(message, 'admin')
    text2 = database.get_message_text(message, 'command_return')
    mess = bot.send_message(message.chat.id, "*" + text1 + ":*\n\n" + text2 + " _/admin_ ❌", parse_mode='Markdown')
    database.register_last_message(mess)