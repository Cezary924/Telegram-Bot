import threading
import time
from dataclasses import dataclass
from typing import Callable

from core.log import print_error, print_log


@dataclass(frozen=True)
class Scheduled:
    name: str
    handler: Callable
    interval: float
    is_aligned: bool = False


class Scheduler:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._jobs: list[Scheduled] = []
        self._threads: list[threading.Thread] = []

    def add(self, name: str, handler: Callable, interval: float, is_aligned: bool = False) -> None:
        self._jobs.append(Scheduled(name, handler, interval, is_aligned))

    def names(self) -> list[str]:
        return [job.name for job in self._jobs]

    def find(self, name: str) -> Scheduled | None:
        return next((job for job in self._jobs if job.name == name), None)

    @staticmethod
    def _delay(interval: float, is_aligned: bool) -> float:
        return interval - time.time() % interval if is_aligned else interval

    def _loop(self, job: Scheduled) -> None:
        while not self._stop.is_set():
            try:
                job.handler()
            except Exception as error:
                print_error("Job failed in '" + job.name + "' - " + type(error).__name__ + ".",
                            str(error))
            self._stop.wait(self._delay(job.interval, job.is_aligned))

    def start(self) -> None:
        if not self._jobs:
            return
        for job in self._jobs:
            thread = threading.Thread(target=self._loop, args=(job,),
                                      daemon=True, name="job-" + job.name)
            thread.start()
            self._threads.append(thread)
        print_log("Jobs started: " + ", ".join(self.names()) + ".")

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        for thread in self._threads:
            thread.join(timeout)
        self._threads.clear()
