import telebot, requests
import func

# open file containing bot name and read from it
bot_name = func.read_file("bot_name.txt", "../files/bot_name.txt")
bot_name = str(bot_name[0])

# open file containing GitHub username and read from it
github_username = func.read_file("github_username.txt", "../files/github_username.txt")
github_username = str(github_username[0])

# open file containing GitHub repo and read from it
github_repo = func.read_file("github_repo.txt", "../files/github_repo.txt")
github_repo = str(github_repo[0])

# handle /start command
def command_start(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    help_button = telebot.types.InlineKeyboardButton(text = "📃 Lista komend", callback_data = "command_help")
    markup.add(help_button)
    about_button = telebot.types.InlineKeyboardButton(text = "ℹ️ Informacje o Bocie", callback_data = "command_about")
    markup.add(about_button)
    bot.send_message(message.chat.id, "Cześć, z tej strony " + bot_name + "! 🤖👋", reply_markup = markup)

# handle /help command
def command_help(message, bot):
    bot.send_message(message.chat.id, "*📃 Oto lista dostępnych poleceń*\n\n" + 
                     "/start - _🤖 Zaczęcie rozmowy z Botem_\n" + 
                     "/help - _📃 Strona pomocy z listą dostępnych komend_\n" +
                     "/contact - _🧑‍🔬 Informacje o drogach kontaktu z Administratorem_\n" +
                     "/report - _📨 Wysłanie bezzwrotnego zgłoszenia do Administratora_\n" +
                     "/about - _ℹ️ Informacje o Bocie_\n" +
                     "/tiktok - _🎵 Pobieranie wideo z serwisu TikTok_\n" +
                     "/twitter - _🐦 Pobieranie wideo z serwisu Twitter_", parse_mode= 'Markdown')

# handle /contact command
def command_contact(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    report_button = telebot.types.InlineKeyboardButton(text = "✉️ Zgłoszenie do Administratora", callback_data = "command_report")
    markup.add(report_button)
    bot.send_message(message.chat.id, "Aby skontaktować się z Administratorem, napisz bezpośrednio do @Cezary924 lub wyślij bezzwrotną wiadomość-zgłoszenie 📨", reply_markup = markup)

# handle /report command
def command_report(message, bot):
    bot.send_message(message.chat.id, "Napisz wiadomość-zgłoszenie do Administratora, a ja ją przekażę 🫡")

# handle /delete_data command
def command_delete_data(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    yes_button = telebot.types.InlineKeyboardButton(text = "✅ Tak", callback_data = "command_delete_data_yes")
    markup.add(yes_button)
    no_button = telebot.types.InlineKeyboardButton(text = "❌ Nie", callback_data = "command_delete_data_no")
    markup.add(no_button)
    bot.send_message(message.chat.id, "Czy na pewno chcesz usunąć wszystkie dane zgromadzone o Tobie przez Bota?"
                     + " Utracisz przyznane uprawnienia. Funkcje oferowane przez Bota będą wymagały ponownej"
                     + " konfiguracji. Operacji tej nie będzie można cofnąć.", 
                     reply_markup = markup)
def command_delete_data_yes(message, bot):
    bot.send_message(message.chat.id, "Operacja usuwania danych przebiegła pomyślnie.")
def command_delete_data_no(message, bot):
    bot.send_message(message.chat.id, "Operacja usuwania danych została anulowana.")

# handle /about command
def command_about(message, bot, ver):
    def info_about_version(ver):
        resp = requests.request("GET", "https://api.github.com/repos/" + github_username + "/" + github_repo + "/commits?per_page=10000")
        online_ver = len(resp.json())
        if ver > online_ver:
            return "Beta"
        elif ver == online_ver:
            return "Stablina, aktualna"
        else:
            return "Stablina, przestarzała (" + str(online_ver) + ")"

    bot.send_message(message.chat.id, "*ℹ️ Informacje o Bocie*\n\n"
                    + "*" + bot_name + "*\n"
                    + "Opis: _Wielofunkcyjny bot na platformie Telegram_\n"
                    + "Autor: _@" + github_username + "_\n"
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
