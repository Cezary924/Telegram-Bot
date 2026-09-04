from core.testing import not_none
from core.ui.keyboard import Button
from core.ui.view import View, render, render_text


def test_view_defaults():
    view = View("text1")
    assert view.buttons == [] and view.path == []
    assert view.name == "" and view.argument is None
    assert not view.is_screen
    assert view.columns == 1 and view.parse_mode == "Markdown"


def test_a_named_view_is_a_screen():
    assert View("text1", name="view1").is_screen


def test_views_do_not_share_their_lists():
    View("text1").buttons.append(Button("text2"))
    assert View("text3").buttons == []


def test_text_without_a_path():
    assert render_text(View("text1")) == "text1"


def test_text_with_a_path():
    assert render_text(View("text1", path=["one"])) == "*one:*\n\ntext1"


def test_text_joins_a_longer_path():
    view = View("text1", path=["one", "two", "three"])
    assert render_text(view) == "*one > two > three:*\n\ntext1"


def test_render_returns_text_and_markup():
    view = View("text1", buttons=[Button("text2", "action1")])
    text, markup = render(view, "module1")
    assert text == "text1"
    assert not_none(markup).keyboard[0][0].callback_data == "module1:action1"


def test_render_without_buttons_has_no_markup():
    text, markup = render(View("text1"), "module1")
    assert text == "text1" and markup is None


def test_return_button_is_added_last():
    view = View("text1", buttons=[Button("text2", "action1")], name="view1")
    _, markup = render(view, "module1", "back")
    keyboard = not_none(markup).keyboard
    assert [button[0].callback_data for button in keyboard] == ["module1:action1", "core:back"]
    assert keyboard[-1][0].text == "back"


def test_return_button_alone_still_makes_a_markup():
    _, markup = render(View("text1", name="view1"), "module1", "back")
    assert not_none(markup).keyboard[0][0].callback_data == "core:back"


def test_render_does_not_mutate_the_view():
    view = View("text1", buttons=[Button("text2", "action1")], name="view1")
    render(view, "module1", "back")
    render(view, "module1", "back")
    assert len(view.buttons) == 1


def test_return_button_always_keeps_its_own_row():
    buttons = [Button("text" + str(index), "action" + str(index)) for index in range(4)]
    view = View("text1", buttons=buttons, name="view1", columns=2)
    _, markup = render(view, "module1", "back")
    keyboard = not_none(markup).keyboard
    assert [len(row) for row in keyboard] == [2, 2, 1]
    assert keyboard[-1][0].callback_data == "core:back"
