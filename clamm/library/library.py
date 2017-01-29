#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
import sys
import argparse

def main():
    args = parse_input_args().parse_args()
    alib = audiolib.AudioLib(args)

    # front-end action
    if args.action == "consume": alib.consume()
    elif args.action == "synchronize": alib.synchronize()
    else: audiolib.walker(alib.act.func[args.action])

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
