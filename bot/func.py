import datetime

# create boolean variable storing info if beta ver of bot is running
suffix = 0

# read and open file 'name' located in 'path'
def read_file(name, path):
    try:
        with open(path) as f:
            x = f.readlines()
        f.close()
    except OSError:
        print("Open error: Could not open the \'" + name + ".txt\' file.")
    return x

# write and open file 'name' located in 'path' with buffering parameter 'buff'
def write_file(name, path, buff = -1):
    try:
        x = open(path, 'w', buffering = buff)
    except OSError:
        print("Open error: Could not open the \'" + name + ".txt\' file.")
    return x

# write and open log file 'name' located in 'path'
def log_file(name, path):
    try:
        x = open(path, 'a')
    except OSError:
        print("Open error: Could not open the \'" + name + ".txt\' file.")
    return x

# print info about bot's tasks
def print_log(info, bot_name = None, start = 0):
    if bot_name != None and start == 1:
        print("|================================================================|")
        print("|++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++|")
        print(" " + "               " + bot_name + " has been started. ")
        print("|++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++|")
        print("|================================================================|")
        return
    elif bot_name != None and start == 0:
        print("|++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++|")
        print(" " + "               " + bot_name + " has been stopped. ")
        print("|++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++|")
        print("|================================================================|")
        return
    print(str(datetime.datetime.now().strftime(" %Y-%m-%d %H:%M:%S ")))
    print(" ---------------------------------------------------------------- ")
    print(" " + info + " ")
    print("|================================================================|")