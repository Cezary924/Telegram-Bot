import time
from threading import Thread
from datetime import datetime

def check_reminders():
    while True:
        t = datetime.utcnow()
        sleeptime = 60 - (t.second + t.microsecond/1000000.0)
        time.sleep(sleeptime)
        print(datetime.utcnow())

thread = Thread(target = check_reminders, daemon = True)
thread.start()