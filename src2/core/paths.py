import os

core_dir: str = os.path.dirname(os.path.realpath(__file__))
src_dir: str = os.path.dirname(core_dir)
root_dir: str = os.path.dirname(src_dir)

config_dir: str = os.path.join(root_dir, "config")
db_dir: str = os.path.join(root_dir, "db")
log_dir: str = os.path.join(root_dir, "log")
temp_dir: str = os.path.join(root_dir, "tmp")

modules_dir: str = os.path.join(src_dir, "modules")
internal_modules_dir: str = os.path.join(modules_dir, "internal")
external_modules_dir: str = os.path.join(modules_dir, "external")


def config_file(name: str) -> str:
    return os.path.join(config_dir, name)


def db_file(name: str) -> str:
    return os.path.join(db_dir, name)


def log_file(name: str) -> str:
    return os.path.join(log_dir, name)


def make_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def remove_dir(path: str) -> None:
    if not os.path.isdir(path):
        return
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        if os.path.isdir(item_path):
            remove_dir(item_path)
        else:
            os.remove(item_path)
    os.rmdir(path)
