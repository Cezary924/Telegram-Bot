import telebot

main_units = ['m', 'g', 's']
units_1 = {'mm': 1000, 'cm': 100, 'in': 39.37, 'dm': 10, 'ft': 3.281, 'm': 1, 'km': 0.001,  'mi': 0.000621371}
units_2 = {'mg': 1000, 'dag': 10, 'g': 1, 'oz': 0.03527396, 'lb': 0.00220462, 'kg': 0.001, 't': 0.000001}
units_3 = {'ms': 1000, 's': 1, 'min': 1/60, 'h': 1/3600, 'd': 1/86400, 'wk': 1/604800, 'mo': 1/2592000, 'yr': 1/31536000}

# check if the message contains any known unit
def check_message(message: telebot.types.Message) -> tuple[int, str, str]:
    text = message.text
    #-------------------------------------------------------
    text_test = text.replace(' ', '')
    units = list(units_1.keys())
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
    units = list(units_2.keys())
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
    units = list(units_3.keys())
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
def change_unit(num: float, x: int) -> None:
    if x == 3:
        for unit in list(units_3.keys()):
            _ = "{:g}".format(num * units_3[unit])
            print(_ + " " + unit) #TODO message to user

# handle messages with known units
def message_handler(message: telebot.types.Message, bot: telebot.TeleBot):
    x, unit, num = check_message(message)
    try:
        num = float(num)
    except:
        return #TODO message to user about misunderstood msg
    if x > 0:
        if unit in main_units:
            change_unit(num, x)
        else:
            num = get_to_main_unit(num, unit, x)
            change_unit(num, x)