import telebot
import database

main_units = ['m', 'g', 's']
units_1 = {'mm': 1000, 'cm': 100, 'in': 39.37, 'dm': 10, 'ft': 3.281, 'm': 1, 'km': 0.001,  'mi': 0.000621371}
units_2 = {'mg': 1000, 'dag': 10, 'g': 1, 'oz': 0.03527396, 'lb': 0.00220462, 'kg': 0.001, 't': 0.000001}
units_3 = {'ms': 1000, 's': 1, 'min': 1/60, 'h': 1/3600, 'd': 1/86400, 'wk': 1/604800, 'mo': 1/2592000, 'yr': 1/31536000}

# check if the message contains any known unit
def check_message(message: telebot.types.Message) -> tuple[int, str, str]:
    text = message.text
    #-------------------------------------------------------
    text_test = text.replace(' ', '')
    units = sorted(list(units_1.keys()), key=len, reverse=True)
    unit = ''
    for element in units:
        if element in text_test:
            unit = element
            text_test = text_test.replace(element, '')
            break
    if text_test.replace('.', '').isdigit():
        return (1, unit, text_test)
    #-------------------------------------------------------
    text_test = text.replace(' ', '')
    units = sorted(list(units_2.keys()), key=len, reverse=True)
    unit = ''
    for element in units:
        if element in text_test:
            unit = element
            text_test = text_test.replace(element, '')
            break
    if text_test.replace('.', '').isdigit():
        return (2, unit, text_test)
    #-------------------------------------------------------
    text_test = text.replace(' ', '')
    units = sorted(list(units_3.keys()), key=len, reverse=True)
    unit = ''
    for element in units:
        if element in text_test:
            unit = element
            text_test = text_test.replace(element, '')
            break
    if text_test.replace('.', '').isdigit():
        return (3, unit, text_test)
    #-------------------------------------------------------
    return (0, '', '')

# get number with its unit to main unit
def get_to_main_unit(num: float, unit: str, x: int) -> float:
    if x == 1:
        return num/units_1[unit]
    elif x == 2:
        return num/units_2[unit]
    elif x == 3:
        return num/units_3[unit]

# change unit and send message to user
def change_unit(num: float, x: int) -> str:
    msg = ''
    if x == 1:
        for unit in list(units_1.keys()):
            _ = "{:g}".format(num * units_1[unit])
            msg = msg + "   " + telebot.telebot.formatting.hitalic(unit + ": ") + _ + "\n"
    elif x == 2:
        for unit in list(units_2.keys()):
            _ = "{:g}".format(num * units_2[unit])
            msg = msg + "   " + telebot.telebot.formatting.hitalic(unit + ": ") + _ + "\n"
    elif x == 3:
        for unit in list(units_3.keys()):
            _ = "{:g}".format(num * units_3[unit])
            msg = msg + "   " + telebot.telebot.formatting.hitalic(unit + ": ") + _ + "\n"
    return msg

# handle messages with known units
def message_handler(message: telebot.types.Message, bot: telebot.TeleBot):
    text1 = database.get_message_text(message, 'unitconverter')
    x, unit, num = check_message(message)
    _num = num
    try:
        num = float(num)
    except:
        text2 = database.get_message_text(message, 'error')
        mess = bot.send_message(message.chat.id, telebot.telebot.formatting.hbold(text1 + ":\n\n") + text2, parse_mode = 'html')
        database.register_last_message(mess)
    msg = database.get_message_text(message, 'error')
    if x > 0:
        if unit in main_units:
            msg = change_unit(num, x)
        else:
            num = get_to_main_unit(num, unit, x)
            msg = change_unit(num, x)
    text2 = _num + " " + unit + " =="
    mess = bot.send_message(message.chat.id, telebot.telebot.formatting.hbold(text1 + ":\n\n") + text2 + "\n" + msg[:-1], parse_mode = 'html')
    database.register_last_message(mess)