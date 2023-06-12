import sys, datetime

# get current date & time
time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# class for stdout logging instances
class LoggerStdout(object):
    def __init__(self):
        self.terminal = sys.stdout
        self.log = open("../log/log_out_" + time + ".log", "a")
    
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
    
    def flush(self):
        pass

# class for stderr logging instances
class LoggerStderr(object):
    def __init__(self):
        self.terminal = sys.stderr
        self.log = open("../log/log_err_" + time + ".log", "a")
    
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
    
    def flush(self):
        pass
