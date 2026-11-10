import os

os.environ["CAPTCHA_TEST_MODE"] = "1"

try:
    from backend.app import config
    config.CAPTCHA_TEST_MODE = True
except ImportError:
    pass

