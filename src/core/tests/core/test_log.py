import sys

from core import log


def test_print_log_frames_the_info(capsys):
    log.print_log("Something happened.")
    out = capsys.readouterr().out
    assert "Something happened." in out
    assert out.rstrip().endswith("|" + "=" * (log.line_length - 2) + "|")


def test_print_log_includes_ascii_message(capsys):
    log.print_log("URL received.", "https://example.com")
    assert "'https://example.com'" in capsys.readouterr().out


def test_print_log_skips_non_ascii_message(capsys):
    log.print_log("Message received.", "zażółć gęślą jaźń")
    assert "zażółć" not in capsys.readouterr().out


def test_print_error_prefixes(capsys):
    log.print_error("Module error - TikTok.")
    assert "ERROR: Module error - TikTok." in capsys.readouterr().out


def test_print_banner(capsys):
    log.print_banner("Bot", True)
    assert "Bot has been started." in capsys.readouterr().out
    log.print_banner("Bot", False)
    assert "Bot has been stopped." in capsys.readouterr().out


def test_loading_frame_has_constant_width():
    assert all(len(log.loading_frame(dots)) == log.line_length for dots in range(4))


def test_loading_string_cycles_dots():
    loading = log.LoadingString()
    frames = [str(loading) for _ in range(5)]
    assert frames[0] == frames[4]
    assert frames[1] != frames[0]


def test_loading_string_stops():
    loading = log.LoadingString()
    loading.stop()
    loading.run()


def test_logger_writes_to_file_and_terminal(tmp_path, capsys):
    path = tmp_path / "out.log"
    logger = log.Logger(str(path))
    logger.write("hello\n")
    logger.flush()
    logger.close()
    assert path.read_text() == "hello\n"
    assert capsys.readouterr().out.endswith("hello\n")


def test_logger_names_its_own_file(tmp_path, monkeypatch):
    monkeypatch.setattr(log.paths, "log_dir", str(tmp_path))
    logger = log.Logger()
    logger.write("value1")
    logger.close()
    written = list(tmp_path.glob("log_*.log"))
    assert len(written) == 1
    assert written[0].read_text() == "value1"


def test_closing_puts_the_terminal_back(tmp_path, monkeypatch):
    monkeypatch.setattr(log.paths, "log_dir", str(tmp_path))
    terminal = sys.stdout
    logger = log.Logger()
    sys.stdout = logger
    logger.close()
    assert sys.stdout is terminal


def test_writing_after_closing_reaches_the_terminal_only(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(log.paths, "log_dir", str(tmp_path))
    logger = log.Logger()
    logger.close()
    logger.write("text1")
    logger.flush()
    assert "text1" in capsys.readouterr().out


def test_closing_twice_is_harmless(tmp_path, monkeypatch):
    monkeypatch.setattr(log.paths, "log_dir", str(tmp_path))
    logger = log.Logger()
    logger.close()
    logger.close()


def make_logger(tmp_path, monkeypatch):
    monkeypatch.setattr(log.paths, "log_dir", str(tmp_path))
    return log.Logger()


def test_what_is_held_waits_for_the_release(tmp_path, monkeypatch, capsys):
    logger = make_logger(tmp_path, monkeypatch)
    logger.hold()
    logger.write("first")
    logger.write("second")
    assert capsys.readouterr().out == ""
    logger.release()
    assert capsys.readouterr().out == "firstsecond"


def test_a_direct_write_jumps_the_queue(tmp_path, monkeypatch, capsys):
    logger = make_logger(tmp_path, monkeypatch)
    logger.hold()
    logger.write("queued")
    with logger.direct():
        logger.write("banner")
    logger.release()
    assert capsys.readouterr().out == "bannerqueued"


def test_holding_carries_on_after_a_direct_write(tmp_path, monkeypatch, capsys):
    logger = make_logger(tmp_path, monkeypatch)
    logger.hold()
    with logger.direct():
        logger.write("banner")
    logger.write("still queued")
    assert capsys.readouterr().out == "banner"
    logger.release()
    assert capsys.readouterr().out == "still queued"


def test_nothing_is_lost_when_the_logger_closes_while_holding(tmp_path, monkeypatch, capsys):
    logger = make_logger(tmp_path, monkeypatch)
    logger.hold()
    logger.write("queued")
    logger.close()
    assert "queued" in capsys.readouterr().out
    assert list(tmp_path.glob("log_*.log"))[0].read_text() == "queued"


def test_writing_without_holding_goes_straight_out(tmp_path, monkeypatch, capsys):
    logger = make_logger(tmp_path, monkeypatch)
    logger.write("now")
    assert capsys.readouterr().out == "now"


def test_the_file_carries_the_lines_before_the_logger_closes(tmp_path, monkeypatch):
    logger = make_logger(tmp_path, monkeypatch)
    logger.write("line one\n")
    logger.write("line two\n")
    written = list(tmp_path.glob("log_*.log"))[0]
    assert written.read_text() == "line one\nline two\n"
    logger.close()


def test_released_lines_reach_the_file_at_once(tmp_path, monkeypatch):
    logger = make_logger(tmp_path, monkeypatch)
    logger.hold()
    logger.write("queued\n")
    written = list(tmp_path.glob("log_*.log"))[0]
    assert written.read_text() == ""
    logger.release()
    assert written.read_text() == "queued\n"
    logger.close()
