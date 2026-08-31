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
