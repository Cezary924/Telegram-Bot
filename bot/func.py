def read_file(name, path):
    try:
        with open(path) as f:
            x = f.readlines()
        f.close()
    except OSError:
        print("Open error: Could not open the \'telegram.txt\' file.")
    return x