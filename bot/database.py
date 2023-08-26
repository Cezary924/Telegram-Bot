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
def create_table_people() -> None:
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
def create_table_state() -> None:
    database_lock.acquire(True)
    cursor.execute("""
        create table if not exists State (
            id integer primary key,
            state text
            ); """)
    database_lock.release()

# create Last_Bot_Message table if it does not exist
def create_table_last_bot_message() -> None:
    database_lock.acquire(True)
    cursor.execute("""
        create table if not exists Last_Bot_Message (
            id integer primary key,
            mess_id integer
            ); """)
    database_lock.release()

# create Language table if it does not exist
def create_table_language() -> None:
    database_lock.acquire(True)
    cursor.execute("""
        create table if not exists Language (
            id integer primary key,
            lang_code text
            ); """)
    database_lock.release()

# create Reminder table if it does not exist
def create_table_reminder() -> None:
    database_lock.acquire(True)
    cursor.execute("""
        create table if not exists Reminder (
            id integer,
            date text,
            description text
            ); """)
    database_lock.release()

# commit changes and close connection with database
def commit_close() -> None:
    database_lock.acquire(True)
    db_conn.commit()
    db_conn.close()
    database_lock.release()

# check if person is present in table
def guest_check(message: telebot.types.Message, bot: telebot.TeleBot = None, dataprocessing: bool = 0) -> bool:
    database_lock.acquire(True)
    cursor.execute("SELECT COUNT(1) FROM People WHERE id = ?;", (message.chat.id, ))
    (present,)=cursor.fetchone()
    database_lock.release()
    if present == 1:
        return True
    else:
        if dataprocessing:
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
def user_check(message: telebot.types.Message) -> bool:
    database_lock.acquire(True)
    cursor.execute("SELECT role FROM People WHERE id = ?;", (message.chat.id, ))
    (role,)=cursor.fetchone()
    database_lock.release()
    if role >= 1:
        return True
    else:
        return False

# check if person is admin
def admin_check(message: telebot.types.Message) -> bool:
    database_lock.acquire(True)
    cursor.execute("SELECT role FROM People WHERE id = ?;", (message.chat.id, ))
    (role,)=cursor.fetchone()
    database_lock.release()
    if role == 2:
        return True
    else:
        return False
    
# save last command used by person
def set_current_state(message: telebot.types.Message, state: str = "0") -> None:
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
def get_current_state(message: telebot.types.Message) -> str:
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
def deletedata(message: telebot.types.Message) -> None:
    database_lock.acquire(True)
    cursor.execute("DELETE FROM State WHERE id = ?; ", (message.chat.id, ))
    cursor.execute("DELETE FROM People WHERE id = ?; ", (message.chat.id, ))
    cursor.execute("DELETE FROM Last_Bot_Message WHERE id = ?; ", (message.chat.id, ))
    cursor.execute("DELETE FROM Language WHERE id = ?; ", (message.chat.id, ))
    cursor.execute("DELETE FROM Reminder WHERE id = ?; ", (message.chat.id, ))
    db_conn.commit()
    database_lock.release()

# forward message sent by person to admin
def forward_message_to_admin(message: telebot.types.Message, bot: telebot.TeleBot) -> None:
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

# register last Bot message id
def register_last_message(message: telebot.types.Message, state: bool = 0) -> None:
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
    if state:
        set_current_state(message, "1")

# get last Bot message id
def get_last_message(message: telebot.types.Message) -> int:
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
def send_start_info(bot: telebot.TeleBot) -> None:
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
                text = get_message_text(create_empty_message(admin), 'send_restart_error_info')
                text = text + "\n\nError: \n_" + state[4:] + "_"
                mess = bot.send_message(admin, text, disable_notification = True, parse_mode = 'Markdown')
                set_current_state(mess)
                func.print_log("The restart (error) info has been sent to: " + str(admin) + ".")
            elif "admin_restart_" in state:
                text = get_message_text(create_empty_message(admin), 'send_restart_info')
                mess = bot.send_message(admin, text, disable_notification = True, parse_mode = 'Markdown')
                set_current_state(mess)
                func.print_log("The restart info has been sent to: " + str(admin) + ".")
            else:
                text = get_message_text(create_empty_message(admin), 'send_start_info')
                mess = bot.send_message(admin, text, disable_notification = True, parse_mode = 'Markdown')
                set_current_state(mess)
                func.print_log("The start info has been sent to: " + str(admin) + ".")
    else:
        func.print_log("ERROR: Database error - The start info could not be sent because there are no Admins in the database.")

# send info about stop
def send_stop_info(bot: telebot.TeleBot) -> None:
    database_lock.acquire(True)
    cursor.execute("SELECT id FROM People WHERE role = 2;")
    admins=cursor.fetchone()
    database_lock.release()
    if admins != None:
        for admin in admins:
            text = get_message_text(create_empty_message(admin), 'send_stop_info')
            mess = bot.send_message(admin, text, disable_notification = True, parse_mode = 'Markdown')
            func.print_log("The stop info has been sent to: " + str(admin) + ".")
    else:
        func.print_log("ERROR: Database error - The stop info could not be sent because there are no Admins in the database.")

# send info about error
def send_error_info(bot: telebot.TeleBot, err: str) -> None:
    database_lock.acquire(True)
    cursor.execute("SELECT id FROM People WHERE role = 2;")
    admins=cursor.fetchone()
    database_lock.release()
    if admins != None:
        for admin in admins:
            text = get_message_text(create_empty_message(admin), 'send_error_info')
            mess = bot.send_message(admin, text + "\n\nError: \n_" + err + "_", disable_notification = True, parse_mode = 'Markdown')
            func.print_log("The error info has been sent to: " + str(admin) + ".")
    else:
        func.print_log("ERROR: Database error - The error info could not be sent because there are no Admins in the database.")

# set state for every admin
def set_admins_state(bot: telebot.TeleBot, state: str) -> None:
    database_lock.acquire(True)
    cursor.execute("SELECT id FROM People WHERE role = 2;")
    admins=cursor.fetchone()
    database_lock.release()
    if admins != None:
        for admin in admins:
            set_current_state(create_empty_message(admin), state)
    else:
        func.print_log("ERROR: Database error - The state could not be set because there are no Admins in the database.")

# get code of language that users use
def get_user_language(message: telebot.types.Message) -> str:
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
def set_user_language(message: telebot.types.Message, lang_code: str) -> None:
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
def get_message_text(message: telebot.types.Message, key: str, lang: str = None) -> str:
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

# create empty message
def create_empty_message(id: int) -> telebot.types.Message:
    from_user = telebot.types.User(id=id, is_bot=False, first_name="0")
    chat = telebot.types.User(id=id, is_bot=False, first_name="0")
    return telebot.types.Message(message_id=0, from_user=from_user, content_type=None, options="", json_string="0", date=0, chat=chat)

# get reminders with rowid
def get_reminder_rowid(rowid: int) -> list[str, str]:
    database_lock.acquire(True)
    cursor.execute("SELECT date, description FROM Reminder WHERE rowid = ?;", 
                       (rowid, ))
    reminders = cursor.fetchone()
    database_lock.release()
    return reminders

# get reminders that users have created
def get_reminders(message: telebot.types.Message) -> tuple[int, list[tuple[int, str, str]]]:
    database_lock.acquire(True)
    cursor.execute("SELECT COUNT(1) FROM Reminder WHERE id = ?;", (message.chat.id, ))
    (count,)=cursor.fetchone()
    if count > 0:
        cursor.execute("SELECT rowid, date, description FROM Reminder WHERE id = ?;", 
                       (message.chat.id, ))
        reminders = cursor.fetchall()
        database_lock.release()
        return (len(reminders), reminders)
    else:
        database_lock.release()
        return (0, [])

# set reminder that user has created
def set_reminder(message: telebot.types.Message, date: str, description: str) -> None:
    database_lock.acquire(True)
    cursor.execute("INSERT INTO Reminder VALUES (?, ?, ?); ",
                       (message.chat.id, date, description))
    db_conn.commit()
    database_lock.release()

# edit reminder content text
def edit_reminder_content(message: telebot.types.Message, id: int, content: str) -> None:
    database_lock.acquire(True)
    cursor.execute("UPDATE Reminder SET description = ? WHERE rowid = ?;", 
                       (content, id))
    db_conn.commit()
    database_lock.release()

# edit reminder date
def edit_reminder_date(message: telebot.types.Message, id: int, date: str) -> None:
    database_lock.acquire(True)
    cursor.execute("UPDATE Reminder SET date = ? WHERE rowid = ?;", 
                       (date, id))
    db_conn.commit()
    database_lock.release()