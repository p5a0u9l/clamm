#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
import argparse
import os
import json
from subprocess import call

# external
import taglib

def parse_input_args():
    parser = argparse.ArgumentParser(description=\
    """ use sql-like relational patterns to quickly build
        complex playlists using cmus playlist format """
        , formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('query', type=str, nargs='+', \
            help=\
        """
        structure   --> TAG_KEY TRACK_RELATION TAG_VALUE SET_OPERATOR ...

        example     --> ARRANGMENT contains guitar AND COMPOSER contains BACH

        NOTE: for simplicity, though multiple operators may be included in the query,
        e.g., ARRANGMENT is guitar AND COMPOSER contains BACH AND ARTIST is Glenn Gould
        only one operator will be considered since mixing, e.g. AND then OR, would overly
        complicate and require precendence parsing.
        """)

    args = parser.parse_args()

    return args.query

# append matches to global list

# create query
querystring = parse_input_args()
sq = tags.StructuredQuery(querystring)

def main():
    """
    use sql-like relational patterns to quickly build complex
    playlists using cmus playlist format
    """

    # apply playfilt to each file in library
    audiolib.walker(config["path"]["library"], playlist)

    # now, write the accumulated list to a simple pls file format
    pl_name = "-".join(sq.tag_vals).lower()
    pl_path = os.path.join(config["path"]["playlist"], pl_name)
    with open(pl_path, mode="w") as pl:
        [pl.write("{}\n".format(track)) for track in playlist]

    # finally, tell cmus to add the playlist to its catalog
    call([config["bins"]["cmus-remote"], config["opts"]["cmus-remote"], "pl-import " + pl_path])

if __name__ == "__main__": main()
