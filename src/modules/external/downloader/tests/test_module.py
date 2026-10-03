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
def asked_for(monkeypatch) -> list[tuple[str, str]]:
    return []


@pytest.fixture
def downloading(app, monkeypatch, asked_for):
    def download(url, path, _limit, kind):
        asked_for.append((url, kind))
        return make_file(path, "sound.mp3" if kind == "audio" else "video.mp4")

    monkeypatch.setattr(downloader, "download", download)
    return app


def press(app, data: str):
    app.router.handle_callback(make_callback(data, message_id=app.services.bot.last.message_id))
    app.router.wait_for_tasks()


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
    assert bot.last.text.startswith("<b>📥 Downloader:</b>")
    assert "send me a link" in bot.last.text


def test_a_link_is_answered_and_the_video_is_sent(downloading, bot):
    send(downloading, link1)
    assert "give me a moment" in bot.texts()[-1]
    assert [(file.kind, file.name) for file in bot.files] == [("video", "video.mp4")]


def test_the_video_goes_to_the_person_who_asked(downloading, bot):
    send(downloading, link1)
    assert bot.files[0].chat_id == 1


def test_a_video_the_user_asked_for_rings_even_with_notifications_off(downloading, bot):
    downloading.storage.settings.set_notifications(1, False)
    send(downloading, link1)
    assert not bot.files[0].is_silent


def test_a_video_that_does_not_fit_is_reported(app, bot, monkeypatch):
    monkeypatch.setattr(downloader, "download", lambda _url, _path, _limit, _kind: None)
    send(app, link1)
    assert "too large" in bot.last.text
    assert bot.files == []


def test_a_failure_without_ffmpeg_names_the_reason(app, bot, monkeypatch, capsys):
    monkeypatch.setattr(downloader, "has_ffmpeg", lambda: False)

    def fail(_url, _path, _limit, _kind):
        raise ValueError("no such video")

    monkeypatch.setattr(downloader, "download", fail)
    send(app, link1)
    assert "ffmpeg is missing or does not run" in capsys.readouterr().out


def test_a_failure_with_ffmpeg_says_nothing_about_it(app, bot, monkeypatch, capsys):
    monkeypatch.setattr(downloader, "has_ffmpeg", lambda: True)

    def fail(_url, _path, _limit, _kind):
        raise ValueError("no such video")

    monkeypatch.setattr(downloader, "download", fail)
    send(app, link1)
    assert "ffmpeg" not in capsys.readouterr().out


def test_a_failure_is_reported(app, bot, monkeypatch):
    def fail(_url, _path, _limit, _kind):
        raise ValueError("no such video")
    monkeypatch.setattr(downloader, "download", fail)
    send(app, link1)
    assert "could not download" in bot.last.text
    assert bot.files == []


def test_the_workspace_is_gone_afterwards(app, bot, monkeypatch):
    used = []

    def remember(_url, path, _limit, _kind):
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


def options(tmp_path, kind: str = "video") -> dict:
    return downloader.build_options(str(tmp_path), 100, kind)


def test_ffmpeg_brings_the_merging_format(monkeypatch, tmp_path):
    monkeypatch.setattr(downloader, "has_ffmpeg", lambda: True)
    assert options(tmp_path)['format'] == "bv*+ba/b"


def test_without_ffmpeg_only_a_single_file_is_asked_for(monkeypatch, tmp_path):
    monkeypatch.setattr(downloader, "has_ffmpeg", lambda: False)
    assert options(tmp_path)['format'] == "b[ext=mp4]/b"


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


def test_a_video_is_the_default(downloading, bot, asked_for):
    send(downloading, link1)
    assert asked_for == [(link1, "video")]
    assert [(file.kind, file.name) for file in bot.files] == [("video", "video.mp4")]


def test_sound_is_sent_as_an_audio_file(downloading, bot, asked_for):
    downloading.storage.module_state.set(1, "downloader", "format", "audio")
    send(downloading, link1)
    assert asked_for == [(link1, "audio")]
    assert [(file.kind, file.name) for file in bot.files] == [("audio", "sound.mp3")]


def test_asking_offers_a_choice_before_downloading(downloading, bot, asked_for):
    downloading.storage.module_state.set(1, "downloader", "format", "ask")
    send(downloading, link1)
    assert asked_for == []
    assert bot.last.text == "<b>📥 Downloader:</b>\n\nHow should I send it?"
    assert [text for text, _ in bot.last.buttons][:2] == ["🎬 Video (mp4)", "🎵 Sound (mp3)"]


def test_the_choice_downloads_what_was_picked_and_goes_away(downloading, bot, asked_for):
    downloading.storage.module_state.set(1, "downloader", "format", "ask")
    send(downloading, link1)
    question = bot.last.message_id
    press(downloading, [data for _, data in bot.last.buttons][1])
    assert asked_for == [(link1, "audio")]
    assert (1, question) in bot.deleted
    assert [file.kind for file in bot.files] == ["audio"]
    assert downloading.storage.navigation.current(1) is None


def test_a_choice_is_used_only_once(downloading, bot, asked_for):
    downloading.storage.module_state.set(1, "downloader", "format", "ask")
    send(downloading, link1)
    choice = [data for _, data in bot.last.buttons][0]
    press(downloading, choice)
    press(downloading, choice)
    assert asked_for == [(link1, "video")]
    assert bot.last.text == "Sorry, this button does not work anymore... 😥"


def test_two_links_waiting_for_a_choice_keep_apart(downloading, bot, asked_for):
    downloading.storage.module_state.set(1, "downloader", "format", "ask")
    downloading.router.handle_message(make_message(link1, message_id=101))
    downloading.router.wait_for_tasks()
    first = [data for _, data in bot.last.buttons][0]
    downloading.router.handle_message(make_message(insecure_link1, message_id=102))
    downloading.router.wait_for_tasks()
    downloading.router.handle_callback(make_callback(first, message_id=bot.last.message_id))
    downloading.router.wait_for_tasks()
    assert asked_for == [(link1, "video")]


def test_the_command_leads_to_the_settings(app, bot):
    send(app, "/downloader")
    assert ("⚙️ Settings", "core:settings:downloader") in bot.last.buttons


def test_the_settings_show_the_current_format(app, bot):
    send(app, "/settings")
    press(app, "core:settings:downloader")
    assert bot.last.text.startswith("<b>⚙️ Settings &gt; 📥 Downloader:</b>")
    assert "Now: <i>🎬 Video (mp4)</i>" in bot.last.text
    assert [text for text, data in bot.last.buttons if data.startswith("downloader:")] == [
        "🎬 Video (mp4)", "🎵 Sound (mp3)", "❓ Ask every time"]


def test_picking_a_format_rewrites_the_settings_in_place(app, bot):
    send(app, "/settings")
    press(app, "core:settings:downloader")
    screen = bot.last.message_id
    press(app, "downloader:format:ask")
    assert bot.last.message_id == screen
    assert "Now: <i>❓ Ask every time</i>" in bot.last.text
    assert app.storage.module_state.get(1, "downloader", "format") == "ask"


def test_an_unknown_format_is_refused(app, bot):
    send(app, "/settings")
    press(app, "core:settings:downloader")
    press(app, "downloader:format:gif")
    assert bot.last.text == "Sorry, this button does not work anymore... 😥"
    assert app.storage.module_state.get(1, "downloader", "format") is None


def test_sound_is_asked_for_as_mp3(tmp_path):
    asked = options(tmp_path, "audio")
    assert asked['format'] == "bestaudio/best"
    assert asked['postprocessors'][0]['preferredcodec'] == "mp3"
    assert 'merge_output_format' not in asked


def test_a_video_is_not_turned_into_sound(tmp_path):
    asked = options(tmp_path)
    assert 'postprocessors' not in asked
    assert asked['merge_output_format'] == "mp4"


def test_ffmpeg_that_does_not_run_counts_as_missing(monkeypatch, tmp_path):
    broken = tmp_path / "ffmpeg"
    broken.write_text("#!/bin/sh\nexit 1\n")
    broken.chmod(0o755)
    monkeypatch.setattr(downloader.shutil, "which", lambda _name: str(broken))
    downloader.has_ffmpeg.cache_clear()
    try:
        assert not downloader.has_ffmpeg()
    finally:
        downloader.has_ffmpeg.cache_clear()


megabyte = 2 ** 20


def stream(format_id: str, height: int | None = None, size: int | None = None, is_sound: bool = False) -> dict:
    return {'format_id': format_id, 'url': "https://example.com/" + format_id, 'height': height, 'filesize': size,
            'ext': "m4a" if is_sound else "mp4", 'vcodec': "none" if is_sound else "avc1",
            'acodec': "mp4a" if is_sound else "none", 'tbr': 128 if is_sound else height}


def video_info(*streams: dict, **fields) -> dict:
    return {'id': "x", 'title': "A film", 'extractor': "generic", 'extractor_key': "Generic",
            'webpage_url': link1, 'formats': list(streams), **fields}


@pytest.fixture
def with_ffmpeg(monkeypatch):
    monkeypatch.setattr(downloader, "has_ffmpeg", lambda: True)


def test_the_best_quality_that_fits_comes_first(tmp_path, with_ffmpeg):
    info = video_info(stream("a", size=4 * megabyte, is_sound=True), stream("v1080", 1080, 90 * megabyte),
                      stream("v720", 720, 40 * megabyte), stream("v480", 480, 20 * megabyte))
    wanted = downloader.video_formats(options(tmp_path), info, 50 * megabyte)
    assert wanted == [downloader.video_format(720), downloader.video_format(480)]


def test_sound_and_picture_count_together(tmp_path, with_ffmpeg):
    info = video_info(stream("a", size=15 * megabyte, is_sound=True), stream("v720", 720, 40 * megabyte),
                      stream("v480", 480, 20 * megabyte))
    assert downloader.video_formats(options(tmp_path), info, 50 * megabyte) == [downloader.video_format(480)]


def test_a_size_nobody_knows_is_still_tried(tmp_path, with_ffmpeg):
    info = video_info(stream("a", is_sound=True), stream("v720", 720), stream("v480", 480))
    assert downloader.video_formats(options(tmp_path), info, 50 * megabyte)[0] == downloader.video_format()


def test_nothing_fits_when_even_the_smallest_is_too_big(tmp_path, with_ffmpeg):
    info = video_info(stream("a", size=4 * megabyte, is_sound=True), stream("v480", 480, 90 * megabyte))
    assert downloader.video_formats(options(tmp_path), info, 50 * megabyte) == []


def test_a_film_too_big_after_all_is_tried_again_one_size_down(tmp_path, monkeypatch, with_ffmpeg):
    info = video_info(stream("a", is_sound=True), stream("v720", 720), stream("v480", 480))
    monkeypatch.setattr(downloader, "look_up", lambda _options, _url: info)
    tried = []

    def fetch(fetch_options, _info):
        tried.append(fetch_options['format'])
        make_file(str(tmp_path), "film.mp4", 200 if len(tried) == 1 else 50)

    monkeypatch.setattr(downloader, "fetch", fetch)
    found = downloader.download(link1, str(tmp_path), 100)
    assert tried == [downloader.video_format(), downloader.video_format(480)]
    assert found is not None and os.path.getsize(found) == 50


def test_sound_gets_its_tags_and_a_bitrate_that_fits(tmp_path, monkeypatch):
    info = video_info(title="Rick Astley - Never Gonna Give You Up (Official Video)", duration=60 * 60)
    monkeypatch.setattr(downloader, "look_up", lambda _options, _url: info)
    seen = {}

    def fetch(fetch_options, fetched):
        seen['tags'] = (fetched['artist'], fetched['track'])
        seen['bitrate'] = fetch_options['postprocessors'][0]['preferredquality']
        make_file(str(tmp_path), "Rick Astley - Never Gonna Give You Up.mp3")

    monkeypatch.setattr(downloader, "fetch", fetch)
    found = downloader.download(link1, str(tmp_path), 50 * megabyte, "audio")
    assert found is not None
    assert seen == {'tags': ("Rick Astley", "Never Gonna Give You Up"), 'bitrate': "110"}
    assert os.path.basename(found) == "Rick Astley - Never Gonna Give You Up.mp3"


@pytest.mark.parametrize("fields, expected", [
    ({'artist': "Daft Punk", 'track': "One More Time", 'title': "whatever"}, ("Daft Punk", "One More Time")),
    ({'title': "Queen - Bohemian Rhapsody [Official Video Remastered]"}, ("Queen", "Bohemian Rhapsody")),
    ({'title': "Bohemian Rhapsody (Lyrics)", 'channel': "Queen - Topic"}, ("Queen", "Bohemian Rhapsody")),
    ({'title': "My holiday", 'uploader': "Ania"}, ("Ania", "My holiday")),
    ({'title': "Live (2019)", 'channel': "Band"}, ("Band", "Live (2019)")),
])
def test_tags_fall_back_step_by_step(fields, expected):
    assert downloader.tags(fields) == expected


@pytest.mark.parametrize("duration, expected", [
    (None, 192), (3 * 60, 192), (60 * 60, 110), (10 * 60 * 60, 32)])
def test_the_bitrate_keeps_sound_under_the_limit(duration, expected):
    assert downloader.bitrate(duration, 50 * megabyte) == expected


def test_sound_is_tagged_and_gets_a_cover(tmp_path):
    keys = [one['key'] for one in options(tmp_path, "audio")['postprocessors']]
    assert keys == ["FFmpegExtractAudio", "FFmpegMetadata", "FFmpegThumbnailsConvertor", "EmbedThumbnail"]
    assert options(tmp_path, "audio")['outtmpl'].endswith("%(artist).60B - %(track).80B.%(ext)s")


def test_a_left_over_cover_is_not_taken_for_the_sound(tmp_path):
    make_file(str(tmp_path), "A - B.jpg")
    make_file(str(tmp_path), "A - B.mp3")
    found = downloader.downloaded_file(str(tmp_path), 1000)
    assert found is not None and found.endswith(".mp3")


def test_a_redirect_is_followed_once_before_anything_else(monkeypatch):
    calls = []

    class Tool:
        def __init__(self, _options):
            self.calls = calls

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def extract_info(self, url, **_values):
            self.calls.append(url)
            return {'_type': "url", 'url': "https://example.com/real"} if url == link1 else video_info()

    monkeypatch.setattr("modules.external.downloader.module.YoutubeDL", Tool)
    assert downloader.look_up({}, link1)['title'] == "A film"
    assert calls == [link1, "https://example.com/real"]
