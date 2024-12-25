import sqlite3, threading, requests, telebot
from datetime import datetime
import func, locales

# connect to users database
if func.suffix == 0:
    db_conn = sqlite3.connect("../db/database.db", check_same_thread=False)
else:
    db_conn = sqlite3.connect("../db/database-beta.db", check_same_thread=False)

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

# create Settings table if it does not exist
def create_table_settings() -> None:
    database_lock.acquire(True)
    cursor.execute("""
        create table if not exists Settings (
            id integer primary key,
            lang_code text,
            notifications int
            ); """)
    database_lock.release()

# create Reminder table if it does not exist
def create_table_reminder() -> None:
    database_lock.acquire(True)
    cursor.execute("""
        create table if not exists Reminder (
            id integer,
            date text,
            description text,
            notified integer
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
            cursor.execute("INSERT INTO People VALUES (?, ?, ?, ?, ?); ",
                           (message.chat.id, message.chat.first_name, 
                            message.chat.last_name, message.chat.username, 0))
            db_conn.commit()
            database_lock.release()
            send_new_user_info(bot, message.chat.id, message.chat.first_name)
            return True
        func.print_log("", "Data Processing Agreement: " + message.chat.first_name + " (" + str(message.chat.id) + ").")
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

# check if person is banned
def banned_check(message: telebot.types.Message) -> bool:
    database_lock.acquire(True)
    cursor.execute("SELECT COUNT(1) FROM People WHERE id = ?;", (message.chat.id, ))
    (present,)=cursor.fetchone()
    database_lock.release()
    if present == 1:
        database_lock.acquire(True)
        cursor.execute("SELECT role FROM People WHERE id = ?;", (message.chat.id, ))
        (role,)=cursor.fetchone()
        database_lock.release()
        if role >= 0:
            return False
        else:
            return True
    else:
        return False

# check if person is banned
def banned_check(message: telebot.types.Message) -> bool:
    database_lock.acquire(True)
    cursor.execute("SELECT COUNT(1) FROM People WHERE id = ?;", (message.chat.id, ))
    (present,)=cursor.fetchone()
    database_lock.release()
    if present == 1:
        database_lock.acquire(True)
        cursor.execute("SELECT role FROM People WHERE id = ?;", (message.chat.id, ))
        (role,)=cursor.fetchone()
        database_lock.release()
        if role >= 0:
            return False
        else:
            return True
    else:
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
    cursor.execute("DELETE FROM Settings WHERE id = ?; ", (message.chat.id, ))
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
        func.print_log("", "ERROR: Database error - The raport could not be sent because there are no Admins in the database.")
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

# get list of users
def get_users() -> list[tuple[int, str]]:
    database_lock.acquire(True)
    cursor.execute("SELECT id, first_name FROM People;")
    users = cursor.fetchall()
    database_lock.release()
    return users

# get user data
def get_user_data(userid: int) -> tuple[str, str, str, int]:
    database_lock.acquire(True)
    cursor.execute("SELECT first_name, last_name, username, role FROM People WHERE id = ?;", (userid, ))
    data = cursor.fetchone()
    database_lock.release()
    return data

# edit user role
def edit_user_role(userid: int, role: int):
    database_lock.acquire(True)
    cursor.execute("UPDATE People SET role = ? WHERE id = ?;", 
                       (role, userid))
    if role > 0:
        cursor.execute("UPDATE Settings SET notifications = ? WHERE id = ?;", 
                       (1, userid))
    else:
        cursor.execute("UPDATE Settings SET notifications = ? WHERE id = ?;", 
                       (0, userid))
    db_conn.commit()
    database_lock.release()

# send info about update to users
def send_update_info_to_users(bot: telebot.TeleBot) -> None:
    response = requests.get('https://api.github.com/repos/' + func.config['github_username'] + '/' + func.config['github_repo'] + '/releases/latest')
    if response.status_code != 200:
        func.print_log("", "ERROR: Wrong response from GitHub.")
    response = response.json()
    database_lock.acquire(True)
    cursor.execute("SELECT id FROM Settings WHERE notifications = ?;", (1, ))
    ids=cursor.fetchall()
    database_lock.release()
    for (userid,) in ids:
        send_message_to_user(userid, bot, '\n\n' + response['html_url'], get_msg_text = 'update_info', disable_notification=True)

# send info about role change
def send_role_change_info(userid: int, bot: telebot.TeleBot, text: str) -> None:
    send_message_to_user(userid, bot, text + "_", get_msg_text = 'role_change_mess')

# send message to user
def send_message_to_user(userid: int, bot: telebot.TeleBot, text: str, disable_notification: bool = False, get_msg_text: str = None) -> None:
    if get_msg_text != None:
        text = get_message_text(create_empty_message(userid), get_msg_text) + text
    bot.send_message(userid, "*🤖 Bot:*\n\n" + text, disable_notification=disable_notification, parse_mode = 'Markdown')
    func.print_log("", "The message has been sent to the User: " + get_user_data(userid)[0] + " (" + str(userid) + ").")

# send info about (re)start
def send_start_info(bot: telebot.TeleBot) -> None:
    send_message_to_admins(bot, "", True, 'send_start_info')

# send info about stop
def send_stop_info(bot: telebot.TeleBot) -> None:
    send_message_to_admins(bot, "", True, 'send_stop_info')

# send info about error
def send_error_info(bot: telebot.TeleBot, err: str) -> None:
    send_message_to_admins(bot, "\nError: _" + err + "_", False, 'send_error_info')

# send new user info
def send_new_user_info(bot: telebot.TeleBot, user_id: int, user_first_name: str) -> None:
    send_message_to_admins(bot, "\nNick: _" + user_first_name + "_\nID: _" + str(user_id) + "_", False, 'send_new_user_info')

# send message to Admins
def send_message_to_admins(bot: telebot.TeleBot, text: str, disable_notification: bool = False, get_msg_text: str = None) -> None:
    database_lock.acquire(True)
    cursor.execute("SELECT p.id, first_name FROM People AS p FULL OUTER JOIN Settings AS s ON p.id = s.id WHERE role = 2 AND notifications = 1;")
    admins = cursor.fetchall()
    database_lock.release()
    if len(admins) > 0:
        names = [x[1] for x in admins]
        ids = [x[0] for x in admins]
        for i in range(len(ids)):
            if get_msg_text != None:
                text = get_message_text(create_empty_message(ids[i]), get_msg_text) + text
            bot.send_message(ids[i], "*" + get_message_text(create_empty_message(ids[i]), 'admin_bot') + ":*\n\n" + text, disable_notification=disable_notification, parse_mode = 'Markdown')
            func.print_log("", "The message has been sent to the Admin: " + names[i] + " (" + str(ids[i]) + ").")
    else:
        func.print_log("", "ERROR: Database error - The messages could not be sent because there are no Admins in the database.")

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
        func.print_log("", "ERROR: Database error - The state could not be set because there are no Admins in the database.")

# get code of language that users use
def get_user_language(message: telebot.types.Message) -> str:
    database_lock.acquire(True)
    cursor.execute("SELECT COUNT(1) FROM Settings WHERE id = ?;", (message.chat.id, ))
    (present,)=cursor.fetchone()
    if present == 1:
        cursor.execute("SELECT lang_code FROM Settings WHERE id = ?;", 
                       (message.chat.id, ))
        (lang_code,)=cursor.fetchone()
        database_lock.release()
        return lang_code
    else:
        cursor.execute("INSERT INTO Settings VALUES (?, ?, ?); ",
                       (message.chat.id, 'en', 0))
        db_conn.commit()
        database_lock.release()
        return 'en'

# set code of language that users use
def set_user_language(message: telebot.types.Message, lang_code: str) -> None:
    database_lock.acquire(True)
    cursor.execute("SELECT COUNT(1) FROM Settings WHERE id = ?;", (message.chat.id, ))
    (present,)=cursor.fetchone()
    if present == 1:
        cursor.execute("UPDATE Settings SET lang_code = ? WHERE id = ?;", 
                       (lang_code, message.chat.id))
    else:
        cursor.execute("INSERT INTO Settings VALUES (?, ?, ?); ",
                       (message.chat.id, lang_code, 0))
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

# get users notifications settings
def get_user_notifications(message: telebot.types.Message) -> int:
    database_lock.acquire(True)
    cursor.execute("SELECT COUNT(1) FROM Settings WHERE id = ?;", (message.chat.id, ))
    (present,)=cursor.fetchone()
    if present == 1:
        cursor.execute("SELECT notifications FROM Settings WHERE id = ?;", 
                       (message.chat.id, ))
        (notifications,)=cursor.fetchone()
        database_lock.release()
        return notifications
    else:
        cursor.execute("INSERT INTO Settings VALUES (?, ?, ?); ",
                       (message.chat.id, 'en', 0))
        db_conn.commit()
        database_lock.release()
        return 0

# set users notifications settings
def set_user_notifications(message: telebot.types.Message, notifications: int) -> None:
    database_lock.acquire(True)
    cursor.execute("SELECT COUNT(1) FROM Settings WHERE id = ?;", (message.chat.id, ))
    (present,)=cursor.fetchone()
    if present == 1:
        cursor.execute("UPDATE Settings SET notifications = ? WHERE id = ?;", 
                       (notifications, message.chat.id))
    else:
        cursor.execute("INSERT INTO Settings VALUES (?, ?, ?); ",
                       (message.chat.id, 'en', notifications))
    db_conn.commit()
    database_lock.release()

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

# get reminders that users have created
def get_unnotified_reminders() -> tuple[int, list[tuple[int, str, str, int]]]:
    database_lock.acquire(True)
    cursor.execute("SELECT rowid, date, description, id FROM Reminder WHERE notified = ?;", (0, ))
    reminders = cursor.fetchall()
    database_lock.release()
    return (len(reminders), reminders)
    
# set reminder that user has created
def set_reminder(message: telebot.types.Message, date: str, description: str) -> None:
    date_obj = datetime.strptime(date, '%Y-%m-%d %H:%M')
    now_obj = datetime.strptime(datetime.now().strftime('%Y-%m-%d %H:%M'), '%Y-%m-%d %H:%M')
    if now_obj < date_obj:
        notified = 0
    else:
        notified = 1
    database_lock.acquire(True)
    cursor.execute("INSERT INTO Reminder VALUES (?, ?, ?, ?); ",
                       (message.chat.id, date, description, notified))
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
    date_obj = datetime.strptime(date, '%Y-%m-%d %H:%M')
    now_obj = datetime.strptime(datetime.now().strftime('%Y-%m-%d %H:%M'), '%Y-%m-%d %H:%M')
    if now_obj < date_obj:
        edit_notified_status(id, 0)
    else:
        edit_notified_status(id, 1)
    database_lock.acquire(True)
    cursor.execute("UPDATE Reminder SET date = ? WHERE rowid = ?;", 
                       (date, id))
    db_conn.commit()
    database_lock.release()

# edit notified status
def edit_notified_status(id: int, notified: int) -> None:
    database_lock.acquire(True)
    cursor.execute("UPDATE Reminder SET notified = ? WHERE rowid = ?;", 
                       (notified, id))
    db_conn.commit()
    database_lock.release()

# delete reminder
def delete_reminder_rowid(rowid: int) -> None:
    database_lock.acquire(True)
    cursor.execute("DELETE FROM Reminder WHERE rowid = ?; ", (rowid, ))
    db_conn.commit()
    database_lock.release()