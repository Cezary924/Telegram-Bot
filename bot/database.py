import sqlite3

# connect to users database
db_conn = sqlite3.connect("../files/users_database.db", check_same_thread=False)

# create cursor
cursor = db_conn.cursor()

# create People table if it does not exist
# Role types:
#   0 - guest
#   1 - user
#   2 - admin
def create_table():
    cursor.execute("""
        create table if not exists People (
            user_id integer primary key,
            first_name text,
            last_name text,
            username text,
            language_code text,
            role integer
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