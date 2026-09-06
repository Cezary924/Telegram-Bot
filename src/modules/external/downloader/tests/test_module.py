import os
import pytest

from core.api import Role
from core.testing import make_callback, make_message
from modules.external.downloader import module as downloader

link1 = "https://example.com/watch?v=1"
insecure_link1 = link1.replace("https", "http")


def send(app, text: str):
    app.router.handle_message(make_message(text))
    app.router.wait_for_tasks()


def make_file(path: str, name: str = "video.mp4", size: int = 16) -> str:
    full_path = os.path.join(path, name)
    with open(full_path, "wb") as handle:
        handle.write(b"x" * size)
    return full_path


@pytest.fixture
def downloading(app, monkeypatch):
    monkeypatch.setattr(downloader, "download", lambda _url, path, _limit: make_file(path))
    return app


@pytest.mark.parametrize("text", [
    link1,
    insecure_link1,
    "https://example.com",
    "  https://example.com/a  ",
])
def test_a_lone_link_is_taken(text):
    assert downloader.is_link(text)


@pytest.mark.parametrize("text", [
    "", "hello", "5 km", "example.com/a", "ftp://example.com/a",
    "look at https://example.com/a", "https://example.com/a https://example.com/b", "https://",
])
def test_anything_else_is_left_alone(text):
    assert not downloader.is_link(text)


def test_the_command_explains_how(app, bot):
    send(app, "/downloader")
    assert bot.last.text.startswith("*📥 Downloader:*")
    assert "send me a link" in bot.last.text


def test_a_link_is_answered_and_the_video_is_sent(downloading, bot):
    send(downloading, link1)
    assert "give me a moment" in bot.texts()[-1]
    assert [(file.kind, file.name) for file in bot.files] == [("video", "video.mp4")]


def test_the_video_goes_to_the_person_who_asked(downloading, bot):
    send(downloading, link1)
    assert bot.files[0].chat_id == 1


def test_a_silent_user_gets_a_silent_video(downloading, bot):
    downloading.storage.settings.set_notifications(1, False)
    send(downloading, link1)
    assert bot.files[0].is_silent


def test_a_video_that_does_not_fit_is_reported(app, bot, monkeypatch):
    monkeypatch.setattr(downloader, "download", lambda _url, _path, _limit: None)
    send(app, link1)
    assert "too large" in bot.last.text
    assert bot.files == []


def test_a_failure_without_ffmpeg_names_the_reason(app, bot, monkeypatch, capsys):
    monkeypatch.setattr(downloader, "has_ffmpeg", lambda: False)

    def fail(_url, _path, _limit):
        raise ValueError("no such video")

    monkeypatch.setattr(downloader, "download", fail)
    send(app, link1)
    assert "ffmpeg is not installed" in capsys.readouterr().out


def test_a_failure_with_ffmpeg_says_nothing_about_it(app, bot, monkeypatch, capsys):
    monkeypatch.setattr(downloader, "has_ffmpeg", lambda: True)

    def fail(_url, _path, _limit):
        raise ValueError("no such video")

    monkeypatch.setattr(downloader, "download", fail)
    send(app, link1)
    assert "ffmpeg" not in capsys.readouterr().out


def test_a_failure_is_reported(app, bot, monkeypatch):
    def fail(_url, _path, _limit):
        raise ValueError("no such video")
    monkeypatch.setattr(downloader, "download", fail)
    send(app, link1)
    assert "could not download" in bot.last.text
    assert bot.files == []


def test_the_workspace_is_gone_afterwards(app, bot, monkeypatch):
    used = []

    def remember(_url, path, _limit):
        used.append(path)
        return make_file(path)

    monkeypatch.setattr(downloader, "download", remember)
    send(app, link1)
    assert used and not os.path.exists(used[0])


def test_a_guest_gets_nothing(downloading, bot):
    downloading.storage.users.set_role(1, Role.GUEST)
    send(downloading, link1)
    assert bot.last.text.startswith("Sorry, you cannot use this command")
    assert bot.files == []


def test_it_speaks_polish(downloading, bot):
    downloading.storage.settings.set_language(1, "pl")
    send(downloading, link1)
    assert "📥 Pobieracz" in bot.texts()[-1]


def test_a_screen_takes_the_message_before_the_downloader(app, bot):
    app.storage.users.set_role(1, Role.ADMIN)
    send(app, "/admin")
    for action in ["admin:users", "admin:search"]:
        app.router.handle_callback(make_callback(action, message_id=bot.last.message_id))
    send(app, link1)
    assert "has not been found" in bot.last.text
    assert bot.files == []


def options(tmp_path) -> dict:
    return downloader.build_options(str(tmp_path), 100)


def test_ffmpeg_brings_the_merging_format(monkeypatch, tmp_path):
    monkeypatch.setattr(downloader, "has_ffmpeg", lambda: True)
    assert options(tmp_path)['format'] == downloader.merged_format


def test_without_ffmpeg_only_a_single_file_is_asked_for(monkeypatch, tmp_path):
    monkeypatch.setattr(downloader, "has_ffmpeg", lambda: False)
    assert options(tmp_path)['format'] == downloader.single_format


def test_the_limit_reaches_yt_dlp(tmp_path):
    assert options(tmp_path)['max_filesize'] == 100


def test_pages_are_asked_for_the_way_a_browser_does(tmp_path):
    agent = options(tmp_path)['http_headers']['User-Agent']
    assert agent.startswith("Mozilla/5.0") and "Chrome/" in agent


def test_the_download_lands_in_the_workspace(tmp_path):
    assert options(tmp_path)['outtmpl'] == os.path.join(str(tmp_path), downloader.name_template)


def test_a_half_downloaded_file_is_not_taken(tmp_path):
    make_file(str(tmp_path), "video.mp4.part")
    assert downloader.downloaded_file(str(tmp_path), 100) is None


def test_a_file_over_the_limit_is_not_taken(tmp_path):
    make_file(str(tmp_path), "video.mp4", size=200)
    assert downloader.downloaded_file(str(tmp_path), 100) is None


def test_a_file_within_the_limit_is_taken(tmp_path):
    make_file(str(tmp_path), "video.mp4", size=50)
    assert downloader.downloaded_file(str(tmp_path), 100) == os.path.join(str(tmp_path), "video.mp4")
