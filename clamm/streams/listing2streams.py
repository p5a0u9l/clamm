#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# __author__ Paul Adams

"""
listing2streams is a program for batch streaming a listing of albums
from iTunes to raw pcm files via shairport-sync.

iTunes is controlled using macos' built-in `osascript` tool and simple
javascript request templates.

When the listings have finished streaming, the pcm files (streams)
are processed by `stream2tracks` and converted from streams to a
collection of flac tracks
"""

# built-ins
import os
import json
import time
import sys
from os.path import join

# local
from clamm.util import config
from clamm.streams import util


def main(listing):
    print("INFO: Begin listing2streams...")

    # fetch the album listing
    try:
        with open(listing) as b:
            batch = json.load(b)
    except FileNotFoundError:
        sys.exit("ERROR: File with name {} not found".format(listing))

    # iterate over albums in the listing
    for key, val in batch.items():

        util.start_shairport(util.TMPSTREAM)

        artist, album = val['artist'], val['album']
        pcm = "{}; {}.pcm".format(artist, album)
        pcm_path = join(config["path"]["pcm"], pcm)

        print("INFO: {} --> begin listing2streams stream of {}..."
              .format(time.ctime(), pcm))

        print("INFO: talking to iTunes...")
        util.dial_itunes(artist, album)

        # wait for stream to start
        while not util.is_started(util.TMPSTREAM):
            time.sleep(1)
        print("INFO: Stream successfully started, "
              " now waiting for finish (one dot per minute)...")

        # wait for stream to finish
        while not util.is_finished(util.TMPSTREAM):
            time.sleep(1)
        print("INFO: Stream successfully finished.")

        os.rename(util.TMPSTREAM, pcm_path)

    print("INFO: Batch successfully finished.")


if __name__ == '__main__':
    main()
