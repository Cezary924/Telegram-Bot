import sqlite3, threading, telebot
import func, locales

# connect to users database
if func.suffix == 0:
    db_conn = sqlite3.connect("../files/database.db", check_same_thread=False)
else:
    db_conn = sqlite3.connect("../files/database-beta.db", check_same_thread=False)

# create cursor
cursor = db_conn.cursor()

# create lock object
database_lock = threading.Lock()

# create People table if it does not exist
# Role types:
#  -1 - banned
#   0 - guest
#   1 - user
#   2 - admin
def create_table_people():
    database_lock.acquire(True)
    cursor.execute("""
        create table if not exists People (
            id integer primary key,
            first_name text,
            last_name text,
            username text,
            language_code text,
            role integer
            ); """)
    database_lock.release()

# create State table if it does not exist
# A state is last run command by a person
def create_table_state():
    database_lock.acquire(True)
    cursor.execute("""
        create table if not exists State (
            id integer primary key,
            state text
            ); """)
    database_lock.release()

# create Last_Bot_Message table if it does not exist
def create_table_last_bot_message():
    database_lock.acquire(True)
    cursor.execute("""
        create table if not exists Last_Bot_Message (
            id integer primary key,
            mess_id integer
            ); """)
    database_lock.release()

# create Language table if it does not exist
def create_table_language():
    database_lock.acquire(True)
    cursor.execute("""
        create table if not exists Language (
            id integer primary key,
            lang_code text
            ); """)
    database_lock.release()

# commit changes and close connection with database
def commit_close():
    database_lock.acquire(True)
    db_conn.commit()
    db_conn.close()
    database_lock.release()

# check if person is present in table
def guest_check(message, bot = None, dataprocessing = 0):
    database_lock.acquire(True)
    cursor.execute("SELECT COUNT(1) FROM People WHERE id = ?;", (message.chat.id, ))
    (present,)=cursor.fetchone()
    database_lock.release()
    if present == 1:
        return True
    else:
        if dataprocessing == 1:
            database_lock.acquire(True)
            cursor.execute("INSERT INTO People VALUES (?, ?, ?, ?, ?, ?); ",
                           (message.chat.id, message.chat.first_name, 
                            message.chat.last_name, message.chat.username, 
                            message.from_user.language_code, 0))
            db_conn.commit()
            database_lock.release()
            return True
        func.print_log("/dataprocessing_pl: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
        markup = telebot.types.InlineKeyboardMarkup()
        text = get_message_text(message, 'command_dataprocessing_lang_switch', 'pl')
        en_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_dataprocessing_en")
        markup.add(en_button)
        text = get_message_text(message, 'command_dataprocessing_yes_button', 'pl')
        yes_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_dataprocessing_pl_yes")
        markup.add(yes_button)
        text = get_message_text(message, 'command_dataprocessing_no_button', 'pl')
        no_button = telebot.types.InlineKeyboardButton(text = text, callback_data = "command_dataprocessing_pl_no")
        markup.add(no_button)
        text = get_message_text(message, 'command_dataprocessing', 'pl')
        bot.send_message(message.chat.id, text, parse_mode = 'Markdown', reply_markup = markup)
        return False

# check if person is user
def user_check(message):
    database_lock.acquire(True)
    cursor.execute("SELECT role FROM People WHERE id = ?;", (message.chat.id, ))
    (role,)=cursor.fetchone()
    database_lock.release()
    if role >= 1:
        return True
    else:
        return False

# check if person is admin
def admin_check(message):
    database_lock.acquire(True)
    cursor.execute("SELECT role FROM People WHERE id = ?;", (message.chat.id, ))
    (role,)=cursor.fetchone()
    database_lock.release()
    if role == 2:
        return True
    else:
        return False
    
# save last command used by person
def set_current_state(message, state="0"):
    database_lock.acquire(True)
    cursor.execute("SELECT COUNT(1) FROM State WHERE id = ?;", (message.chat.id, ))
    (present,)=cursor.fetchone()
    if present == 1:
        cursor.execute("UPDATE State SET state = ? WHERE id = ?;", 
                       (state, message.chat.id))
        db_conn.commit()
        database_lock.release()
    else:
        if state != "1":
            cursor.execute("INSERT INTO State VALUES (?, ?); ",
                        (message.chat.id, state))
            db_conn.commit()
            database_lock.release()
        else:
            cursor.execute("INSERT INTO State VALUES (?, ?); ",
                        (message.chat.id, "0"))
            db_conn.commit()
            database_lock.release()
            guest_check(message, dataprocessing=1)

# get last command used by person
def get_current_state(message):
    database_lock.acquire(True)
    cursor.execute("SELECT COUNT(1) FROM State WHERE id = ?;", (message.chat.id, ))
    (present,)=cursor.fetchone()
    if present == 1:
        cursor.execute("SELECT state FROM State WHERE id = ?;", 
                       (message.chat.id, ))
        (state,)=cursor.fetchone()
        database_lock.release()
        return state
    else:
        cursor.execute("INSERT INTO State VALUES (?, ?); ",
                       (message.chat.id, "0"))
        db_conn.commit()
        database_lock.release()
        return "0"

# delete all data collected from person
def deletedata(message):
    database_lock.acquire(True)
    cursor.execute("DELETE FROM State WHERE id = ?; ", (message.chat.id, ))
    cursor.execute("DELETE FROM People WHERE id = ?; ", (message.chat.id, ))
    cursor.execute("DELETE FROM Last_Bot_Message WHERE id = ?; ", (message.chat.id, ))
    cursor.execute("DELETE FROM Language WHERE id = ?; ", (message.chat.id, ))
    db_conn.commit()
    database_lock.release()

# forward message sent by person to admin
def forward_message_to_admin(message, bot):
    database_lock.acquire(True)
    cursor.execute("SELECT id FROM People WHERE role = 2;")
    admins=cursor.fetchone()
    database_lock.release()
    if admins != None:
        for admin in admins:
            text_hi = get_message_text(message, 'hi')
            text = get_message_text(message, 'message_forwarded_to_admin')
            bot.send_message(admin, text_hi + ", *" + message.chat.first_name 
                            + " (" + str(message.chat.id) + ")* " + text + ": \n\n_" 
                            + message.text + "_", parse_mode= 'Markdown')
        text = get_message_text(message, 'forward_message_to_admin')
        bot.send_message(message.chat.id, text)
    else:
        func.print_log("ERROR: Database error - The raport could not be sent because there are no Admins in the database.")
        text = get_message_text(message, 'no_admin')
        bot.send_message(message.chat.id, text)
    set_current_state(message)

# register last bot message id
def register_last_message(message, state = 0):
    database_lock.acquire(True)
    cursor.execute("SELECT COUNT(1) FROM Last_Bot_Message WHERE id = ?;", (message.chat.id, ))
    (present,)=cursor.fetchone()
    if present == 1:
        cursor.execute("UPDATE Last_Bot_Message SET mess_id = ? WHERE id = ?;", 
                       (message.id, message.chat.id))
        db_conn.commit()
    else:
        cursor.execute("INSERT INTO Last_Bot_Message VALUES (?, ?); ",
                       (message.chat.id, message.id))
        db_conn.commit()
    database_lock.release()
    if state == 1:
        set_current_state(message, "1")

# get last bot message id
def get_last_message(message):
    database_lock.acquire(True)
    cursor.execute("SELECT COUNT(1) FROM Last_Bot_Message WHERE id = ?;", (message.chat.id, ))
    (present,)=cursor.fetchone()
    if present == 1:
        cursor.execute("SELECT mess_id FROM Last_Bot_Message WHERE id = ?;", 
                       (message.chat.id, ))
        (mess_id,)=cursor.fetchone()
        database_lock.release()
        return mess_id
    else:
        cursor.execute("INSERT INTO Last_Bot_Message VALUES (?, ?); ",
                       (message.chat.id, message.id))
        db_conn.commit()
        database_lock.release()
        return message.id

# send info about (re)start
def send_start_info(bot):
    database_lock.acquire(True)
    cursor.execute("SELECT id FROM People WHERE role = 2;")
    admins=cursor.fetchone()
    database_lock.release()
    if admins != None:
        for admin in admins:
            database_lock.acquire(True)
            cursor.execute("SELECT state FROM State WHERE id = ?;", (admin, ))
            (state,)=cursor.fetchone()
            database_lock.release()
            if state.startswith("err_"):
                mess = bot.send_message(admin, ".")
                text = get_message_text(mess, 'send_restart_error_info')
                text = text + "\n\nError: \n_" + state[4:] + "_"
                register_last_message(mess)
                bot.delete_message(mess.chat.id, get_last_message(mess))
                mess = bot.send_message(admin, text, parse_mode = 'Markdown')
                set_current_state(mess)
                func.print_log("The restart (error) info has been sent to: " + str(admin) + ".")
            elif "admin_restart_" in state:
                mess = bot.send_message(admin, ".")
                text = get_message_text(mess, 'send_restart_info')
                register_last_message(mess)
                bot.delete_message(mess.chat.id, get_last_message(mess))
                mess = bot.send_message(admin, text, parse_mode = 'Markdown')
                set_current_state(mess)
                func.print_log("The restart info has been sent to: " + str(admin) + ".")
            else:
                mess = bot.send_message(admin, ".")
                text = get_message_text(mess, 'send_start_info')
                register_last_message(mess)
                bot.delete_message(mess.chat.id, get_last_message(mess))
                mess = bot.send_message(admin, text, parse_mode = 'Markdown')
                set_current_state(mess)
                func.print_log("The start info has been sent to: " + str(admin) + ".")
    else:
        func.print_log("ERROR: Database error - The start info could not be sent because there are no Admins in the database.")

# send info about stop
def send_stop_info(bot):
    database_lock.acquire(True)
    cursor.execute("SELECT id FROM People WHERE role = 2;")
    admins=cursor.fetchone()
    database_lock.release()
    if admins != None:
        for admin in admins:
            mess = bot.send_message(admin, ".")
            text = get_message_text(mess, 'send_stop_info')
            register_last_message(mess)
            bot.delete_message(mess.chat.id, get_last_message(mess))
            mess = bot.send_message(admin, text, parse_mode = 'Markdown')
            # set_current_state(mess)
            func.print_log("The stop info has been sent to: " + str(admin) + ".")
    else:
        func.print_log("ERROR: Database error - The stop info could not be sent because there are no Admins in the database.")

# set state for every admin
def set_admins_state(bot, state):
    database_lock.acquire(True)
    cursor.execute("SELECT id FROM People WHERE role = 2;")
    admins=cursor.fetchone()
    database_lock.release()
    if admins != None:
        for admin in admins:
            mess = bot.send_message(admin, ".")
            register_last_message(mess)
            set_current_state(mess, state)
            bot.delete_message(mess.chat.id, get_last_message(mess))
    else:
        func.print_log("ERROR: Database error - The state could not be set because there are no Admins in the database.")

# get code of language that users use
def get_user_language(message):
    database_lock.acquire(True)
    cursor.execute("SELECT COUNT(1) FROM Language WHERE id = ?;", (message.chat.id, ))
    (present,)=cursor.fetchone()
    if present == 1:
        cursor.execute("SELECT lang_code FROM Language WHERE id = ?;", 
                       (message.chat.id, ))
        (lang_code,)=cursor.fetchone()
        database_lock.release()
        return lang_code
    else:
        cursor.execute("INSERT INTO Language VALUES (?, ?); ",
                       (message.chat.id, 'en'))
        db_conn.commit()
        database_lock.release()
        return 'en'

# set code of language that users use
def set_user_language(message, lang_code):
    database_lock.acquire(True)
    cursor.execute("SELECT COUNT(1) FROM Language WHERE id = ?;", (message.chat.id, ))
    (present,)=cursor.fetchone()
    if present == 1:
        cursor.execute("UPDATE Language SET lang_code = ? WHERE id = ?;", 
                       (lang_code, message.chat.id))
    else:
        cursor.execute("INSERT INTO Language VALUES (?, ?); ",
                       (message.chat.id, lang_code))
    db_conn.commit()
    database_lock.release()

# get message text
def get_message_text(message, key, lang = None):
    if lang != None:
        if lang != 'pl':
            if key in locales.en.keys():
                if locales.en[key] != None:
                    return locales.en[key].replace(r'\n', '\n')
        return locales.pl[key].replace(r'\n', '\n')
    else:
        if get_user_language(message) != 'pl':
            if key in locales.en.keys():
                if locales.en[key] != None:
                    return locales.en[key].replace(r'\n', '\n')
        return locales.pl[key].replace(r'\n', '\n')