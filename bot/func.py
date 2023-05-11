import datetime

def read_file(name, path):
    try:
        with open(path) as f:
            x = f.readlines()
        f.close()
    except OSError:
        print("Open error: Could not open the \'telegram.txt\' file.")
    return x

def print_log(info, bot_name = None):
    if bot_name != None:
        print("|================================================================|")
        print("|++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++|")
        print(" " + bot_name + " has been started. ")
        print("|++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++|")
        print("|================================================================|")
        return
    print(str(datetime.datetime.now().strftime(" %Y-%m-%d %H:%M:%S ")))
    print(" ---------------------------------------------------------------- ")
    print(" " + info + " ")
    print("|================================================================|")