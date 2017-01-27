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

# local
import tags

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
playlist = []

# create query
querystring = parse_input_args()
sq = tags.StructuredQuery(querystring)

def playfilt(tagfile):
    tags = tagfile.tags

    # not sure how to (or if I want to) deal with compilations yet, particularly since they are missing
    # ARRANGMENT tags
    try:
        if tags["COMPILATION"][0] == "1": return
    except KeyError:
        util.log_missing_tag("COMPILATION", tagfile)

    if sq.operators[0] == "AND":
        include = True
        for i, filt in enumerate(sq.filters):
            key = sq.keys[i]
            try:
                if filt[key] not in tags[key]: include = False
            except KeyError:
                include = False
                util.log_missing_tag(key, tagfile)

    elif sq.operators[0] == "OR":
        include = False

        for i, filt in enumerate(sq.filters):
            key = sq.keys[i]
            if filt[key] in tags[key]: include = True

    if include: playlist.append(tagfile.path)

def main():
    """ use sql-like relational patterns to quickly build complex playlists using cmus playlist format """

    # apply playfilt to each file in library
    audiolib.walker(config["path"]["library"], playfilt)

    # now, write the accumulated list to a simple pls file format
    pl_name = "-".join(sq.tag_vals).lower()
    pl_path = os.path.join(config["path"]["playlist"], pl_name)
    with open(pl_path, mode="w") as pl:
        [pl.write("{}\n".format(track)) for track in playlist]

    # finally, tell cmus to add the playlist to its catalog
    call([config["bins"]["cmus-remote"], config["opts"]["cmus-remote"], "pl-import " + pl_path])

if __name__ == "__main__": main()
