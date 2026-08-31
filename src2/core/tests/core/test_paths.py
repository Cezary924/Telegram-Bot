import os

from core import paths


def test_dirs_are_absolute():
    for path in [paths.root_dir, paths.src_dir, paths.core_dir, paths.config_dir,
                 paths.db_dir, paths.log_dir, paths.modules_dir]:
        assert os.path.isabs(path)


def test_layout():
    assert paths.core_dir == os.path.join(paths.src_dir, "core")
    assert paths.src_dir == os.path.join(paths.root_dir, "src2")
    assert paths.internal_modules_dir == os.path.join(paths.modules_dir, "internal")
    assert paths.external_modules_dir == os.path.join(paths.modules_dir, "external")


def test_root_holds_project_dirs():
    assert os.path.isdir(paths.config_dir)
    assert os.path.isdir(paths.db_dir)
    assert os.path.isdir(paths.log_dir)


def test_helpers_join_names():
    assert paths.config_file("config.yaml") == os.path.join(paths.config_dir, "config.yaml")
    assert paths.db_file("bot.db") == os.path.join(paths.db_dir, "bot.db")
    assert paths.log_file("log.log") == os.path.join(paths.log_dir, "log.log")


def test_paths_do_not_depend_on_cwd(tmp_path, monkeypatch):
    before = paths.root_dir
    monkeypatch.chdir(tmp_path)
    import importlib
    importlib.reload(paths)
    assert paths.root_dir == before


def test_make_dir_is_idempotent(tmp_path):
    target = str(tmp_path / "a" / "b")
    assert paths.make_dir(target) == target
    assert paths.make_dir(target) == target
    assert os.path.isdir(target)


def test_remove_dir_deletes_tree(tmp_path):
    target = tmp_path / "work"
    (target / "nested").mkdir(parents=True)
    (target / "file.txt").write_text("x")
    (target / "nested" / "file.txt").write_text("x")
    paths.remove_dir(str(target))
    assert not target.exists()


def test_remove_dir_ignores_missing(tmp_path):
    paths.remove_dir(str(tmp_path / "nope"))
