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
import util
from library import libwalker

class StructuredQuery():
    def __init__(self, querystr):
        self.query = querystr
        self.keys = [key for key in self.query if key in util.config["playlist"]["tag_keys"]]
        relations = [key for key in self.query if key in util.config["playlist"]["relations"]]
        self.operators = [key for key in self.query if key in util.config["playlist"]["operators"]]
        self.tag_vals = [key for key in self.query if \
                key not in self.keys and \
                key not in relations and \
                key not in self.operators]

        self.filters = [{self.keys[i]: self.tag_vals[i], "rel": relations[i]} for i in range(len(self.operators) + 1)]
        if not self.operators: self.operators.append("AND")

    def __repr__(self): return str(["{}".format(filt) for filt in self.filters])

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
    sq = StructuredQuery(args.query)

    return sq

# append matches to global list
playlist = []

# parse once, make globally available
sq = parse_input_args()

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
    libwalker(util.config["path"]["library"], playfilt)

    # now, write the accumulated list to a simple pls file format
    pl_name = "-".join(sq.tag_vals).lower()
    pl_path = os.path.join(util.config["path"]["playlist"], pl_name)
    with open(pl_path, mode="w") as pl:
        [pl.write("{}\n".format(track)) for track in playlist]

    # finally, tell cmus to add the playlist to its catalog
    call(["/usr/local/bin/cmus-remote", "-C", "pl-import " + pl_path])

if __name__ == "__main__": main()
