import logging
import sys

logging.basicConfig(level=logging.DEBUG)


if __name__ == '__main__':
    if sys.platform == "darwin":
        from browser.cocoa.main import main
        main()
    else:
        raise RuntimeError("Unsupported platform")
