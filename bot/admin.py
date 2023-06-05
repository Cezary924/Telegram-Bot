import telebot, os, signal, sys, subprocess
import database, basic_commands

# handle /admin command
def command_admin(message, bot, update):
    markup = telebot.types.InlineKeyboardMarkup()
    if update:
        update_bot_button = telebot.types.InlineKeyboardButton(text = "⬇️ Aktualizacja Bota 🤖", callback_data = "command_admin_update_bot")
        markup.add(update_bot_button)
    shutdown_bot_button = telebot.types.InlineKeyboardButton(text = "📴 Wyłączenie Bota 🤖", callback_data = "command_admin_shutdown_bot")
    markup.add(shutdown_bot_button)
    shutdown_device_button = telebot.types.InlineKeyboardButton(text = "📴 Wyłączenie urządzenia 🖥️", callback_data = "command_admin_shutdown_device")
    markup.add(shutdown_device_button)
    restart_bot_button = telebot.types.InlineKeyboardButton(text = "🔁 Restart Bota 🤖", callback_data = "command_admin_restart_bot")
    markup.add(restart_bot_button)
    restart_device_button = telebot.types.InlineKeyboardButton(text = "🔁 Restart urządzenia 🖥️", callback_data = "command_admin_restart_device")
    markup.add(restart_device_button)
    exit_button = telebot.types.InlineKeyboardButton(text = "❌ Wyjście", callback_data = "command_admin_return")
    markup.add(exit_button)
    mess = bot.send_message(message.chat.id, "🛠️ *Panel Administratora:*\n\nWybierz zadanie z podanych",
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)

# handle bot shutdown command
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

# handle device shutdown command
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

# handle bot restart
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

# handle device restart
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

# handle bot update
def command_admin_update_bot(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    yes_button = telebot.types.InlineKeyboardButton(text = "✅ Tak", callback_data = "command_admin_update_bot_yes")
    markup.add(yes_button)
    no_button = telebot.types.InlineKeyboardButton(text = "❌ Nie", callback_data = "command_admin_return")
    markup.add(no_button)
    mess = bot.send_message(message.chat.id, "🤖 *Aktualizacja Bota:*\n\nCzy na pewno chcesz zaktualizować Bota?", 
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_admin_update_bot_yes(message, bot):
    mess = bot.send_message(message.chat.id, "🤖 *Aktualizacja Bota...*", 
                     parse_mode = 'Markdown')
    #database.register_last_message(mess)
    proc = subprocess.run(["git", "pull", os.getcwdb()[:(0 - int(len('bot/')))]], capture_output=True)
    if proc.returncode != 0:
        bot.send_message(message.chat.id, "🤖 *Aktualizacja Bota:*\n\nWystąpił błąd podczas wykonywania komendy _git pull_ ❌", 
                     parse_mode = 'Markdown')
    else:
        if 'Already up to date' in proc.stdout.decode("utf-8"):
            bot.send_message(message.chat.id, "🤖 *Aktualizacja Bota:*\n\nNie ma dostępnej aktualizacji - najnowsza wersja jest już pobrana 😊", 
                     parse_mode = 'Markdown')
        else:
            bot.send_message(message.chat.id, "🤖 *Aktualizacja Bota:*\n\nPrzy pomocy komendy _git pull_ pobrano zmiany ze zdalnego repozytorium ⬇️", 
                     parse_mode = 'Markdown')
    #basic_commands.delete_previous_bot_message(mess, bot)