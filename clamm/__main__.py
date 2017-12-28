""" module containing command line interface implementation
and utilities.
"""

import argparse
from subprocess import call
import os
import json

import clamm.util
import clamm.audiolib
import clamm.streams
from clamm import config, get_config_path, installed_location


def create_library_parsers(subps):
    """creates library sub-parsers
    """
    lib_p = subps.add_parser(
        "library",
        help="""Commands for acting on each audio file in the library,
            or a specified directory under the library.""")

    lib_p.add_argument(
        "-d", "--dir", type=str, default=config["path"]["library"],
        help="""
                the target directory (default: config['path']['library'])
                """)

    lib_subps = lib_p.add_subparsers(dest="sub_cmd")

    # ACTION
    lib_act_p = lib_subps.add_parser(
        "action",
        help="""
        Apply one of the many small(er) library actions.
        Actions can be chained together, as in
        $ clamm library action --prune_artist_tags --synchronize_artist
            """)

    lib_act_p.add_argument("-k", "--key", help="tag key")
    lib_act_p.add_argument("-v", "--val", help="tag value")

    lib_act_p.add_argument(
        "--prune_artist_tags", action="store_true",
        help="""
                Conform artist/albumartist tag key names by applying
                config['library']['tags']['prune_artist'] rule.
                e.g., ALBUMARTIST instead of ALBUM_ARTIST
                """)

    lib_act_p.add_argument(
        "--recently_added", action="store_true",
        help="""
                Generate a recently_added playlist by looking at the
                date of the parent directory.
                """)

    lib_act_p.add_argument(
        "--remove_junk_tags", action="store_true",
        help="""
                Similar to prune_artist_tags, but indiscriminately
                removes tags in config['library']['tags']['junk'].
                """)

    lib_act_p.add_argument(
        "--change_tag_by_name", action="store_true",
        help="""
                globally change a single tag field, applied to a
                directory or library. Can also be used to delete
                a tag by name.
                """)

    lib_act_p.add_argument(
        "--handle_composer_as_artist", action="store_true",
        help="""
                Test for and handle composer embedded in artist fields.
                Background:
                    Many taggers/publishers deal with classical music
                    tags by lumping the composer in with the artist,
                    as in ARTIST=JS Bach; Glenn Gould
                """)

    lib_act_p.add_argument(
        "--synchronize_artist", action="store_true",
        help="""
                Verify there is a corresponding entry in tags.json for
                each artist found in the tag file. If an entry is not
                found, user is prompted to add a new artist.
                Find the arrangement that is best fit for a given file.
                Finally, synchronize the file tags to the database.
                """)

    lib_act_p.add_argument(
        "--synchronize_composer", action="store_true",
        help="""
                Verify there is a corresponding entry in tags.json for
                the composer found in the tag file.
                If an entry is not found, user is prompted to add a
                new composer.
                Finally, synchronize the file tags to the database.
                """)

    lib_act_p.add_argument(
        "--get_artist_counts", action="store_true",
        help="""
                Update the occurence count of each artist in tags.json.
                These are then used for ordering new arrangements.
                """)

    lib_act_p.add_argument(
        "--get_arrangement_set", action="store_true",
        help="""
                get the set and counts of all instrumental groupings
                via sorted arrangements
                """)

    lib_subps.add_parser(
        "initialize",
        help="""
            Initialize a new folder / library by applying a sequence
            of library actions.
            """)

    lib_subps.add_parser(
        "synchronize",
        help="""
             synchronize the library file tags with the tags
             database""")

    lib_play_p = lib_subps.add_parser("playlist", help="")

    lib_play_p.add_argument(
        "-q", '--query', type=str, nargs='+',
        help="""structure --> TAG_KEY TRACK_RELATION TAG_VALUE SET_OPERATOR
            example --> ARRANGMENT contains guitar AND COMPOSER contains
            BACH""")


def create_config_parsers(subps):
    """ creates config sub-parsers
    """
    config_p = subps.add_parser(
        "config",
        help="""
            commands providing access to the configuration
            """)
    config_subps = config_p.add_subparsers(dest="sub_cmd")
    config_subps.add_parser(
        "edit",
        help="edit the config.json file in $EDITOR")
    config_subps.add_parser(
        "show",
        help="pretty print the current configuration to stdout")


def create_database_parsers(subps):
    """ creates tag database sub-parsers
    """
    db_p = subps.add_parser(
        "tags", help="commands providing access to tag database")
    db_subps = db_p.add_subparsers(dest="sub_cmd")
    db_subps.add_parser(
        "edit", help="edit the tags.json file in $EDITOR")
    db_subps.add_parser(
        "show", help="pretty print the tags.json file to stdout")


def create_stream_parsers(subps):
    """creates streams subparsers
    """
    strm_p = subps.add_parser(
        "streams",
        help="""
            commands for working with streams of audio data
            """)
    strm_subps = strm_p.add_subparsers(dest="sub_cmd")
    strm_init_p = strm_subps.add_parser(
        "listing",
        help="""
                 utilize a listing.json file to create a batch of new streams
                 """)

    strm_init_p.add_argument(
        "-l", "--listing", type=str, default="json/listing.json",
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


def parse_inputs():
    """populate a heirarchical argument parser
    """

    # top-level
    p = argparse.ArgumentParser(
        prog="CLAMM",
        description="""
            CLassical Music Manager
            """)
    subps = p.add_subparsers(dest="cmd")

    # sub-levels
    create_database_parsers(subps)
    create_config_parsers(subps)
    create_stream_parsers(subps)
    create_library_parsers(subps)

    return p


def tags_show(args):
    """Dump tags database to ``STDOUT``
    """
    with open(config["path"]["database"]) as db:
        tags = json.load(db)
    print(json.dumps(tags, ensure_ascii=False, indent=4))


def tags_edit(args):
    """Open tag database in ``$EDITOR``
    """
    call([os.environ["EDITOR"], config["path"]["database"]])


def config_init(args):
    """copy config template to ``$HOME/.config/clamm/config.json``
    """
    call([
        'cp',
        os.path.join(
            installed_location, 'clamm', 'templates', 'config.json'),
        get_config_path()
    ])


def config_show(args):
    """Dump config.json to ``STDOUT``
    """
    print(json.dumps(config, ensure_ascii=False, indent=4))


def config_edit(args):
    """Open config.json in ``$EDITOR``.
    """
    call([os.environ["EDITOR"], get_config_path()])


def streams_tracks(args):
    """ Calls :func:`~streams.stream2tracks` with ``streampath`` provided
    at command line.

    .. code-block:: bash

       $ clamm streams initialize
    """
    clamm.streams.stream2tracks(args.streampath)


def streams_listing(args):
    """ Calls :func:`~streams.listing2streams` with ``listing`` provided
    at command line.

    .. code-block:: bash

       $ clamm library initialize
    """
    clamm.streams.listing2streams(args.listing)


def streams_stream(args):
    """ Calls :func:`~streams.main`
    """
    clamm.streams.main(args)


def library_action(args):
    """ calls :func:`~clamm.audiolib.AudioLib.walker` with ``args`` provided
    at command line.

    Example

    .. code-block:: bash

       $ clamm library action --recently_added
    """
    alib = clamm.audiolib.AudioLib(args)
    funcdict = {q[0]: q[1] for q in args._get_kwargs()
                if isinstance(q[1], bool)}
    for funcname, flag in funcdict.items():
        if flag:
            clamm.util.printr(funcname)
            alib.func = funcname
            func = eval("alib.ltfa.{}".format(funcname))
            alib.walker(func)


def library_initialize(args):
    """ calls :func:`~clamm.audiolib.AudioLib.initialize` with ``args`` provided
    at command line.

    Example

    .. code-block:: bash

       $ clamm library initialize
    """
    clamm.audiolib.AudioLib(args).initialize()


def library_synchronize(args):
    """ calls :func:`~clamm.audiolib.AudioLib.synchronize` with ``args``
    provided at command line.

    Example

    .. code-block:: bash

       $ clamm library synchronize
    """
    clamm.audiolib.AudioLib(args).synchronize()


def library_playlist(args):
    """ calls :func:`~clamm.audiolib.AudioLib.playlist` with ``args``
    provided at command line.

    Example

    .. code-block:: bash

       $ clamm library playlist
    """
    clamm.audiolib.AudioLib(args).playlist()


def main():
    """clamm entrance point.

    Parses and executes the action specified by the command line inputs.
    """
    args = parse_inputs().parse_args()

    # retrieve the parsed cmd/sub/... and evaluate
    full_cmd = "{}_{}".format(args.cmd, args.sub_cmd)
    try:
        functor = eval(full_cmd)
    except NameError as ne:
        clamm.util.printr("failed to parse the command {}...".format(full_cmd))
        raise ne

    clamm.util.printr("parsed and executing {}...".format(full_cmd))
    functor(args)
