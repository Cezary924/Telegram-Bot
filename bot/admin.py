import telebot, os, signal, sys, subprocess
import database

# handle /admin command
def command_admin(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    shutdown_bot_button = telebot.types.InlineKeyboardButton(text = "🤖 Wyłączenie Bota", callback_data = "command_admin_shutdown_bot")
    markup.add(shutdown_bot_button)
    shutdown_device_button = telebot.types.InlineKeyboardButton(text = "🖥️ Wyłączenie urządzenia", callback_data = "command_admin_shutdown_device")
    markup.add(shutdown_device_button)
    restart_bot_button = telebot.types.InlineKeyboardButton(text = "🤖 Restart Bota", callback_data = "command_admin_restart_bot")
    markup.add(restart_bot_button)
    restart_device_button = telebot.types.InlineKeyboardButton(text = "🖥️ Restart urządzenia", callback_data = "command_admin_restart_device")
    markup.add(restart_device_button)
    exit_button = telebot.types.InlineKeyboardButton(text = "❌ Wyjście", callback_data = "command_admin_return")
    markup.add(exit_button)
    mess = bot.send_message(message.chat.id, "🛠️ *Panel Administratora:*\n\nWybierz zadanie z podanych",
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)

def command_admin_shutdown_bot(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    yes_button = telebot.types.InlineKeyboardButton(text = "✅ Tak", callback_data = "command_admin_shutdown_bot_yes")
    markup.add(yes_button)
    no_button = telebot.types.InlineKeyboardButton(text = "❌ Nie", callback_data = "command_admin_return")
    markup.add(no_button)
    mess = bot.send_message(message.chat.id, "🤖 *Wyłączenie Bota:*\n\nCzy na pewno chcesz wyłączyć skrypt Bota?", 
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_admin_shutdown_bot_yes(message, bot):
    bot.send_message(message.chat.id, "🤖 *Wyłączenie Bota...*", 
                     parse_mode = 'Markdown')
    os.kill(os.getpid(), signal.SIGINT)
def command_admin_shutdown_device(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    yes_button = telebot.types.InlineKeyboardButton(text = "✅ Tak", callback_data = "command_admin_shutdown_device_yes")
    markup.add(yes_button)
    no_button = telebot.types.InlineKeyboardButton(text = "❌ Nie", callback_data = "command_admin_return")
    markup.add(no_button)
    mess = bot.send_message(message.chat.id, "🖥️ *Wyłączenie urządzenia:*\n\nCzy na pewno chcesz wyłączyć urządzenie, na którym uruchomiony jest Bot?", 
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_admin_shutdown_device_yes(message, bot):
    bot.send_message(message.chat.id, "🖥️ *Wyłączenie urządzenia...*", 
                     parse_mode = 'Markdown')
    os.system("shutdown /s /t 1")

def command_admin_restart_bot(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    yes_button = telebot.types.InlineKeyboardButton(text = "✅ Tak", callback_data = "command_admin_restart_bot_yes")
    markup.add(yes_button)
    no_button = telebot.types.InlineKeyboardButton(text = "❌ Nie", callback_data = "command_admin_return")
    markup.add(no_button)
    mess = bot.send_message(message.chat.id, "🤖 *Restart Bota:*\n\nCzy na pewno chcesz uruchomić ponownie Bota?", 
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_admin_restart_bot_yes(message, bot):
    bot.send_message(message.chat.id, "🤖 *Restart Bota...*", 
                     parse_mode = 'Markdown')
    subprocess.call(["python", os.path.join(sys.path[0], __file__)] + sys.argv[1:])
def command_admin_restart_device(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    yes_button = telebot.types.InlineKeyboardButton(text = "✅ Tak", callback_data = "command_admin_restart_device_yes")
    markup.add(yes_button)
    no_button = telebot.types.InlineKeyboardButton(text = "❌ Nie", callback_data = "command_admin_return")
    markup.add(no_button)
    mess = bot.send_message(message.chat.id, "🖥️ *Restart urządzenia:*\n\nCzy na pewno chcesz uruchomić ponownie urządzenie, na którym uruchomiony jest Bot?", 
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_admin_restart_device_yes(message, bot):
    bot.send_message(message.chat.id, "🖥️ *Restart urządzenia...*", 
                     parse_mode = 'Markdown')
    os.system("shutdown /r /t 1")