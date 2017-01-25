#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
from os import walk
from os.path import join
import sys
import argparse

# external
import taglib

# local
import util
from action import AtomicAction

def libwalker(root, func, tagfile=True):
    """ iterate over every audio file under the target directory and apply action to each """

    for folder, _, files in walk(root, topdown=False):
        if not files: continue

        print("walked into {}...".format(folder.replace(util.config["path"]["library"], "$LIBRARY")))
        if tagfile:
            [func(taglib.File(join(folder, name))) for name in files if util.is_audio_file(name)]
        else:
            [func(folder, name) for name in files if util.is_audio_file(name)]

class AudioLib():
    def __init__(self, args):
        self.root = args.target
        self.act = AtomicAction(args)

    def synchronize(self):
        """ special hook for ensuring the tag database and the library file tags are sync'd """
        libwalker(self.root, self.act.synchronize_composer)
        libwalker(self.root, self.act.synchronize_artist)

    def consume(self):
        """ special hook for consuming new music into library"""
        libwalker(self.root, util.audio2flac, tagfile=False)
        libwalker(self.root, self.act.synchronize_composer)
        libwalker(self.root, self.act.prune_artist_tags)
        libwalker(self.root, self.act.remove_junk_tags)
        libwalker(self.root, self.act.handle_composer_as_artist)
        libwalker(self.root, self.act.synchronize_artist)

def parse_input_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=str, help="The target operating directory")
    parser.add_argument("action", type=str, help="The action to enact on the target")
    parser.add_argument("-t", "--tag", default="", help="a tag field upon which to act")
    parser.add_argument("-v", "--value", default="", help="the value to apply to tags")
    return parser

def main():
    args = parse_input_args().parse_args()
    alib = AudioLib(args)

    # front-end action
    if args.action == "consume": alib.consume()
    elif args.action == "synchronize": alib.synchronize()
    else: libwalker(alib.act.func[args.action])

    # define follow-up actions
    if util.COUNT > 0: print("\n{} tagfiles updated.".format(util.COUNT))

    elif args.action == "get_arrangement_set":
        with open('instrument_groupings.json' ,'w') as f:
            json.dump(alib.act.instrument_groupings, f, indent=4)

    elif args.action == "get_artist_counts":
        for key, val in alib.act.instrument_groupings.items():
            if not key == None: alib.act.tagdb.artist[key]["count"] = val

        alib.act.tagdb.refresh()

    elif args.action == "find_multi_instrumentalists":
        print(alib.act.instrument_groupings)

    elif args.action == "get_tag_sets" or sys.argv[2] == "show_tag_usage":
        print(alib.act.found_tags)

if __name__ == "__main__": main()
