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
    p = argparse.ArgumentParser(
            prog="CLAMM",
            description="""
            CLassical Music Manager
            """)
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
            help="""Commands for acting on each audio file in the library,
            or a specified directory under the library.""")

    lib_p.add_argument(
                "-d", "--dir", type=str, default=config["path"]["library"],
                help="the target directory (default: config['path']['library'])")

    lib_subps = lib_p.add_subparsers(dest="sub_cmd")

     # ACTION
    lib_act_p = lib_subps.add_parser(
            "action",
            help="""
            Apply one of the many small(er) library maintenance actions.
            """)

    lib_act_p.add_argument(
                "--prune_artist_tags", type=str, default="",
                help="""
                Conform artist/albumartist tag key names by applying
                config['library']['tags']['prune_artist'] rule.
                e.g., ALBUMARTIST instead of ALBUM_ARTIST
                """)

    lib_act_p.add_argument(
                "--remove_junk_tags", type=str, default="",
                help="""
                Similar to prune_artist_tags, but indiscriminately
                removes tags in config['library']['tags']['junk'].
                Example:
                    $ clamm library action --remove_junk_tags
                """)

    lib_act_p.add_argument(
                "--delete_tag_globber", type=str, default="",
                help="""
                Unlike `remove_junk_tags`, allows removing a set of similarly
                named tags, as in the MUSICBRAINZ_* tags, without cluttering
                the junk list with excessive entries.
                """)

    lib_init_p = lib_subps.add_parser("initialize",
                                      help="initialize a new folder " +
                                      "/ library by applying a sequence " +
                                      "of initializing actions")

    lib_sync_p = lib_subps.add_parser("synchronize", help="""
                                       synchronize the library file tags with
                                       the tags database""")

    lib_play_p = lib_subps.add_parser("playlist", help="")

    lib_play_p.add_argument(
            "-q", '--query', type=str, nargs='+',
            help="""structure --> TAG_KEY TRACK_RELATION TAG_VALUE SET_OPERATOR
            example --> ARRANGMENT contains guitar AND COMPOSER contains
            BACH""")

    return p


# functor wrappers
def tags_show(args):
    with open(config["path"]["database"]) as db:
        tags = json.load(db)
    print(json.dumps(tags, ensure_ascii=False, indent=4))


def tags_edit(args):
    call([os.environ["EDITOR"], config["path"]["database"]])


def config_show(args):
    print(json.dumps(config, ensure_ascii=False, indent=4))


def config_edit(args):
    call([os.environ["EDITOR"], config["path"]["config"]])


def streams_tracks(args):
    stream2tracks.main(args.streampath)


def streams_listing(args):
    listing2streams.main(args.listing)


def streams_stream(args):
    streams.main(args)


def library_action(args):
    import bpdb; bpdb.set_trace()
    clamm.library.audiolib.AudioLib(args).walker(args.action)


def library_initialize(args):
    clamm.library.audiolib.AudioLib(args).initialize()


def library_synchronize(args):
    clamm.library.audiolib.AudioLib(args).synchronize()


def library_playlist(args):
    clamm.library.audiolib.AudioLib(args).playlist()


# define `functor` function lookup
# each key/val pair follows following format
#   "subcommand_command": subcommand_command
functors = {
            "streams_listing": streams_listing,
            "streams_tracks": streams_tracks,
            "streams_stream": streams_stream,
            "tags_show": tags_show,
            "tags_edit": tags_edit,
            "config_show": config_show,
            "config_edit": config_edit,
            "library_action": library_action,
            "library_initialize": library_initialize,
            "library_synchronize": library_synchronize,
            "library_playlist": library_playlist
            }
