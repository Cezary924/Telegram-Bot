import telebot, time
from threading import Thread
from datetime import datetime

import database

def check_reminders() -> None:
    while True:
        t = datetime.utcnow()
        sleeptime = 60 - (t.second + t.microsecond/1000000.0)
        time.sleep(sleeptime)
        #print(datetime.utcnow())

thread = Thread(target = check_reminders, daemon = True)
thread.start()

# handle /reminder command
def command_reminder(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    number, reminders = database.get_reminders(message)
    text1 = database.get_message_text(message, 'reminder')
    text2 = database.get_message_text(message, 'command_reminder')
    markup = telebot.types.InlineKeyboardMarkup()
    text3 = database.get_message_text(message, 'reminder_set_button')
    create_button = telebot.types.InlineKeyboardButton(text = text3, callback_data = "command_reminder_set")
    markup.add(create_button)
    if number > 0:
        text3 = database.get_message_text(message, 'reminder_manage_button')
        manage_button = telebot.types.InlineKeyboardButton(text = text3, callback_data = "command_reminder_manage")
        markup.add(manage_button)
    text3 = database.get_message_text(message, 'exit')
    exit_button = telebot.types.InlineKeyboardButton(text = text3, callback_data = "command_reminder_return")
    markup.add(exit_button)
    mess = bot.send_message(message.chat.id, "🔔 *" + text1 + ":*\n\n" + text2 + ": _" + str(number) + "_", reply_markup = markup, parse_mode= 'Markdown')
    database.register_last_message(mess)
    database.set_current_state(message, 'reminder')

# handle reminder content setting/editing
def command_reminder_set(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    state = database.get_current_state(message)
    state_splitted = state.split('_')
    if 'reminder_manage_menu_edit_content_' in state:
        if state_splitted[-1] == 'waiting':
            state_splitted.append(message.text)
        if(len(state_splitted) > 7):
            text1 = database.get_message_text(message, 'reminder')
            text2 = database.get_message_text(message, 'reminder_manage_button')
            text3 = "🔔" + database.get_message_text(message, 'command_reminder_manage_menu')
            text4 = database.get_message_text(message, 'command_reminder_manage_menu_edit_date')
            
            text5 = database.get_message_text(message, 'command_reminder_update_correct')
            text6 = database.get_message_text(message, 'content')
            text7 = database.get_message_text(message, 'date')
            markup = telebot.types.InlineKeyboardMarkup()
            text8 = database.get_message_text(message, 'return')
            return_button = telebot.types.InlineKeyboardButton(text = text8, callback_data = "command_reminder_return")
            markup.add(return_button)
            mess = bot.send_message(message.chat.id, "🔔 *" + text1 + " > " + text2 + " > " + text3 + " > " + text4 + ":*\n\n" + text5 + "\n" + text6 + ": _" + state_splitted[-1] + "_\n" + text7 + ": _" + database.get_reminder_rowid(state_splitted[-3])[0] + "_", reply_markup=markup, parse_mode='Markdown')
            database.register_last_message(mess)
            database.edit_reminder_content(message, state_splitted[-3], state_splitted[-1])
            return
        text1 = database.get_message_text(message, 'reminder')
        text2 = database.get_message_text(message, 'reminder_manage_button')
        text3 = "🔔" + database.get_message_text(message, 'command_reminder_manage_menu')
        text4 = database.get_message_text(message, 'command_reminder_manage_menu_edit_date')
        
        text5 = database.get_message_text(message, 'command_reminder_set')
        mess = bot.send_message(message.chat.id, "🔔 *" + text1 + " > " + text2 + " > " + text3 + " > " + text4 + ":*\n\n" + text5 + ":", parse_mode='Markdown')
        database.register_last_message(mess)
        database.set_current_state(message, state + '_waiting')
        return
    text1 = database.get_message_text(message, 'reminder')
    text2 = database.get_message_text(message, 'reminder_set_button')
    text3 = database.get_message_text(message, 'command_reminder_set')
    mess = bot.send_message(message.chat.id, "🔔 *" + text1 + " > " + text2 + ":*\n\n" + text3 + ":", parse_mode='Markdown')
    database.register_last_message(mess)
    database.set_current_state(message, 'reminder_set')

# handle reminder date setting/editing
def command_reminder_set_date(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    state = database.get_current_state(message)
    state_splitted = state.split('_')
    if 'reminder_manage_menu_edit_date_' in state:
        if len(state_splitted) > 7:
            try:
                date = datetime.strptime(str(message.text), '%Y-%m-%d %H:%M').strftime('%Y-%m-%d %H:%M')
            except:
                text1 = database.get_message_text(message, 'reminder')
                text2 = database.get_message_text(message, 'reminder_manage_button')
                text3 = "🔔" + database.get_message_text(message, 'command_reminder_manage_menu')
                text4 = database.get_message_text(message, 'command_reminder_manage_menu_edit_date')
                text5 = database.get_message_text(message, 'command_reminder_set_date_wrong')
                text6 = database.get_message_text(message, 'command_reminder_set_date')
                mess = bot.send_message(message.chat.id, "🔔 *" + text1 + " > " + text2 + " > " + text3 + " > " + text4 + ":*\n\n" + text5 + "\n" + text6 + ":", parse_mode='Markdown')
                database.register_last_message(mess)
            else:
                text1 = database.get_message_text(message, 'reminder')
                text2 = database.get_message_text(message, 'reminder_manage_button')
                text3 = "🔔" + database.get_message_text(message, 'command_reminder_manage_menu')
                text4 = database.get_message_text(message, 'command_reminder_manage_menu_edit_date')
                text5 = database.get_message_text(message, 'command_reminder_update_correct')
                text6 = database.get_message_text(message, 'content')
                text7 = database.get_message_text(message, 'date')
                markup = telebot.types.InlineKeyboardMarkup()
                text8 = database.get_message_text(message, 'return')
                return_button = telebot.types.InlineKeyboardButton(text = text8, callback_data = "command_reminder_return")
                markup.add(return_button)
                mess = bot.send_message(message.chat.id, "🔔 *" + text1 + " > " + text2 + " > " + text3 + " > " + text4 + ":*\n\n" + text5 + "\n" + text6 + ": _" + database.get_reminder_rowid(state_splitted[-2])[1] + "_\n" + text7 + ": _" + date + "_", reply_markup=markup, parse_mode='Markdown')
                database.register_last_message(mess)
                database.edit_reminder_date(message, state_splitted[-2], date)
        else:
            text1 = database.get_message_text(message, 'reminder')
            text2 = database.get_message_text(message, 'reminder_manage_button')
            text3 = "🔔" + database.get_message_text(message, 'command_reminder_manage_menu')
            text4 = database.get_message_text(message, 'command_reminder_manage_menu_edit_date')
            text5 = database.get_message_text(message, 'command_reminder_set_date')
            mess = bot.send_message(message.chat.id, "🔔 *" + text1 + " > " + text2 + " > " + text3 + " > " + text4 + ":*\n\n" + text5 + ":", parse_mode='Markdown')
            database.register_last_message(mess)
            database.set_current_state(message, state + "_waiting")
        return
    if len(state_splitted) > 2:
        try:
            date = datetime.strptime(str(message.text), '%Y-%m-%d %H:%M').strftime('%Y-%m-%d %H:%M')
        except:
            text1 = database.get_message_text(message, 'reminder')
            text2 = database.get_message_text(message, 'reminder_set_button')
            text3 = database.get_message_text(message, 'command_reminder_set_date_wrong')
            text4 = database.get_message_text(message, 'command_reminder_set_date')
            mess = bot.send_message(message.chat.id, "🔔 *" + text1 + " > " + text2 + ":*\n\n" + text3 + "\n" + text4 + ":", parse_mode='Markdown')
            database.register_last_message(mess)
        else:
            text1 = database.get_message_text(message, 'reminder')
            text2 = database.get_message_text(message, 'reminder_set_button')
            text3 = database.get_message_text(message, 'command_reminder_set_correct')
            text4 = database.get_message_text(message, 'content')
            text5 = database.get_message_text(message, 'date')
            markup = telebot.types.InlineKeyboardMarkup()
            text6 = database.get_message_text(message, 'return')
            return_button = telebot.types.InlineKeyboardButton(text = text6, callback_data = "command_reminder_return")
            markup.add(return_button)
            mess = bot.send_message(message.chat.id, "🔔 *" + text1 + " > " + text2 + ":*\n\n" + text3 + "\n" + text4 + ": _" + state_splitted[-1] + "_\n" + text5 + ": _" + date + "_", reply_markup=markup, parse_mode='Markdown')
            database.register_last_message(mess)
            database.set_current_state(message, 'reminder_set_correct')
            database.set_reminder(message, date, state_splitted[-1])
    else:
        text1 = database.get_message_text(message, 'reminder')
        text2 = database.get_message_text(message, 'reminder_set_button')
        text3 = database.get_message_text(message, 'command_reminder_set_date')
        mess = bot.send_message(message.chat.id, "🔔 *" + text1 + " > " + text2 + ":*\n\n" + text3 + ":", parse_mode='Markdown')
        database.register_last_message(mess)
        database.set_current_state(message, state + "_" + str(message.text))

def command_reminder_manage(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text1 = database.get_message_text(message, 'reminder')
    text2 = database.get_message_text(message, 'reminder_manage_button')
    text3 = database.get_message_text(message, 'command_reminder_manage')
    markup = telebot.types.InlineKeyboardMarkup()
    number, reminders = database.get_reminders(message)
    for i in range(number):
        reminder_button = telebot.types.InlineKeyboardButton(text = reminders[i][2], callback_data = 'echo_reminder_manage_menu_' + str(reminders[i][0]))
        markup.add(reminder_button)
    text4 = database.get_message_text(message, 'return')
    return_button = telebot.types.InlineKeyboardButton(text = text4, callback_data = "command_reminder_return")
    markup.add(return_button)
    mess = bot.send_message(message.chat.id, "🔔 *" + text1 + " > " + text2 + ":*\n\n" + text3 + ":", reply_markup = markup, parse_mode='Markdown')
    database.register_last_message(mess)
    database.set_current_state(message, 'reminder_manage')

def command_reminder_manage_menu(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text1 = database.get_message_text(message, 'reminder')
    text2 = database.get_message_text(message, 'reminder_manage_button')
    text3 = "🔔" + database.get_message_text(message, 'command_reminder_manage_menu')
    text4 = database.get_message_text(message, 'content')
    text5 = database.get_message_text(message, 'date')
    text6 = database.get_message_text(message, 'command_reminder_manage_menu_edit_content')
    text7 = database.get_message_text(message, 'command_reminder_manage_menu_edit_date')
    text8 = database.get_message_text(message, 'command_reminder_manage_menu_delete')
    text9 = database.get_message_text(message, 'return')
    state = int(database.get_current_state(message).split('_')[-1])
    markup = telebot.types.InlineKeyboardMarkup()
    edit_content_button = telebot.types.InlineKeyboardButton(text = text6, callback_data = "command_reminder_manage_menu_edit_content_" + str(state))
    markup.add(edit_content_button)
    edit_date_button = telebot.types.InlineKeyboardButton(text = text7, callback_data = "command_reminder_manage_menu_edit_date_" + str(state))
    markup.add(edit_date_button)
    delete_button = telebot.types.InlineKeyboardButton(text = text8, callback_data = "command_reminder_manage_menu_delete_" + str(state))
    markup.add(delete_button)
    return_button = telebot.types.InlineKeyboardButton(text = text9, callback_data = "command_reminder_return")
    markup.add(return_button)
    number, reminders = database.get_reminders(message)
    reminder = 0
    for i in range(len(reminders)):
        if reminders[i][0] == state:
            reminder = i
            break
    mess = bot.send_message(message.chat.id, "🔔 *" + text1 + " > " + text2 + " > " + text3 + ":*\n\n" + text4 + ": _" + reminders[reminder][1] + "_\n" + text5 + ": _" + reminders[reminder][2] + "_", reply_markup = markup, parse_mode='Markdown')
    database.register_last_message(mess)

def command_reminder_return(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text = database.get_message_text(message, 'command_reminder_return')
    mess = bot.send_message(message.chat.id, text, parse_mode='Markdown')
    database.register_last_message(mess)