""" clamm initialize """
import os
import json

PKG_ROOT = os.path.abspath(os.path.dirname(__file__))


def get_config_path():
    """ get_config_path """
    return os.path.join(os.environ["HOME"], '.config', 'clamm', 'config.json')


def get_config():
    """ get_config """
    with open(get_config_path()) as fptr:
        config = json.load(fptr)

    return config


CONFIG = get_config()   # static at run-time
