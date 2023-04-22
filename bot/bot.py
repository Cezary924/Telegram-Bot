import telebot, os, requests

# get path of directory containing bot script
dir = os.path.dirname(os.path.realpath(__file__)) + "/"

# change current working directory to 'dir'
os.chdir(dir)

# open file containing token and read from it
try:
    with open("../secret.txt") as f:
        token = f.readlines()
    f.close()
except OSError:
    print("Open error: Could not open the \'secret.txt\' file.")

# open file containing RapidAPI key and read from it
try:
    with open("../rapidapi.txt") as f:
        rapidapi = f.readlines()
    f.close()
except OSError:
    print("Open error: Could not open the \'rapidapi.txt\' file.")

# prepare token and key
token = str(token[0])
rapidapi = str(rapidapi[0])

# create bot instance
bot = telebot.TeleBot(token)

# handle callback queries
@bot.callback_query_handler(func=lambda call: True)
def test_callback(call):
    globals()[str(call.data)](call.message)

# handle /start command
@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.InlineKeyboardMarkup()
    help_button = telebot.types.InlineKeyboardButton(text = "Lista komend 📃", callback_data = "help")
    markup.add(help_button)
    bot.send_message(message.chat.id, "Cześć, z tej strony Cezary924Bot! 🤖👋", reply_markup = markup)

# handle /help command
@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id, "Oto lista dostępnych poleceń 📃:\n\n" + 
                     "/start - Zaczęcie rozmowy z botem 🤖\n" + 
                     "/help - Lista dostępnych komend 📃")

# handle TikTok urls
@bot.message_handler(func=lambda message: message.content_type == 'text' and 'tiktok.com' in message.text and 'http' in message.text)
def echo_tiktok(message):

    url = "https://tiktok-full-info-without-watermark.p.rapidapi.com/vid/index"
    querystring = {"url":message.text}
    headers = {
        "X-RapidAPI-Key": rapidapi,
        "X-RapidAPI-Host": "tiktok-full-info-without-watermark.p.rapidapi.com"
    }
    bot.send_message(message.chat.id, "Przetwarzanie linku z TikToka... ⏳")
    response = requests.request("GET", url, headers=headers, params=querystring)
    if response.status_code != 200:
        bot.send_message(message.chat.id, "Niestety, pobranie filmiku z TikToka nie jest teraz możliwe 😞")
        return
    vid_url = response.json()['video'][0]
    response = requests.request("GET", vid_url, headers=headers, params=querystring)
    if response.status_code != 200:
        bot.send_message(message.chat.id, "Niestety, pobranie filmiku z TikToka nie jest teraz możliwe 😞")
        return
    vid_name = str(message.chat.id) + str(message.message_id) + ".mp4"
    try:
        with open(vid_name, "wb") as f:
            f.write(response.content)
            f.close()
    except OSError:
        print("Open error: Could not open the \'.mp4\' file.")
    bot.send_video(message.chat.id, open(vid_name, 'rb'))
    os.remove(vid_name)

# handle any other message
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.send_message(message.chat.id, "Niestety, nie rozumiem Twojej wiadomości... 💔")

# infinite loop
print("Cezary924-Telegram-Bot has been started.")
bot.infinity_polling()
