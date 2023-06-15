import sqlite3, threading, telebot
import func

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
        markup = telebot.types.InlineKeyboardMarkup()
        yes_button = telebot.types.InlineKeyboardButton(text = "✅ Tak, zgadzam się", callback_data = "command_dataprocessing_yes")
        markup.add(yes_button)
        no_button = telebot.types.InlineKeyboardButton(text = "❌ Nie, nie zgadzam się", callback_data = "command_dataprocessing_no")
        markup.add(no_button)
        bot.send_message(message.chat.id, "✋ *Zgoda na przetwarzanie danych:*\n\nWidzę, że dopiero zaczynamy naszą wspólną drogę. "
                                + "Jednakże zanim będziemy mogli ze sobą rozmawiać, musisz zgodzić się na "
                                + "gromadzenie przeze mnie przekazywanych mi przez Ciebie danych oraz na "
                                + "wykorzystywanie ich zgodnie z ich przeznaczeniem - korzystanie z moich funkcjonalności, pomoc i ułatwianie Ci życia 💝", 
                        parse_mode = 'Markdown', reply_markup = markup)
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
def save_current_state(message, state="0"):
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
    db_conn.commit()
    database_lock.release()

# forward message sent by person to admin
def forward_message_to_admin(message, bot):
    database_lock.acquire(True)
    cursor.execute("SELECT id FROM People WHERE role = 2;")
    admins=cursor.fetchone()
    database_lock.release()
    for admin in admins:
        bot.send_message(admin, "Cześć, *" + message.chat.first_name 
                         + " (" + str(message.chat.id) + ")* chciałby przekazać Ci tę wiadomość-zgłoszenie: \n\n_" 
                         + message.text + "_", parse_mode= 'Markdown')
    bot.send_message(message.chat.id, "Wiadomość została przekazana pomyślnie 😁")
    save_current_state(message)

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
        save_current_state(message, "1")

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

def send_restart_info(bot,):
    database_lock.acquire(True)
    cursor.execute("SELECT id FROM People WHERE role = 2;")
    admins=cursor.fetchone()
    database_lock.release()
    for admin in admins:
        database_lock.acquire(True)
        cursor.execute("SELECT state FROM State WHERE id = ?;", (admin, ))
        (state,)=cursor.fetchone()
        database_lock.release()
        if "admin_restart_" in state:
            mess = bot.send_message(admin, "🤖 *Bot został pomyślnie uruchomiony ponownie!*", 
                     parse_mode = 'Markdown')
            save_current_state(mess)
            func.print_log("Sending info about restart to: " + str(admin) + ".")