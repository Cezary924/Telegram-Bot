import telebot, time
from threading import Thread
from datetime import datetime

import database

def check_reminders() -> None:
    while True:
        t = datetime.utcnow()
        sleeptime = 60 - (t.second + t.microsecond/1000000.0)
        time.sleep(sleeptime)
        print(datetime.utcnow())

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

def command_reminder_set(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text1 = database.get_message_text(message, 'reminder')
    text2 = database.get_message_text(message, 'reminder_set_button')
    text3 = database.get_message_text(message, 'command_reminder_set')
    mess = bot.send_message(message.chat.id, "🔔 *" + text1 + " > " + text2 + ":*\n\n" + text3 + ":", parse_mode='Markdown')
    database.register_last_message(mess)

def command_reminder_manage(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text1 = database.get_message_text(message, 'reminder')
    text2 = database.get_message_text(message, 'reminder_manage_button')
    text3 = database.get_message_text(message, 'command_reminder_manage')
    mess = bot.send_message(message.chat.id, "🔔 *" + text1 + " > " + text2 + ":*\n\n" + text3 + ":", parse_mode='Markdown')
    database.register_last_message(mess)

def command_reminder_return(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    text = database.get_message_text(message, 'command_reminder_return')
    mess = bot.send_message(message.chat.id, text, parse_mode='Markdown')
    database.register_last_message(mess)