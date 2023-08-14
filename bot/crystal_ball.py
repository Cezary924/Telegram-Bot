import telebot, random

import database

# handle /crystalball command
def command_crystalball(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
    number1, number2 = crystalball()
    text1 = database.get_message_text(message, 'crystalball')
    text2 = database.get_message_text(message, 'command_crystalball_' + str(number1) + "_" + str(number2))
    if number1 == 1:
        text2 = text2 + " ✅"
    elif number1 == 2:
        text2 = text2 + " ❔"
    else:
        text2 = text2 + " ❌"
    mess = bot.send_message(message.chat.id, "🔮 *" + text1 + ":*\n\n" + text2, parse_mode= 'Markdown')
    database.register_last_message(mess)

# get random int [1, 3] & another random int [1, 5]
def crystalball() -> tuple[int, int]:
    return random.choice([1, 2, 3]), random.choice([1, 2, 3, 4, 5])