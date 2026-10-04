import json
import os
from typing import cast

import pytest
from yt_dlp import YoutubeDL
from yt_dlp.networking import Request

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
        return [(make_file(path, "sound.mp3" if kind == "audio" else "video.mp4"), kind)]

    monkeypatch.setattr(downloader, "download", download)
    monkeypatch.setattr(downloader, "has_only_pictures", lambda _path, _url: False)
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
    monkeypatch.setattr(downloader, "download", lambda _url, _path, _limit, _kind: [])
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
        return [(make_file(path), "video")]

    monkeypatch.setattr(downloader, "download", remember)
    send(app, link1)
    assert used and not os.path.exists(used[0])


def test_a_guest_gets_nothing(downloading, bot):
    downloading.storage.users.set_role(1, Role.GUEST)
    send(downloading, link1)
    assert bot.last.text.startswith("You do not have access to")
    assert ("🙋 Ask for access", "core:request:downloader") in bot.last.buttons
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
    monkeypatch.setattr(downloader, "look_up", lambda _tool, _url: info)
    tried = []

    def fetch(fetch_options, _info):
        tried.append(fetch_options['format'])
        make_file(os.path.dirname(fetch_options['outtmpl']), "film.mp4", 200 if len(tried) == 1 else 50)

    monkeypatch.setattr(downloader, "fetch", fetch)
    found = downloader.download(link1, str(tmp_path), 100)
    assert tried == [downloader.video_format(), downloader.video_format(480)]
    assert [(os.path.getsize(path), kind) for path, kind in found] == [(50, "video")]


def test_sound_gets_its_tags_and_a_bitrate_that_fits(tmp_path, monkeypatch):
    info = video_info(stream("v720", 720), title="Rick Astley - Never Gonna Give You Up (Official Video)",
                      duration=60 * 60)
    monkeypatch.setattr(downloader, "look_up", lambda _tool, _url: info)
    seen = {}

    def fetch(fetch_options, fetched):
        seen['tags'] = (fetched['artist'], fetched['track'])
        seen['bitrate'] = fetch_options['postprocessors'][0]['preferredquality']
        make_file(os.path.dirname(fetch_options['outtmpl']), "Rick Astley - Never Gonna Give You Up.mp3")

    monkeypatch.setattr(downloader, "fetch", fetch)
    found = downloader.download(link1, str(tmp_path), 50 * megabyte, "audio")
    assert seen == {'tags': ("Rick Astley", "Never Gonna Give You Up"), 'bitrate': "110"}
    assert [(os.path.basename(path), kind) for path, kind in found] == [
        ("Rick Astley - Never Gonna Give You Up.mp3", "audio")]


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


def test_a_redirect_is_followed_once_before_anything_else():
    calls = []

    class Tool:
        def __init__(self):
            self.calls = calls

        def extract_info(self, url, **_values):
            self.calls.append(url)
            return {'_type': "url", 'url': "https://example.com/real"} if url == link1 else video_info()

    assert downloader.look_up(as_tool(Tool()), link1)['title'] == "A film"
    assert calls == [link1, "https://example.com/real"]


def storyboard(format_id: str, height: int) -> dict:
    return {'format_id': format_id, 'url': "https://example.com/" + format_id, 'height': height,
            'ext': "mhtml", 'vcodec': "none", 'acodec': "none", 'protocol': "mhtml"}


def test_storyboards_are_not_qualities_of_the_film():
    info = video_info(stream("v720", 720), stream("v480", 480), storyboard("sb0", 90), storyboard("sb1", 45))
    assert downloader.heights(info) == [480]


def test_a_quality_nothing_matches_is_skipped_rather_than_fatal(tmp_path, with_ffmpeg):
    info = video_info(stream("a", size=4 * megabyte, is_sound=True), stream("v720", 720, 90 * megabyte))
    assert downloader.resolve(options(tmp_path), info, downloader.video_format(90)) is None


def test_a_film_with_storyboards_still_finds_its_qualities(tmp_path, with_ffmpeg):
    info = video_info(stream("a", size=4 * megabyte, is_sound=True), stream("v1080", 1080, 90 * megabyte),
                      stream("v720", 720, 40 * megabyte), storyboard("sb0", 90), storyboard("sb1", 45))
    assert downloader.video_formats(options(tmp_path), info, 50 * megabyte) == [downloader.video_format(720)]


def test_every_pass_shares_the_cookies_of_the_workspace(tmp_path):
    assert options(tmp_path)['cookiefile'] == os.path.join(str(tmp_path), "cookies.txt")
    assert options(tmp_path, "audio")['cookiefile'] == os.path.join(str(tmp_path), "cookies.txt")


def test_the_cookies_are_neither_sent_nor_cleared(tmp_path):
    make_file(str(tmp_path), "cookies.txt")
    assert downloader.downloaded_file(str(tmp_path), 1000) is None
    make_file(str(tmp_path), "film.mp4")
    downloader.clear(str(tmp_path))
    assert os.listdir(str(tmp_path)) == ["cookies.txt"]


jpeg_body = b"\xff\xd8\xff\xe0" + b"x" * 60
webp_body = b"RIFF" + b"\x00" * 4 + b"WEBPVP8 " + b"x" * 60


class Page:
    def __init__(self, body: bytes):
        self.body = body

    def read(self) -> bytes:
        return self.body


class Web:
    def __init__(self, pages: dict, refuses_chrome: bool = False):
        self.pages = pages
        self.refuses_chrome = refuses_chrome
        self.asked: list[tuple[str, bool]] = []

    def urlopen(self, request: Request | str) -> Page:
        url = request.url if isinstance(request, Request) else request
        as_chrome = isinstance(request, Request) and bool(request.extensions.get('impersonate'))
        self.asked.append((url, as_chrome))
        if as_chrome and self.refuses_chrome:
            raise downloader.RequestError("no impersonation")
        return Page(self.pages[url])


def as_tool(fake) -> YoutubeDL:
    return cast(YoutubeDL, fake)


def tiktok_page(*urls: str) -> bytes:
    images = [{'imageURL': {'urlList': [url, url + "?other"]}} for url in urls]
    item = {'imagePost': {'images': images}}
    data = {'__DEFAULT_SCOPE__': {'webapp.video-detail': {'itemInfo': {'itemStruct': item}}}}
    return ('<html><script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">'
            + json.dumps(data) + '</script></html>').encode()


tiktok_video_page = "https://www.tiktok.com/@someone/video/123"


@pytest.mark.parametrize("url, expected", [
    ("https://www.tiktok.com/@someone/photo/123?_r=1", "https://www.tiktok.com/@someone/video/123?_r=1"),
    ("https://www.tiktok.com/@someone/video/123", "https://www.tiktok.com/@someone/video/123"),
    ("https://www.instagram.com/p/abc/", "https://www.instagram.com/p/abc/"),
])
def test_a_tiktok_photo_post_is_read_from_its_video_page(url, expected):
    assert downloader.page_of(url) == expected


def test_a_carousel_shares_where_it_came_from_with_every_element():
    info = {'_type': "playlist", 'extractor': "Instagram", 'extractor_key': "Instagram", 'webpage_url': link1,
            'entries': [{'id': "1"}, {'id': "2"}]}
    assert [(one['id'], one['extractor_key']) for one in downloader.entries_of(info)] == [
        ("1", "Instagram"), ("2", "Instagram")]


@pytest.mark.parametrize("formats, expected", [
    ([stream("v720", 720)], True), ([stream("a", is_sound=True)], False), ([], False)])
def test_only_something_with_a_picture_track_is_a_video(formats, expected):
    assert downloader.is_video({'formats': formats}) == expected


def test_the_largest_picture_comes_last():
    entry = {'thumbnails': [{'url': "https://x/small"}, {'url': "https://x/large"}]}
    assert downloader.best_picture(entry) == "https://x/large"


def test_tiktok_pictures_come_from_the_page_asked_for_as_chrome():
    web = Web({tiktok_video_page: tiktok_page("https://x/1.jpeg", "https://x/2.jpeg")})
    info = {'extractor_key': "TikTok", 'webpage_url': tiktok_video_page, 'formats': [stream("a", is_sound=True)]}
    assert downloader.picture_urls(as_tool(web), info, [info]) == ["https://x/1.jpeg", "https://x/2.jpeg"]
    assert web.asked == [(tiktok_video_page, True)]


def test_without_impersonation_the_page_is_asked_for_plainly():
    web = Web({tiktok_video_page: tiktok_page("https://x/1.jpeg")}, refuses_chrome=True)
    assert downloader.fetch_page(as_tool(web), tiktok_video_page).startswith(b"<html>")
    assert web.asked == [(tiktok_video_page, True), (tiktok_video_page, False)]


def test_a_tiktok_video_has_no_pictures_to_look_for():
    web = Web({})
    info = {'extractor_key': "TikTok", 'webpage_url': tiktok_video_page, 'formats': [stream("v720", 720)]}
    assert downloader.picture_urls(as_tool(web), info, [info]) == []
    assert web.asked == []


def test_a_carousel_gives_the_pictures_of_its_pictures_only():
    picture = {'thumbnails': [{'url': "https://x/p1"}]}
    film = {'formats': [stream("v720", 720)], 'thumbnails': [{'url': "https://x/cover"}]}
    info = {'extractor_key': "Instagram"}
    assert downloader.picture_urls(as_tool(Web({})), info, [picture, film, picture]) == ["https://x/p1", "https://x/p1"]


def test_pictures_are_saved_in_order_and_a_jpeg_stays_as_it_is(tmp_path):
    web = Web({"https://x/1": jpeg_body, "https://x/2": jpeg_body})
    saved = downloader.save_pictures(as_tool(web), ["https://x/1", "https://x/2"], str(tmp_path))
    assert [os.path.basename(one) for one in saved] == ["00.jpg", "01.jpg"]


def test_a_webp_without_ffmpeg_is_kept_under_its_own_name(tmp_path, monkeypatch):
    monkeypatch.setattr(downloader, "has_ffmpeg", lambda: False)
    saved = downloader.save_pictures(as_tool(Web({"https://x/1": webp_body})), ["https://x/1"], str(tmp_path))
    assert [os.path.basename(one) for one in saved] == ["00.webp"]


def test_a_webp_is_turned_into_a_jpeg_by_ffmpeg(tmp_path, monkeypatch, with_ffmpeg):
    ran = []
    monkeypatch.setattr(downloader.subprocess, "run", lambda command, **_values: ran.append(command))
    saved = downloader.save_pictures(as_tool(Web({"https://x/1": webp_body})), ["https://x/1"], str(tmp_path))
    assert [os.path.basename(one) for one in saved] == ["00.jpg"]
    assert ran[0][-1].endswith("00.jpg") and ran[0][ran[0].index("-i") + 1].endswith("00.webp")


def test_a_picture_over_the_telegram_limit_is_left_out(tmp_path, monkeypatch):
    monkeypatch.setattr(downloader, "photo_limit", 10)
    assert downloader.save_pictures(as_tool(Web({"https://x/1": jpeg_body})), ["https://x/1"], str(tmp_path)) == []


@pytest.fixture
def mixed_post(app, monkeypatch):
    def download(_url, path, _limit, kind):
        return [(make_file(path, "00.jpg"), "photo"), (make_file(path, "01.jpg"), "photo"),
                (make_file(path, "film.mp4"), kind)]

    monkeypatch.setattr(downloader, "download", download)
    monkeypatch.setattr(downloader, "has_only_pictures", lambda _path, _url: False)
    return app


def test_pictures_come_as_one_album_and_films_after_them(mixed_post, bot, capsys):
    send(mixed_post, link1)
    assert bot.albums == [["00.jpg", "01.jpg"]]
    assert [(file.kind, file.name) for file in bot.files] == [("video", "film.mp4")]
    assert "Downloaded 2 photos, a video" in capsys.readouterr().out


def test_a_post_of_pictures_only_is_sent_without_asking(app, bot, monkeypatch):
    app.storage.module_state.set(1, "downloader", "format", "ask")
    monkeypatch.setattr(downloader, "has_only_pictures", lambda _path, _url: True)
    monkeypatch.setattr(downloader, "download",
                        lambda _url, path, _limit, _kind: [(make_file(path, "00.jpg"), "photo")])
    send(app, link1)
    assert "How should I send it?" not in bot.texts()[-1]
    assert [(file.kind, file.name) for file in bot.files] == [("photo", "00.jpg")]


@pytest.mark.parametrize("pieces, expected", [
    ([("a", "video")], "a video"), ([("a", "audio")], "a sound"),
    ([("a", "photo"), ("b", "photo"), ("c", "video")], "2 photos, a video")])
def test_the_log_counts_what_was_sent(pieces, expected):
    assert downloader.summary(pieces) == expected
