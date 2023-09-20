import telebot

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

