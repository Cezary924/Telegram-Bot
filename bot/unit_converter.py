import telebot

main_units = ['m', 'g', 's']
units_1 = {'cm': 100, 'dm': 10, 'km': 0.001, 'mm': 1000, 'in': 39.37, 'ft': 3.281, 'mi': 0.000621371, 'm': 1}
units_2 = {'dag': 10, 'lb': 0.00220462, 'kg': 0.001, 'oz': 0.03527396, 't': 0.000001, 'mg': 1000, 'g': 1}
units_3 = {'min': 1/60, 'wk': 1/604800, 'yr': 1/31536000, 'mo': 1/2592000, 'ms': 1000, 'd': 1/86400, 'h': 1/3600, 's': 1}

# check if the message contains any known unit
def check_message(message: telebot.types.Message) -> tuple[int, str]:
    text = message.text
    #-------------------------------------------------------
    text_test = text.replace(' ', '')
    units = ['cm', 'dm', 'km', 'mm', 'in', 'ft', '\"', '”', 'M', 'm']
    unit = ''
    for element in units:
        if element in text_test:
            unit = element
            text_test = text_test.replace(element, '')
            break
    if text_test.replace('.', '').isdigit():
        return (1, unit)
    #-------------------------------------------------------
    text_test = text.replace(' ', '')
    units = ['dag', 'lbs', 'lb', 'kg', 'oz', 't', 'mg', 'g']
    unit = ''
    for element in units:
        if element in text_test:
            unit = element
            text_test = text_test.replace(element, '')
            break
    if text_test.replace('.', '').isdigit():
        return (2, unit)
    #-------------------------------------------------------
    text_test = text.replace(' ', '')
    units = ['min', 'wk', 'yr', 'mo', 'ms', 'd', 'h', 's']
    unit = ''
    for element in units:
        if element in text_test:
            unit = element
            text_test = text_test.replace(element, '')
            break
    if text_test.replace('.', '').isdigit():
        return (3, unit)
    #-------------------------------------------------------
    return (0, '')

# handle messages with known units
def message_handler(message: telebot.types.Message, bot: telebot.TeleBot):
    x = check_message(message)
    if x == 1:
        print(message.text)
    elif x == 2:
        print(message.text)
    else:
        print(message.text)