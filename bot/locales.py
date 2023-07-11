import yaml

# open and read from locale file
def load_locale_file(path):
    try:
        with open(path, encoding='utf8') as f:
            x = yaml.load(f, Loader=yaml.Loader)
        f.close()
    except OSError:
        print("Open error: Could not open the locale file.")
    return x

# create lang dicts
pl = load_locale_file("../locales/pl.yaml")
en = load_locale_file("../locales/en.yaml")