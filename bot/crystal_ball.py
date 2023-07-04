import random

import database

# handle /crystalball command
def command_crystalball(message, bot):
    number1, number2 = crystalball()
    text = database.get_message_text(message, 'command_crystalball_' + str(number1) + "_" + str(number2))
    if number1 == 1:
        text = text + " ✅"
    elif number1 == 2:
        text = text + " ❔"
    else:
        text = text + " ❌"
    mess = bot.send_message(message.chat.id, "🔮 *" + text + "*", parse_mode= 'Markdown')
    database.register_last_message(mess)

# get random int [1, 3] & another random int [1, 5]
def crystalball():
    return random.choice([1, 2, 3]), random.choice([1, 2, 3, 4, 5])