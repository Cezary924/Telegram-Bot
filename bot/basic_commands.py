import telebot, requests
from urllib.parse import parse_qs, urlparse

import func, database

# open file containing bot name and read from it
bot_name = func.read_file("bot_name.txt", "../files/bot_name.txt")
bot_name = str(bot_name[0])
if func.suffix == 1:
    bot_name = "Beta" + bot_name

# open file containing GitHub username and read from it
github_username = func.read_file("github_username.txt", "../files/github_username.txt")
github_username = str(github_username[0])

# open file containing GitHub repo and read from it
github_repo = func.read_file("github_repo.txt", "../files/github_repo.txt")
github_repo = str(github_repo[0])

# get commits number from GitHub
def info_about_version(ver):
    response = requests.get("https://api.github.com/repos/" + github_username + "/" + github_repo + "/commits?per_page=1")
    if response.status_code != 200:
        return (0, "Błąd. Spróbuj później.")
    online_ver = int(parse_qs(urlparse(response.links["last"]["url"]).query)["page"][0])
    if ver > online_ver:
        return (online_ver, "Beta")
    elif ver == online_ver:
        return (online_ver, "Stablina, aktualna")
    else:
        return (online_ver, "Stablina, przestarzała (" + str(online_ver) + ")")

# delete previously sent message by bot
def delete_previous_bot_message(message, bot):
    # func.print_log("Delete previous message: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
    bot.delete_message(message.chat.id, database.get_last_message(message))

# handle /start command
def command_start(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    help_button = telebot.types.InlineKeyboardButton(text = "📃 Lista komend", callback_data = "command_help")
    markup.add(help_button)
    about_button = telebot.types.InlineKeyboardButton(text = "ℹ️ Informacje o Bocie", callback_data = "command_about")
    markup.add(about_button)
    mess = bot.send_message(message.chat.id, "*👋 Cześć!*\n\nZ tej strony " + bot_name + "! 🤖",
                      parse_mode = 'Markdown', reply_markup = markup)
    if database.guest_check(message, bot) != True:
        return
    database.save_current_state(message, "start")
    database.register_last_message(mess)

# handle /help command
def command_help(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    main_button = telebot.types.InlineKeyboardButton(text = "🤖 Ogólne", callback_data = "command_help_main")
    markup.add(main_button)
    downloader_button = telebot.types.InlineKeyboardButton(text = "⬇️ Pobieranie wideo", callback_data = "command_help_downloader")
    markup.add(downloader_button)
    contact_button = telebot.types.InlineKeyboardButton(text = "☎️ Kontakt", callback_data = "command_help_contact")
    markup.add(contact_button)
    settings_button = telebot.types.InlineKeyboardButton(text = "⚙️ Ustawienia", callback_data = "command_help_settings")
    markup.add(settings_button)
    exit_button = telebot.types.InlineKeyboardButton(text = "❌ Wyjście", callback_data = "command_help_return")
    markup.add(exit_button)
    mess = bot.send_message(message.chat.id, "📃 *Pomoc:*\n\nWybierz interesującą Cię kategorię komend",
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_help_main(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    help_button = telebot.types.InlineKeyboardButton(text = "Powrót", callback_data = "command_help_return")
    markup.add(help_button)
    mess = bot.send_message(message.chat.id, "📃 *Pomoc > 🤖 Ogólne:*\n\n" + 
                     "/start - _🤖 Zaczęcie rozmowy z Botem_\n" + 
                     "/help - _📃 Strona pomocy z listą dostępnych komend_\n" +
                     "/about - _ℹ️ Informacje o Bocie_", parse_mode= 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_help_downloader(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    help_button = telebot.types.InlineKeyboardButton(text = "Powrót", callback_data = "command_help_return")
    markup.add(help_button)
    mess = bot.send_message(message.chat.id, "📃 *Pomoc > ⬇️ Pobieranie wideo:*\n\n" + 
                     "/tiktok - _🎵 Pobieranie wideo z serwisu TikTok_\n" +
                     "/twitter - _🐦 Pobieranie wideo z serwisu Twitter_", parse_mode= 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_help_contact(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    help_button = telebot.types.InlineKeyboardButton(text = "Powrót", callback_data = "command_help_return")
    markup.add(help_button)
    mess = bot.send_message(message.chat.id, "📃 *Pomoc > ☎️ Kontakt:*\n\n" + 
                     "/contact - _☎️ Informacje o drogach kontaktu z Administratorem_\n" +
                     "/report - _📨 Wysłanie bezzwrotnego zgłoszenia do Administratora_\n", parse_mode= 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_help_settings(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    help_button = telebot.types.InlineKeyboardButton(text = "Powrót", callback_data = "command_help_return")
    markup.add(help_button)
    mess = bot.send_message(message.chat.id, "📃 *Pomoc > ⚙️ Ustawienia:*\n\n" + 
                     "/deletedata - _🗑️ Usuń wszystkie zebrane od Ciebie dane_\n", parse_mode= 'Markdown', reply_markup = markup)
    database.register_last_message(mess)

# handle /contact command
def command_contact(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    report_button = telebot.types.InlineKeyboardButton(text = "📨 Zgłoszenie do Administratora", callback_data = "command_report")
    markup.add(report_button)
    mess = bot.send_message(message.chat.id, "☎️ *Kontakt:*\n\nAby skontaktować się z Administratorem, napisz bezpośrednio do @Cezary924 lub wyślij bezzwrotną wiadomość-zgłoszenie 📨", 
                     parse_mode = 'Markdown',
                     reply_markup = markup)
    database.register_last_message(mess)

# handle /report command
def command_report(message, bot):
    mess = bot.send_message(message.chat.id, "📨 *Zgłoszenie:*\n\nNapisz wiadomość-zgłoszenie do Administratora, a ja ją przekażę 🫡", parse_mode= 'Markdown')
    database.register_last_message(mess)

# handle /deletedata command
def command_deletedata(message, bot):
    markup = telebot.types.InlineKeyboardMarkup()
    yes_button = telebot.types.InlineKeyboardButton(text = "✅ Tak", callback_data = "command_deletedata_yes")
    markup.add(yes_button)
    no_button = telebot.types.InlineKeyboardButton(text = "❌ Nie", callback_data = "command_deletedata_no")
    markup.add(no_button)
    mess = bot.send_message(message.chat.id, "🗑️ *Usuwanie danych:*\n\nCzy na pewno chcesz usunąć wszystkie dane zgromadzone o Tobie przez Bota?"
                     + " Utracisz przyznane uprawnienia. Funkcje oferowane przez Bota będą wymagały ponownej"
                     + " konfiguracji. Operacji tej nie będzie można cofnąć.", 
                     parse_mode = 'Markdown', reply_markup = markup)
    database.register_last_message(mess)
def command_deletedata_yes(message, bot):
    mess = bot.send_message(message.chat.id, "Operacja usuwania danych przebiegła pomyślnie.")
    database.register_last_message(mess)
def command_deletedata_no(message, bot):
    mess = bot.send_message(message.chat.id, "Operacja usuwania danych została anulowana.")
    database.register_last_message(mess)

# handle /about command
def command_about(message, bot, ver):
    mess = bot.send_message(message.chat.id, "*ℹ️ Informacje o Bocie:*\n\n"
                    + "*" + bot_name + "*\n"
                    + "Opis: _Wielofunkcyjny bot na platformie Telegram_\n"
                    + "Autor: _@" + github_username + "_\n"
                    + "Wersja: _" + str(ver) + "_\n"
                    + "Status wersji: _" + info_about_version(ver)[1] + "_\n"
                    + "Rok powstania: _2023_\n"
                    + "Lata rozwijania: _2023-nadal_", parse_mode= 'Markdown')
    database.register_last_message(mess)

# handle /tiktok command
def command_tiktok(message, bot):
    mess = bot.send_message(message.chat.id, "🎵 *TikTok*\n\nAby pobrać wideo z serwisu TikTok wystarczy, że wyślesz mi do niego link 🔗", parse_mode= 'Markdown')
    database.register_last_message(mess)

# handle /twitter command
def command_twitter(message, bot):
    mess = bot.send_message(message.chat.id, "🐦 *Twitter*\n\nAby pobrać wideo z serwisu Twitter wystarczy, że wyślesz mi do niego link 🔗", parse_mode= 'Markdown')
    database.register_last_message(mess)

# handle /tumblr command
def command_tumblr(message, bot):
    mess = bot.send_message(message.chat.id, "📄 *Tumblr*\n\nAby pobrać wideo z serwisu Tumblr wystarczy, że wyślesz mi do niego link 🔗", parse_mode= 'Markdown')
    database.register_last_message(mess)