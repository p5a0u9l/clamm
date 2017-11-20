""" utilities
"""
import os
import inspect

import colorama

from clamm import CONFIG

ARTIST_TAG_NAMES = ["ALBUMARTIST_CREDIT",
                    "ALBUM ARTIST",
                    "ARTIST",
                    "ARTIST_CREDIT",
                    "ALBUMARTIST"]
SPLIT_REGEX = r'&\s*|,\s*|;\s*| - |:\s*|/\s*| feat. | and '
SEC_PER_DAY = 60*60*24


def pretty_dict(dict_):
    """ lazy """
    for key, val in dict_.items():
        print("\t{}: {}".format(key, val))


def printr(func_or_msg, verbosic_precedence=3, caller=True):
    """a utility that enables callers to simplify printing behavior.

        Args:
            func_or_msg: Either a function handle to call or a message string
            to print.

        Kwargs:
            verbosic_precedence: Integer setting verbosity level.
            If not set, the message is printed if the config value
            `verbosity` is higher than the default value.
            The caller can short-circuit the config value by setting
            the kwarg.
            caller: Bool indicating whether or not to print the caller name.
    """

    if int(CONFIG["library"]["verbosity"]) > verbosic_precedence:
        return

    caller_name = ""
    if caller:
        caller_name = inspect.stack()[1][3]

    if isinstance(func_or_msg, str):
        print("\n" +
              colorama.Fore.BLUE + caller_name +
              colorama.Fore.WHITE + ": " + func_or_msg)
    else:
        func_or_msg()

def resolve(config_path):
    """ resolve config paths """
    head = config_path[0]
    tail = config_path[1:]
    head = {True: "/", False: os.environ["HOME"]}[head == "root"]
    tail = os.path.sep.join(tail)
    return os.path.join(head, tail)
