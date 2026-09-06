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


def test_a_plain_job_waits_the_whole_interval():
    assert Scheduler()._delay(60, False) == 60


def test_an_aligned_job_waits_only_until_the_next_whole_interval(monkeypatch):
    monkeypatch.setattr("core.scheduler.time.time", lambda: 1012.5)
    assert Scheduler()._delay(60, True) == 60 - (1012.5 % 60)


def test_an_aligned_job_lands_on_the_interval(monkeypatch):
    monkeypatch.setattr("core.scheduler.time.time", lambda: 119.0)
    assert Scheduler()._delay(60, True) == 1.0


def test_a_job_is_found_by_its_name():
    one = Scheduler()
    one.add("job1", lambda: None, 60, is_aligned=True)
    found = one.find("job1")
    assert found is not None and found.interval == 60 and found.is_aligned
    assert one.find("job2") is None
