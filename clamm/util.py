""" utils
"""

import os
import sys
import time
import inspect

import colorama

from clamm import config

SPLIT_REGEX = '&\s*|,\s*|;\s*| - |:\s*|/\s*| feat. | and '
ARTIST_TAG_NAMES = ["ALBUMARTIST_CREDIT",
                    "ALBUM ARTIST",
                    "ARTIST",
                    "ARTIST_CREDIT",
                    "ALBUMARTIST"]
SEC_PER_DAY = 60*60*24


def commit_to_libfile(tagfile):
    """common entry point for writing values from tag database into
    an audiofile.
    """

    # check if differences (or newness) exists
    n_delta_fields, n_tracks_updated = 0, 0
    for k, _ in tagfile.tags.items():
        is_new = k not in tagfile.tag_copy.keys()
        if not is_new:
            is_dif = tagfile.tags[k][0] != tagfile.tag_copy[k][0]
        if is_new or is_dif:
            n_delta_fields += 1

    # short-circuit if no changes to be made
    if n_delta_fields == 0:
        return (n_tracks_updated, n_delta_fields)

    n_tracks_updated += 1
    # prompted or automatic write
    if config["database"]["require_prompt_when_committing"]:
        printr("Proposed: ")
        pretty_dict(sorted(tagfile.tags))

        if not input("Accept? [y]/n: "):
            tagfile.save()

    else:
        tagfile.save()
        printr(
            lambda: [
                sys.stdout.write(
                    colorama.Fore.RED + "." + colorama.Fore.WHITE),
                sys.stdout.flush()])

    return (n_tracks_updated, n_delta_fields)


def size_sampler(filepath):
    """
    return the file size, sampled with a 1 second gap to determine
    if the file is being written to and thus growing
    """

    s0 = os.path.getsize(filepath)
    time.sleep(1)
    s1 = os.path.getsize(filepath)
    return (s0, s1)


def pretty_dict(d):
    for k, v in d.items():
        print("\t{}: {}".format(k, v))


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

    if int(config["verbosity"]) > verbosic_precedence:
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
