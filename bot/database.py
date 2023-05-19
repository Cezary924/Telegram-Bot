import sqlite3
import func

# connect to users database
if func.suffix == 0:
    db_conn = sqlite3.connect("../files/database.db", check_same_thread=False)
else:
    db_conn = sqlite3.connect("../files/database-beta.db", check_same_thread=False)

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
            id integer primary key,
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
            id integer primary key,
            state text
            ); """)

# commit changes and close connection with database
def commit_close():
    db_conn.commit()
    db_conn.close()

# check if person is present in table
def guest_check(message):
    cursor.execute("SELECT COUNT(1) FROM People WHERE id = ?;", (message.chat.id, ))
    (present,)=cursor.fetchone()
    if present == 1:
        return True
    else:
        cursor.execute("INSERT INTO People VALUES (?, ?, ?, ?, ?, ?); ",
                       (message.chat.id, message.chat.first_name, 
                        message.chat.last_name, message.chat.username, 
                        message.from_user.language_code, 0))
        db_conn.commit()

# check if person is user
def user_check(message):
    cursor.execute("SELECT role FROM People WHERE id = ?;", (message.chat.id, ))
    (role,)=cursor.fetchone()
    if role >= 1:
        return True
    else:
        return False

# check if person is admin
def admin_check(message):
    cursor.execute("SELECT role FROM People WHERE id = ?;", (message.chat.id, ))
    (role,)=cursor.fetchone()
    if role == 2:
        return True
    else:
        return False
    
# save last command used by person
def save_current_state(message, state="0"):
    cursor.execute("SELECT COUNT(1) FROM State WHERE id = ?;", (message.chat.id, ))
    (present,)=cursor.fetchone()
    if present == 1:
        cursor.execute("UPDATE State SET state = ? WHERE id = ?;", 
                       (state, message.chat.id))
        db_conn.commit()
    else:
        cursor.execute("INSERT INTO State VALUES (?, ?); ",
                       (message.chat.id, state))
        db_conn.commit()

# get last command used by person
def get_current_state(message):
    cursor.execute("SELECT COUNT(1) FROM State WHERE id = ?;", (message.chat.id, ))
    (present,)=cursor.fetchone()
    if present == 1:
        cursor.execute("SELECT state FROM State WHERE id = ?;", 
                       (message.chat.id, ))
        (state,)=cursor.fetchone()
        return state
    else:
        cursor.execute("INSERT INTO State VALUES (?, ?); ",
                       (message.chat.id, "0"))
        db_conn.commit()
        return "0"

# delete all data collected from person
def deletedata(message):
    cursor.execute("DELETE FROM State WHERE id = ?; ", (message.chat.id, ))
    cursor.execute("DELETE FROM People WHERE id = ?; ", (message.chat.id, ))
    db_conn.commit()

# forward message sent by person to admin
def forward_message_to_admin(message, bot):
    cursor.execute("SELECT id FROM People WHERE role = 2;")
    admins=cursor.fetchone()
    for admin in admins:
        bot.send_message(admin, "Cześć, *" + message.chat.first_name 
                         + " (" + str(message.chat.id) + ")* chciałby przekazać Ci tę wiadomość-zgłoszenie: \n\n_" 
                         + message.text + "_", parse_mode= 'Markdown')
    bot.send_message(message.chat.id, "Wiadomość została przekazana pomyślnie 😁")
    save_current_state(message)