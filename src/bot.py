import sys

from core.app import App

if __name__ == "__main__":
    App(is_beta=len(sys.argv) > 1 and sys.argv[1] == "beta").start()
