import telebot, requests

# handle /start command
def command_start(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    help_button = telebot.types.InlineKeyboardButton(text = "Lista komend 📃", callback_data = "command_help")
    markup.add(help_button)
    about_button = telebot.types.InlineKeyboardButton(text = "Informacje o bocie ℹ️", callback_data = "command_about")
    markup.add(about_button)
    bot.send_message(message.chat.id, "Cześć, z tej strony Cezary924Bot! 🤖👋", reply_markup = markup)

# handle /help command
def command_help(message, bot):
    bot.send_message(message.chat.id, "*Oto lista dostępnych poleceń 📃*\n\n" + 
                     "/start - _Zaczęcie rozmowy z botem 🤖_\n" + 
                     "/help - _Strona pomocy z listą dostępnych komend 📃_\n" +
                     "/about - _Informacje o bocie ℹ️_\n" +
                     "/tiktok - _Pobieranie wideo z serwisu TikTok 🎵_\n" +
                     "/twitter - _Pobieranie wideo z serwisu Twitter 🐦_", parse_mode= 'Markdown')

# handle /about command
def command_about(message, bot, ver):
    def info_about_version(ver):
        resp = requests.request("GET", "https://api.github.com/repos/Cezary924/Cezary924-Telegram-Bot/commits?per_page=10000")
        online_ver = len(resp.json())
        if ver > online_ver:
            return "Beta"
        elif ver == online_ver:
            return "Stablina, aktualna"
        else:
            return "Stablina, przestarzała (" + str(online_ver) + ")"

    bot.send_message(message.chat.id, "*Informacje o bocie ℹ️*\n\n"
                    + "*Cezary924Bot*\n"
                    + "Opis: _Wielofunkcyjny bot na platformie Telegram_\n"
                    + "Autor: _@Cezary924_\n"
                    + "Rok powstania: _2023_\n"
                    + "Wersja: _" + str(ver) + "_\n"
                    + "Status wersji: _" + info_about_version(ver) + "_\n"
                    + "Lata rozwijania: _2023-nadal_", parse_mode= 'Markdown')
    
# handle /tiktok command
def command_tiktok(message, bot):
    bot.send_message(message.chat.id, "Aby pobrać wideo z serwisu TikTok wystarczy, że wyślesz mi do niego link 🎵")

# handle /twitter command
def command_twitter(message, bot):
    bot.send_message(message.chat.id, "Aby pobrać wideo z serwisu Twitter wystarczy, że wyślesz mi do niego link 🐦")
