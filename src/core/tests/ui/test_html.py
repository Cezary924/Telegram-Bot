from core.ui.html import Html, bold, escape, italic, plain


def test_the_three_special_characters_are_escaped():
    assert escape("a < b & c > d") == "a &lt; b &amp; c &gt; d"


def test_quotes_are_left_as_they_are():
    assert escape("it's \"fine\"") == "it's \"fine\""


def test_anything_is_turned_into_text_first():
    assert escape(42) == "42"


def test_markup_is_not_escaped_twice():
    assert escape(Html("<b>kept</b>")) == "<b>kept</b>"


def test_bold_and_italic_escape_what_they_wrap():
    assert bold("<me>") == "<b>&lt;me&gt;</b>"
    assert italic("R&D") == "<i>R&amp;D</i>"


def test_bold_and_italic_are_markup_themselves():
    assert isinstance(bold("x"), Html) and isinstance(italic("x"), Html)
    assert bold(italic("x")) == "<b><i>x</i></b>"


def test_plain_takes_the_markup_away():
    assert plain("<b>Weight &amp; Height</b>") == "Weight & Height"


def test_plain_leaves_plain_text_alone():
    assert plain("Weight & Height") == "Weight & Height"
