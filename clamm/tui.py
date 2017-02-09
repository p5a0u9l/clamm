#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

"""
this module defines the _t_erminal _u_ser _i_nterface for clamm
"""

# built-ins
import argparse
from subprocess import call
import os
import json

# local
import clamm.library
from clamm.streams import autobatch
from clamm.util import config


def parse_inputs():
    """ populate a heirarchical argument parser """

    # top-level
    p = argparse.ArgumentParser(prog="CLAMM",
                                description="classical music manager")
    subps = p.add_subparsers(dest="cmd")

    # config
    config_p = subps.add_parser(
            "config", help="commands providing access to configuration")
    config_subps = config_p.add_subparsers(dest="sub_cmd")
    config_subps.add_parser("edit",
                            help="edit the config.json file in $EDITOR")
    config_subps.add_parser("show",
                            help="pretty print the current configuration")

    # streams
    bat_p = subps.add_parser(
            "stream",
            help="commands for working with streams of audio data")
    bat_subps = bat_p.add_subparsers(dest="sub_cmd")
    bat_init_p = bat_subps.add_parser("autobatch",
                                      help="utilize the batch_album_" +
                                      "listing.json file to create a batch " +
                                      "of new albums")
    bat_init_p.add_argument(
                "-f", "--file", type=str, default="",
                help="Path to batch_album_listing.json file")
    # library
    lib_p = subps.add_parser(
            "library",
            help="commands for acting on the set or a subset of the library")
    lib_subps = lib_p.add_subparsers(dest="sub_cmd")
    lib_init_p = lib_subps.add_parser("initialize",
                                      help="initialize a new folder " +
                                      "/ library by applying a sequence " +
                                      "of initializing actions")
    lib_init_p.add_argument(
                "-d", "--dir", type=str, default=config["library"],
                help="The target directory, library by default")

    lib_sync_p = lib_subps.add_parser("synchronize", help="""
                                       synchronize the library file tags with
                                       the tags database""")
    lib_sync_p.add_argument("-d", "--dir",
                            type=str, default=config["library"],
                            help="The target directory, library by default")

    lib_play_p = lib_subps.add_parser("playlist", help="")

    lib_play_p.add_argument(
            "-q", '--query', type=str, nargs='+',
            help="""structure --> TAG_KEY TRACK_RELATION TAG_VALUE SET_OPERATOR
            example --> ARRANGMENT contains guitar AND COMPOSER contains
            BACH""")

    return p


# functor wrappers
def show_config(args):
    print(json.dumps(config, ensure_ascii=False, indent=4))


def edit_config(args):
    call([os.environ["EDITOR"], config["path"]["config"]])


def autobatch_stream(args):
    autobatch.main(args)


def initialize_library(args):
    clamm.library.audiolib.AudioLib(args).initialize()


def synchronize_library(args):
    clamm.library.audiolib.AudioLib(args).synchronize()


def playlist_library(args):
    clamm.library.audiolib.AudioLib(args).playlist()


# each key/val pair follows following format
#   commandsubcommand: subcommand_command
functors = {
            "streamautobatch": autobatch_stream,
            "configshow": show_config,
            "configedit": edit_config,
            "libraryinitialize": initialize_library,
            "librarysynchronize": synchronize_library,
            "libraryplaylist": playlist_library
            }
