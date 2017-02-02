#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
import json
from os.path import join, expanduser

# bootstrap config file
cfg_path = join(expanduser('~'), '.config', 'clamm', 'config.json')
with open(cfg_path) as f: config = json.load(f)

SPLIT_REGEX = '&\s*|,\s*|;\s*| - |:\s*|/\s*| feat. | and '

def pretty_dict(d):
    for k, v in d.items():
        printr("\t{}: {}".format(k, v))

def printr(func_or_msg, verbosity=4):
    """ a wrapper that enables clients to not need
    details of controlling printing behavior """

    if config["library"]["verbosity"] > verbosity:
        return

    if isinstance(func_or_msg, str):
        print(func_or_msg)
    else:
        func_or_msg()

def swap_first_last_name(name_str):
    """ if name_str contains a comma (assume it is formatted as Last, First),
        invert and return First Last
        else, invert and return Last, First
    """

    comma_idx = name_str.find(",")
    name_parts = name_str.replace(",", "").split(" ")

    if comma_idx > -1:
        swapd =  "{} {}".format(name_parts[1], name_parts[0])
    else:
        swapd =  "{}, {}".format(name_parts[1], name_parts[0])

    return swapd

