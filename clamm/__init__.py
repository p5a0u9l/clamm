""" clamm initialize """
import os
import json


def get_config_path():
    """ get_config_path """
    return os.path.join(os.environ["HOME"], '.config', 'clamm', 'config.json')


def get_config():
    """ get_config """
    with open(get_config_path()) as fptr:
        config = json.load(fptr)

    return config


config = get_config()
lib_home = os.path.join(os.environ['HOME'], "music")
cfg_home = os.path.join(os.environ['HOME'], ".config", "clamm")
config['path'] = {
        "pcm": os.path.join(lib_home, "streams", "pcm"),
        "wav": os.path.join(lib_home, "streams", "wav"),
        "playlist": os.path.join(lib_home, "playlists"),
        "osa": os.path.join(cfg_home, "osa"),
        "envelopes": os.path.join(cfg_home, "envelopes"),
        "database": os.path.join(cfg_home, "tags.json"),
        "troubled_tracks": os.path.join(cfg_home, "troubled_tracks.json")
    }
