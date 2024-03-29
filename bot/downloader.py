import telebot
import database, func

# check URL scheme & URL hostname
def check_url(message: telebot.types.Message, scheme: str, hostname: str):
    return func.check_url(message, scheme, hostname)

# send message at the beginning of the downloading process
def send_start_message(bot: telebot.TeleBot, message: telebot.types.Message, downloader_name: str) -> None:
    text1 = database.get_message_text(message, downloader_name)
    text2 = database.get_message_text(message, 'downloader_start')
    bot.send_message(message.chat.id, text1 + text2, parse_mode= 'Markdown')

# send message in the middle of the downloading process
def send_processing_message(bot: telebot.TeleBot, message: telebot.types.Message, downloader_name: str) -> None:
    text1 = database.get_message_text(message, downloader_name)
    text2 = database.get_message_text(message, 'downloader_processing')
    bot.send_message(message.chat.id, text1 + text2, parse_mode= 'Markdown')

# send message about error during the downloading process
def send_error_message(bot: telebot.TeleBot, message: telebot.types.Message, downloader_name: str) -> None:
    text1 = database.get_message_text(message, downloader_name)
    text2 = database.get_message_text(message, 'downloader_error')
    bot.send_message(message.chat.id, text1 + text2, parse_mode= 'Markdown')