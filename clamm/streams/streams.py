#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# __author__ Paul Adams

"""
streams is a concatenation of listing2streams and stream2tracks
"""

# built-ins
import os
import glob

# local
from clamm.util import config
from clamm.streams import stream2tracks, listing2streams


def main(args):
    # create a batch of pcm streams by interfacing with iTunes
    listing2streams.main(args.listing)

    # iterate over streams found in config["path"]["pcm"]
    streams = glob.glob(os.path.join(config["path"]["pcm"], "*pcm"))
    for streampath in streams:
        stream2tracks.main(streampath)


if __name__ == '__main__':
    main()
