import datetime, yaml

# create boolean variable storing info if beta ver of bot is running
suffix = 0

def synchronized_with_attr(lock_name):
    def decorator(method):
        def synced_method(self, *args, **kws):
            lock = getattr(self, lock_name)
            with lock:
                return method(self, *args, **kws)
        return synced_method
    return decorator

# load file 'name' located in 'path'
def load_config_file(name, path):
    try:
        with open(path, encoding='utf8') as f:
            x = yaml.load(f, Loader=yaml.Loader)
    except OSError:
        print_log("ERROR: Open error - Could not open the " + name + " file.")
    return x

config = load_config_file("config.yaml", "../files/config.yaml")
tokens = load_config_file("tokens.yaml", "../files/tokens.yaml")

# read and open file 'name' located in 'path'
def read_file(name, path):
    try:
        with open(path) as f:
            x = f.readlines()
    except OSError:
        print_log("ERROR: Open error - Could not open the \'" + name + ".txt\' file.")
    return x

# write and open file 'name' located in 'path' with buffering parameter 'buff'
def write_file(name, path, buff = -1):
    try:
        x = open(path, 'w', buffering = buff)
    except OSError:
        print_log("ERROR: Open error - Could not open the \'" + name + ".txt\' file.")
    return x

# write and open log file 'name' located in 'path'
def log_file(name, path):
    try:
        x = open(path, 'a')
    except OSError:
        print("ERROR: Open error - Could not open the \'" + name + ".txt\' file.")
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