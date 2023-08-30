import telebot, os, io, datetime, yaml, time
from urllib.parse import urlparse

# boolean variable storing info if beta ver of bot is running
suffix = 0

# int variable storing info how long should log lines be
log_length = 102

# sync for attributes
def synchronized_with_attr(lock_name: str):
    def decorator(method):
        def synced_method(self, *args, **kws):
            lock = getattr(self, lock_name)
            with lock:
                return method(self, *args, **kws)
        return synced_method
    return decorator

# load file 'name' located in 'path'
def load_config_file(name: str, path: str) -> dict[str, str]:
    try:
        with open(path, encoding='utf8') as f:
            x = yaml.load(f, Loader=yaml.Loader)
    except OSError:
        print_log("ERROR: Open error - Could not open the " + name + " file.")
    return x

config = load_config_file("config.yaml", "../files/config.yaml")
tokens = load_config_file("tokens.yaml", "../files/tokens.yaml")

# read and open file 'name' located in 'path'
def read_file(name: str, path: str) -> list[str]:
    try:
        with open(path) as f:
            x = f.readlines()
    except OSError:
        print_log("ERROR: Open error - Could not open the \'" + name + ".txt\' file.")
    return x

# write and open file 'name' located in 'path' with buffering parameter 'buff'
def write_file(name: str, path: str, buff: int = -1) -> io.TextIOWrapper:
    try:
        x = open(path, 'w', buffering = buff)
    except OSError:
        print_log("ERROR: Open error - Could not open the \'" + name + ".txt\' file.")
    return x

# write and open log file 'name' located in 'path'
def log_file(name: str, path: str) -> io.TextIOWrapper:
    try:
        x = open(path, 'a')
    except OSError:
        print("ERROR: Open error - Could not open the \'" + name + ".txt\' file.")
    return x

# class defining LoadingString objects
class LoadingString():
    def __init__(self) -> None:
        self._dots = 0
        self._stop = False
        print("|" + "=" * (log_length - 2) + "|")
        print("|" + "+" * (log_length - 2) + "|")
        print('Loading'.center(log_length, ' '), end = '\r')
    def __str__(self) -> str:
        if self._dots >= 4:
            self._dots = 0
        text = 'Loading'.center(log_length, ' ')
        text_split = text.split('Loading')
        text = text_split[0] + 'Loading' + '.' * self._dots + text_split[1][:-self._dots]
        self._dots = self._dots + 1
        return text
    def run(self) -> None:
        while self._stop == False:
            print(self, end = '\r')
            time.sleep(0.5)
    def stop(self) -> None:
        self._stop = True

# print info about Bot's tasks
def print_log(info: str, bot_name: str = None, start: bool = 0) -> None:
    if bot_name != None:
        if start:
            print('\r', end = '')
        if start == 0:
            print("|" + "+" * (log_length - 2) + "|")
        if start:
            text = bot_name + " has been started."
        else:
            text = bot_name + " has been stopped."
        print(text.center(log_length, ' '))
        print("|" + "+" * (log_length - 2) + "|")
        print("|" + "=" * (log_length - 2) + "|")
        return
    print(str(datetime.datetime.now().strftime(" %Y-%m-%d %H:%M:%S ")))
    print(" " + "-" * (log_length - 2) + " ")
    print(" " + info + " ")
    print("|" + "=" * (log_length - 2) + "|")

# check URL scheme & URL hostname
def check_url(message:telebot.types.Message, scheme: str, hostname: str) -> bool:
    url = urlparse(message.text)
    if url.scheme in scheme:
        if url.hostname in hostname:
            return True
    return False

# remove file 'name' located in 'path'
def remove_file(name: str, path: str) -> None:
    os.remove(path)

# remove directory 'name' located in 'path'
def remove_directory(name: str, path: str) -> None:
    files = os.listdir(path)
    for file in files:
        remove_file(file, path + "\\" + file)
    os.rmdir(path)
