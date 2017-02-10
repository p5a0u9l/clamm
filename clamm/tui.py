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
from clamm.streams import listing2streams, stream2tracks, streams
from clamm.util import config


def parse_inputs():
    """
    populate a heirarchical argument parser
    """

    # top-level
    p = argparse.ArgumentParser(prog="CLAMM",
                                description="classical music manager")
    subps = p.add_subparsers(dest="cmd")

    # database
    db_p = subps.add_parser(
            "tags", help="commands providing access to tag database")
    db_subps = db_p.add_subparsers(dest="sub_cmd")
    db_subps.add_parser(
            "edit", help="edit the tags.json file in $EDITOR")
    db_subps.add_parser(
            "show", help="pretty print the tags.json file to stdout")

    # config
    config_p = subps.add_parser(
            "config", help="commands providing access to configuration")
    config_subps = config_p.add_subparsers(dest="sub_cmd")
    config_subps.add_parser(
            "edit", help="edit the config.json file in $EDITOR")
    config_subps.add_parser(
            "show", help="pretty print the current configuration to stdout")

    # streams
    strm_p = subps.add_parser(
            "streams",
            help="commands for working with streams of audio data")
    strm_subps = strm_p.add_subparsers(dest="sub_cmd")
    strm_init_p = strm_subps.add_parser(
            "listing",
            help="""
                 utilize a listing.json file to create a batch of new streams
                 """)

    strm_init_p.add_argument(
                "-l", "--listing", type=str, default="listing.json",
                help="Path to listing.json specification.")

    strm_trck_p = strm_subps.add_parser(
            "tracks",
            help="""
                 process a raw pcm stream to tagged album tracks
                 """)
    strm_trck_p.add_argument(
                "-s", "--streampath", type=str, default="",
                help=" path to a raw pcm stream file ")

    strm_strm_p = strm_subps.add_parser(
            "stream",
            help="""
                 combination of batch listing pcm stream generation and
                 iterative conversion of pcm streams to tagged tracks
                 """)

    strm_strm_p.add_argument(
                "-l", "--listing", type=str, default="listing.json",
                help="Path to listing.json specification.")

    strm_strm_p.add_argument(
                "-s", "--streamfolder", type=str,
                default=config["path"]["pcm"],
                help="""
                     path to directory containing 1 or more pcm streams,
                     defaults to path given in config.json
                     """)

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
def show_tags(args):
    with open(config["path"]["database"]) as db:
        tags = json.load(db)
    print(json.dumps(tags, ensure_ascii=False, indent=4))


def edit_tags(args):
    call([os.environ["EDITOR"], config["path"]["database"]])


def show_config(args):
    print(json.dumps(config, ensure_ascii=False, indent=4))


def edit_config(args):
    call([os.environ["EDITOR"], config["path"]["config"]])


def tracks_streams(args):
    stream2tracks.main(args.streampath)


def listing_streams(args):
    listing2streams.main(args.listing)


def stream_streams(args):
    streams.main(args.streamfolder)


def initialize_library(args):
    clamm.library.audiolib.AudioLib(args).initialize()


def synchronize_library(args):
    clamm.library.audiolib.AudioLib(args).synchronize()


def playlist_library(args):
    clamm.library.audiolib.AudioLib(args).playlist()


# each key/val pair follows following format
#   commandsubcommand: subcommand_command
functors = {
            "streamslisting": listing_streams,
            "streamstracks": tracks_streams,
            "streamsstream": stream_streams,
            "tagsshow": show_tags,
            "tagsedit": edit_tags,
            "configshow": show_config,
            "configedit": edit_config,
            "libraryinitialize": initialize_library,
            "librarysynchronize": synchronize_library,
            "libraryplaylist": playlist_library
            }
