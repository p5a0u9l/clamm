#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
import os

# local
from clamm.tui import config, parse_inputs, functers

# make sure /tmp directories exist
if not os.path.exists(config["path"]["pcm"]): os.makedirs(config["path"]["pcm"])
if not os.path.exists(config["path"]["wav"]): os.makedirs(config["path"]["wav"])

def main():
    """ entrance point for clamm """
    args = tui.parse_inputs().parse_args()

    # retrieve the parsed cmd/sub/... and evaluate
    funky = functers[args.cmd + args.sub_cmd]
    funky(args)


if __name__ == "__main__": main()
