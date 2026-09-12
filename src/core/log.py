import datetime
import os
import sys
import threading
import time
from contextlib import contextmanager

from core import paths
from core.utils import without_secrets

line_length = 146


def print_log(info: str, message_text: str = "") -> None:
    print(datetime.datetime.now().strftime(" %Y-%m-%d %H:%M:%S "))
    print(" " + "-" * (line_length - 2) + " ")
    print(" " + without_secrets(info) + " ")
    if message_text and message_text.isascii():
        print(" - '" + without_secrets(message_text) + "' ")
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
        self._terminal = sys.__stdout__
        self._show(loading_frame(0))

    def _show(self, frame: str) -> None:
        if self._terminal is None:
            return
        self._terminal.write(frame + '\r')
        self._terminal.flush()

    def __str__(self) -> str:
        if self._dots >= 4:
            self._dots = 0
        frame = loading_frame(self._dots)
        self._dots += 1
        return frame

    def run(self) -> None:
        while self._is_running:
            self._show(str(self))
            time.sleep(0.5)

    def stop(self) -> None:
        self._is_running = False


class Logger:
    def __init__(self, path: str | None = None) -> None:
        self.lock = threading.Lock()
        self.terminal = sys.stdout
        self._held: list[str] | None = None
        if path is None:
            name = datetime.datetime.now().strftime("log_%Y-%m-%d_%H-%M-%S.log")
            path = paths.log_file(name)
        paths.make_dir(os.path.dirname(path))
        self.file = open(path, 'a', buffering=1)

    def hold(self) -> None:
        with self.lock:
            self._held = []

    def release(self) -> None:
        with self.lock:
            held, self._held = self._held, None
        for text in held or []:
            self.write(text)

    @contextmanager
    def direct(self):
        with self.lock:
            held, self._held = self._held, None
        try:
            yield
        finally:
            with self.lock:
                self._held = held

    def write(self, text: str) -> None:
        with self.lock:
            if self._held is not None:
                self._held.append(text)
                return
            self.terminal.write(text)
            if not self.file.closed:
                self.file.write(text)

    def flush(self) -> None:
        self.terminal.flush()
        if not self.file.closed:
            self.file.flush()

    def close(self) -> None:
        self.release()
        with self.lock:
            if sys.stdout is self:
                sys.stdout = self.terminal
            if not self.file.closed:
                self.file.close()
