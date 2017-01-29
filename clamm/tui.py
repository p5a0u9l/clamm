#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

"""
this module defines the terminal user interface for clamm
"""

import argparse
from subprocess import call
import os
import json

# local
import clamm.library

# bootstrap config file
cfg_path = os.path.join(os.path.expanduser('~'), '.config', 'clamm', 'config.json')
with open(cfg_path) as f: config = json.load(f)

def parse_inputs():
    """ create heirarchical argument parser """

    # top-level
    p = argparse.ArgumentParser(prog="CLAMM", description="classical music manager")
    subps = p.add_subparsers(dest="cmd")

    # config
    config_p = subps.add_parser("config", \
            help="commands providing access to configuration")
    config_subps = config_p.add_subparsers(dest="sub_cmd")
    configedit_p = config_subps.add_parser("edit", \
            help="edit the config.json file in $EDITOR")
    configshow_p = config_subps.add_parser("show", \
            help="pretty print the current configuration")

    # library
    lib_p = subps.add_parser("library", \
            help="commands for acting on the set or a subset of the library")
    lib_subps = lib_p.add_subparsers(dest="sub_cmd")
    lib_init_p = lib_subps.add_parser("initialize", \
            help="initialize a new folder / library by applying a sequence of initializing actions")
    lib_init_p.add_argument( \
            "-d", "--dir", type=str, default=config["library"], \
            help="The target directory, library by default" \
                )
    lib_sync_p = lib_subps.add_parser("synchronize", \
            help="synchronize the library file tags with the tags database")
    lib_sync_p.add_argument( \
            "-d", "--dir", type=str, default=config["library"], \
            help="The target directory, library by default" \
                )


    # parser.add_argument("-t", "--tag", default="", help="a tag field upon which to act, empty by default")
    # parser.add_argument("-v", "--val", default="", help="the value to apply to tags, empty by default")
    # parser.add_argument("-q", '--query', type=str, nargs='+', \
    #         help=\
    #     """structure   --> TAG_KEY TRACK_RELATION TAG_VALUE SET_OPERATOR ..."""
    #     """\nexample     --> ARRANGMENT contains guitar AND COMPOSER contains BACH""")

    return p

# functer wrappers
def show_config(args):
    print(json.dumps(config, ensure_ascii=False, indent=4))

def edit_config(args):
    call([os.environ["EDITOR"], config["path"]["config"]])

def initialize_library(args):
    pass

def synchronize_library(args):
    clamm.library.audiolib.AudioLib(args).synchronize()

functers = {
            "configshow": show_config, \
            "configedit": edit_config, \
            "libraryinitialize": initialize_library, \
            "librarysynchronize": synchronize_library \
            }


