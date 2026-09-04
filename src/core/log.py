import datetime
import os
import sys
import threading
import time

from core import paths

line_length = 102


def print_log(info: str, message_text: str = "") -> None:
    print(datetime.datetime.now().strftime(" %Y-%m-%d %H:%M:%S "))
    print(" " + "-" * (line_length - 2) + " ")
    print(" " + info + " ")
    if message_text and message_text.isascii():
        print(" - '" + message_text + "' ")
    print("|" + "=" * (line_length - 2) + "|")


def print_error(info: str, message_text: str = "") -> None:
    print_log("ERROR: " + info, message_text)


def print_banner(bot_name: str, is_started: bool) -> None:
    if is_started:
        print('\r', end='')
        print("|" + "=" * (line_length - 2) + "|")
    print("|" + "+" * (line_length - 2) + "|")
    text = bot_name + (" has been started." if is_started else " has been stopped.")
    print(text.center(line_length, ' '))
    print("|" + "+" * (line_length - 2) + "|")
    print("|" + "=" * (line_length - 2) + "|")


def loading_frame(dots: int) -> str:
    text = 'Loading'.center(line_length - 2, ' ')
    left, right = text.split('Loading')
    if dots > 0:
        return '|' + left + 'Loading' + '.' * dots + right[:-dots] + '|'
    return '|' + left + 'Loading' + right + '|'


class LoadingString:
    def __init__(self) -> None:
        self._dots = 0
        self._is_running = True
        print(loading_frame(0), end='\r')

    def __str__(self) -> str:
        if self._dots >= 4:
            self._dots = 0
        frame = loading_frame(self._dots)
        self._dots += 1
        return frame

    def run(self) -> None:
        while self._is_running:
            print(self, end='\r')
            time.sleep(0.5)

    def stop(self) -> None:
        self._is_running = False


class Logger:
    def __init__(self, path: str | None = None) -> None:
        self.lock = threading.Lock()
        self.terminal = sys.stdout
        if path is None:
            name = datetime.datetime.now().strftime("log_%Y-%m-%d_%H-%M-%S.log")
            path = paths.log_file(name)
        paths.make_dir(os.path.dirname(path))
        self.file = open(path, 'a')

    def write(self, text: str) -> None:
        with self.lock:
            self.terminal.write(text)
            self.file.write(text)

    def flush(self) -> None:
        self.terminal.flush()
        self.file.flush()

    def close(self) -> None:
        with self.lock:
            self.file.close()
