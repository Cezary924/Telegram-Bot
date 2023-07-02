import random

import database

# handle /crystalball command
def command_crystalball(message, bot):
    number = crystalball()
    text = database.get_message_text(message, 'command_crystalball_' + str(number))
    mess = bot.send_message(message.chat.id, "🔮 *" + text + "*", parse_mode= 'Markdown')
    database.register_last_message(mess)

# get random int [1, 3]
def crystalball():
    return random.choice([1, 2, 3])