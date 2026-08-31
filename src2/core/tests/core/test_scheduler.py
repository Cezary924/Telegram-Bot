import threading

from core.scheduler import Scheduler


def test_no_jobs_starts_nothing():
    scheduler = Scheduler()
    assert scheduler.names() == []
    scheduler.start()
    scheduler.stop()


def test_jobs_are_named():
    scheduler = Scheduler()
    scheduler.add("job1", lambda: None, 60)
    scheduler.add("job2", lambda: None, 60)
    assert scheduler.names() == ["job1", "job2"]


def test_a_job_runs_at_once():
    started = threading.Event()
    scheduler = Scheduler()
    scheduler.add("job1", started.set, 60)
    scheduler.start()
    assert started.wait(1)
    scheduler.stop()


def test_a_job_repeats():
    runs = []
    done = threading.Event()

    def handler():
        runs.append(1)
        if len(runs) >= 3:
            done.set()

    scheduler = Scheduler()
    scheduler.add("job1", handler, 0.01)
    scheduler.start()
    assert done.wait(2)
    scheduler.stop()
    assert len(runs) >= 3


def test_stopping_ends_the_loop():
    runs = []
    scheduler = Scheduler()
    scheduler.add("job1", lambda: runs.append(1), 0.01)
    scheduler.start()
    scheduler.stop()
    settled = len(runs)
    threading.Event().wait(0.1)
    assert len(runs) == settled


def test_a_failing_job_keeps_running(capsys):
    runs = []
    done = threading.Event()

    def handler():
        runs.append(1)
        if len(runs) >= 2:
            done.set()
        raise RuntimeError("boom")

    scheduler = Scheduler()
    scheduler.add("job1", handler, 0.01)
    scheduler.start()
    assert done.wait(2)
    scheduler.stop()
    assert "Job failed in 'job1' - RuntimeError." in capsys.readouterr().out


def test_one_failing_job_does_not_stop_another():
    healthy = threading.Event()
    scheduler = Scheduler()
    scheduler.add("job1", lambda: (_ for _ in ()).throw(RuntimeError("boom")), 0.01)
    scheduler.add("job2", healthy.set, 0.01)
    scheduler.start()
    assert healthy.wait(2)
    scheduler.stop()
