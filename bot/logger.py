import telebot, sys, datetime, threading

import func

# get current date & time
time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# class for stdout logging instances
class LoggerStdout(object):
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.terminal = sys.stdout
        self.log = func.log_file("log_out_" + time + ".log", "../log/log_out_" + time + ".log")
    
    @func.synchronized_with_attr('lock')
    def write(self, message: telebot.types.Message) -> None:
        self.terminal.write(message)
        self.log.write(message)
    
    def flush(self) -> None:
        pass

# class for stderr logging instances
class LoggerStderr(object):
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.terminal = sys.stderr
        self.log = func.log_file("log_err_" + time + ".log", "../log/log_err_" + time + ".log")
    
    @func.synchronized_with_attr('lock')
    def write(self, message: telebot.types.Message) -> None:
        self.terminal.write(message)
        self.log.write(message)
    
    def flush(self) -> None:
        pass
