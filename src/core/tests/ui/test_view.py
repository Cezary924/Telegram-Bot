from core.testing import not_none
from core.ui.keyboard import Button
from core.ui.view import View, render, render_text


def test_view_defaults():
    view = View("text1")
    assert view.buttons == [] and view.heading == ""
    assert view.name == "" and view.argument is None
    assert not view.is_screen
    assert view.columns == 1 and view.parse_mode == "Markdown"


def test_a_named_view_is_a_screen():
    assert View("text1", name="view1").is_screen


def test_views_do_not_share_their_lists():
    View("text1").buttons.append(Button("text2"))
    assert View("text3").buttons == []


def test_text_without_a_heading():
    assert render_text(View("text1"), []) == "text1"


def test_text_with_a_heading():
    assert render_text(View("text1"), ["one"]) == "*one:*\n\ntext1"


def test_text_joins_a_longer_heading():
    assert render_text(View("text1"), ["one", "two", "three"]) == "*one > two > three:*\n\ntext1"


def test_a_view_may_ask_for_no_heading_at_all():
    assert View("text1", heading=None).heading is None


def test_render_returns_text_and_markup():
    view = View("text1", buttons=[Button("text2", "action1")])
    text, markup = render(view, "module1")
    assert text == "text1"
    assert not_none(markup).keyboard[0][0].callback_data == "module1:action1"


def test_render_without_buttons_has_no_markup():
    text, markup = render(View("text1"), "module1")
    assert text == "text1" and markup is None


controls = [Button.back("back"), Button.home("home"), Button.close("close")]


def test_the_controls_are_added_last():
    view = View("text1", buttons=[Button("text2", "action1")], name="view1")
    _, markup = render(view, "module1", controls)
    keyboard = not_none(markup).keyboard
    assert [button.callback_data for button in keyboard[0]] == ["module1:action1"]
    assert [button.callback_data for button in keyboard[-1]] == ["core:back", "core:home",
                                                                 "core:close"]


def test_the_controls_alone_still_make_a_markup():
    _, markup = render(View("text1", name="view1"), "module1", controls)
    assert not_none(markup).keyboard[0][0].callback_data == "core:back"


def test_a_view_that_is_no_screen_gets_no_controls():
    _, markup = render(View("text1", buttons=[Button("text2", "action1")]), "module1", controls)
    assert [len(row) for row in not_none(markup).keyboard] == [1]


def test_render_does_not_mutate_the_view():
    view = View("text1", buttons=[Button("text2", "action1")], name="view1")
    render(view, "module1", controls)
    render(view, "module1", controls)
    assert len(view.buttons) == 1


def test_the_controls_always_keep_their_own_row():
    buttons = [Button("text" + str(index), "action" + str(index)) for index in range(4)]
    view = View("text1", buttons=buttons, name="view1", columns=2)
    _, markup = render(view, "module1", controls)
    keyboard = not_none(markup).keyboard
    assert [len(row) for row in keyboard] == [2, 2, 3]
