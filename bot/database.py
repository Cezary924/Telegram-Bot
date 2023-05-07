import sqlite3, telebot

# connect to users database
db_conn = sqlite3.connect("../files/database.db", check_same_thread=False)

# create cursor
cursor = db_conn.cursor()

# create People table if it does not exist
# Role types:
#  -1 - banned
#   0 - guest
#   1 - user
#   2 - admin
def create_table_people():
    cursor.execute("""
        create table if not exists People (
            user_id integer primary key,
            first_name text,
            last_name text,
            username text,
            language_code text,
            role integer
            ); """)

# create State table if it does not exist
# A state is last run command by a person
def create_table_state():
    cursor.execute("""
        create table if not exists State (
            user_id integer primary key,
            state text
            ); """)

# check if person is present in table
def guest_check(message):
    cursor.execute("SELECT COUNT(1) FROM People WHERE user_id = ?;", (message.from_user.id, ))
    (present,)=cursor.fetchone()
    if present == 1:
        return True
    else:
        cursor.execute("INSERT INTO People VALUES (?, ?, ?, ?, ?, ?); ",
                       (message.from_user.id, message.from_user.first_name, 
                        message.from_user.last_name, message.from_user.username, 
                        message.from_user.language_code, 0))
        db_conn.commit()

# check if person is user
def user_check(message):
    cursor.execute("SELECT role FROM People WHERE user_id = ?;", (message.from_user.id, ))
    (role,)=cursor.fetchone()
    if role >= 1:
        return True
    else:
        return False

# check if person is admin
def admin_check(message):
    cursor.execute("SELECT role FROM People WHERE user_id = ?;", (message.from_user.id, ))
    (role,)=cursor.fetchone()
    if role == 2:
        return True
    else:
        return False
    
# save last command used by person
def save_current_state(message, state="0"):
    cursor.execute("SELECT COUNT(1) FROM State WHERE user_id = ?;", (message.from_user.id, ))
    (present,)=cursor.fetchone()
    if present == 1:
        cursor.execute("UPDATE State SET state = ? WHERE user_id = ?;", 
                       (state, message.from_user.id))
        db_conn.commit()
    else:
        cursor.execute("INSERT INTO State VALUES (?, ?); ",
                       (message.from_user.id, state))
        db_conn.commit()

# get last command used by person
def get_current_state(message):
    cursor.execute("SELECT COUNT(1) FROM State WHERE user_id = ?;", (message.from_user.id, ))
    (present,)=cursor.fetchone()
    if present == 1:
        cursor.execute("SELECT state FROM State WHERE user_id = ?;", 
                       (message.from_user.id, ))
        (state,)=cursor.fetchone()
        return state
    else:
        cursor.execute("INSERT INTO State VALUES (?, ?); ",
                       (message.from_user.id, "0"))
        db_conn.commit()
        return "0"

# forward message sent by person to admin
def forward_message_to_admin(message, bot):
    cursor.execute("SELECT user_id FROM People WHERE role = 2;")
    admins=cursor.fetchone()
    for admin in admins:
        markup = telebot.types.InlineKeyboardMarkup()
        admin_reply_button = telebot.types.InlineKeyboardButton(text = "↩️ Odpowiedz na wiadomość", 
                                                                callback_data = "contact_admin_reply")
        markup.add(admin_reply_button)
        bot.send_message(admin, "Cześć, *" + message.from_user.first_name 
                         + " (" + str(message.from_user.id) + ")* chciałby przekazać Ci tę wiadomość: \n\n_" 
                         + message.text + "_", parse_mode= 'Markdown', reply_markup = markup)
    bot.send_message(message.chat.id, "Wiadomość została przekazana pomyślnie 😁")