import threading
from typing import Callable

from core.log import print_error, print_log


class Scheduler:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._jobs: list[tuple[str, Callable, float]] = []
        self._threads: list[threading.Thread] = []

    def add(self, name: str, handler: Callable, interval: float) -> None:
        self._jobs.append((name, handler, interval))

    def names(self) -> list[str]:
        return [name for name, _, _ in self._jobs]

    def _loop(self, name: str, handler: Callable, interval: float) -> None:
        while not self._stop.is_set():
            try:
                handler()
            except Exception as error:
                print_error("Job failed in '" + name + "' - " + type(error).__name__ + ".", str(error))
            self._stop.wait(interval)

    def start(self) -> None:
        if not self._jobs:
            return
        for name, handler, interval in self._jobs:
            thread = threading.Thread(target=self._loop, args=(name, handler, interval),
                                      daemon=True, name="job-" + name)
            thread.start()
            self._threads.append(thread)
        print_log("Jobs started: " + ", ".join(self.names()) + ".")

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        for thread in self._threads:
            thread.join(timeout)
        self._threads.clear()
