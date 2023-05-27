import telebot
import database

# handle /admin command
def command_admin(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    restart_bot_button = telebot.types.InlineKeyboardButton(text = "🤖 Restart Bota", callback_data = "command_admin_restart_bot")
    markup.add(restart_bot_button)
    restart_device_button = telebot.types.InlineKeyboardButton(text = "🖥️ Restart urządzenia", callback_data = "command_admin_restart_device")
    markup.add(restart_device_button)
    exit_button = telebot.types.InlineKeyboardButton(text = "❌ Wyjście", callback_data = "command_admin_return")
    markup.add(exit_button)
    mess = bot.send_message(message.chat.id, "🛠️ *Panel Administratora:*\n\nWybierz zadanie z podanych",
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_admin_restart_bot(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    yes_button = telebot.types.InlineKeyboardButton(text = "✅ Tak (niezaimplementowane)", callback_data = "")
    markup.add(yes_button)
    no_button = telebot.types.InlineKeyboardButton(text = "❌ Nie", callback_data = "command_admin_return")
    markup.add(no_button)
    mess = bot.send_message(message.chat.id, "🤖 *Restart Bota:*\n\nCzy na pewno chcesz uruchomić ponownie Bota?", 
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_admin_restart_device(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    yes_button = telebot.types.InlineKeyboardButton(text = "✅ Tak (niezaimplementowane)", callback_data = "")
    markup.add(yes_button)
    no_button = telebot.types.InlineKeyboardButton(text = "❌ Nie", callback_data = "command_admin_return")
    markup.add(no_button)
    mess = bot.send_message(message.chat.id, "🤖 *Restart urządzenia:*\n\nCzy na pewno chcesz uruchomić ponownie urządzenie, na którym uruchomiony jest Bot?", 
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)