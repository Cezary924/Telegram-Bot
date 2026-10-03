import pytest

from core.i18n import Catalog, flatten, load_locale_file
from core.ui.html import Html, italic

escaped_newline = "\\n"
real_newline = "\n"


@pytest.fixture
def catalog():
    catalog = Catalog()
    catalog.add("module1", "en", {'key1': "one", 'key2': "two"})
    catalog.add("module1", "pl", {'key1': "jeden"})
    catalog.add("module2", "en", {'key1': "other"})
    return catalog


@pytest.fixture
def locales_dir(tmp_path):
    (tmp_path / "en.yaml").write_text("key1: one\n", encoding='utf8')
    (tmp_path / "pl.yaml").write_text("key1: jeden\n", encoding='utf8')
    (tmp_path / "notes.txt").write_text("ignored", encoding='utf8')
    return tmp_path


def test_flatten_keeps_flat_keys():
    assert flatten({'key1': "one", 'key2': "two"}) == {'key1': "one", 'key2': "two"}


def test_flatten_joins_nested_keys_with_a_dot():
    assert flatten({'group': {'key1': "one", 'inner': {'key2': "two"}}}) == {
        'group.key1': "one", 'group.inner.key2': "two"}


def test_flatten_turns_escaped_newlines_into_real_ones():
    assert flatten({'key1': "one" + escaped_newline + "two"}) == {'key1': "one" + real_newline + "two"}


def test_flatten_skips_empty_values():
    assert flatten({'key1': "one", 'key2': None}) == {'key1': "one"}


def test_load_locale_file(tmp_path):
    path = tmp_path / "en.yaml"
    path.write_text("key1: one\ngroup:\n  key2: two\n", encoding='utf8')
    assert load_locale_file(str(path)) == {'key1': "one", 'group.key2': "two"}


def test_load_empty_locale_file(tmp_path):
    path = tmp_path / "en.yaml"
    path.write_text("", encoding='utf8')
    assert load_locale_file(str(path)) == {}


def test_text_in_requested_language(catalog):
    assert catalog.text("module1", "key1", "pl") == "jeden"
    assert catalog.text("module1", "key1", "en") == "one"


def test_text_falls_back_to_default_language(catalog):
    assert catalog.text("module1", "key2", "pl") == "two"


def test_text_falls_back_to_the_default_for_unknown_language(catalog):
    assert catalog.text("module1", "key1", "de") == "one"


def test_namespaces_are_separate(catalog):
    assert catalog.text("module1", "key1", "en") == "one"
    assert catalog.text("module2", "key1", "en") == "other"


def test_another_namespace_can_be_named_explicitly(catalog):
    assert catalog.text("module1", "module2:key1", "en") == "other"


def test_missing_key_is_returned_as_is(catalog, capsys):
    assert catalog.text("module1", "key9", "en") == "module1:key9"
    assert "Missing translation" in capsys.readouterr().out


def test_missing_key_is_reported_only_once(catalog, capsys):
    catalog.text("module1", "key9", "en")
    capsys.readouterr()
    catalog.text("module1", "key9", "en")
    assert capsys.readouterr().out == ""


def test_values_are_formatted_in(catalog):
    catalog.add("module1", "en", {'key3': "hello {name}"})
    assert catalog.text("module1", "key3", "en", name="world") == "hello world"


def test_braces_are_left_alone_without_values(catalog):
    catalog.add("module1", "en", {'key3': "Keep {this} as it is"})
    assert catalog.text("module1", "key3", "en") == "Keep {this} as it is"


def test_a_text_is_escaped_so_it_can_be_sent_as_html(catalog):
    catalog.add("module1", "en", {'key3': "Weight & Height < 2 m"})
    assert catalog.text("module1", "key3", "en") == "Weight &amp; Height &lt; 2 m"


def test_a_value_is_escaped_before_it_goes_in(catalog):
    catalog.add("module1", "en", {'key3': "Hello, {name}"})
    assert catalog.text("module1", "key3", "en", name="<Eve>") == "Hello, &lt;Eve&gt;"


def test_a_formatted_value_keeps_its_markup(catalog):
    catalog.add("module1", "en", {'key3': "Hello, {name}"})
    assert catalog.text("module1", "key3", "en", name=italic("Eve")) == "Hello, <i>Eve</i>"


def test_a_text_is_markup_that_is_not_escaped_again(catalog):
    catalog.add("module1", "en", {'key3': "R&D", 'key4': "In {team}"})
    team = catalog.text("module1", "key3", "en")
    assert isinstance(team, Html)
    assert catalog.text("module1", "key4", "en", team=team) == "In R&amp;D"


def test_has(catalog):
    assert catalog.has("module1", "key1", "pl")
    assert not catalog.has("module1", "key2", "pl")
    assert not catalog.has("module1", "key9", "en")


def test_keys_and_languages(catalog):
    assert catalog.languages() == ["en", "pl"]
    assert catalog.keys("module1", "en") == {'key1', 'key2'}
    assert catalog.keys("module1", "pl") == {'key1'}
    assert catalog.keys("module9", "en") == set()


def test_namespaces(catalog):
    assert catalog.namespaces() == {"module1", "module2"}


def test_load_directory(locales_dir):
    catalog = Catalog()
    assert catalog.load_directory("module1", str(locales_dir)) == ["en", "pl"]
    assert catalog.text("module1", "key1", "pl") == "jeden"
    assert catalog.keys("module1", "en") == {'key1'}


def test_load_directory_that_does_not_exist(tmp_path):
    catalog = Catalog()
    assert catalog.load_directory("module1", str(tmp_path / "nope")) == []
    assert catalog.languages() == []


def test_core_locales_are_loaded():
    catalog = Catalog()
    assert catalog.load_core() == ["en", "pl"]
    assert catalog.text("core", "yes_button", "pl") == "✅ Tak"
    assert catalog.text("core", "consent.agreement.title", "en").startswith("✋")


def test_core_locales_have_the_same_keys_in_every_language():
    catalog = Catalog()
    languages = catalog.load_core()
    keys = catalog.keys("core", languages[0])
    for language in languages[1:]:
        assert catalog.keys("core", language) == keys
