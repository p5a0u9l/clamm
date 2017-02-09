#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
import os
import json
import time
import sys

# local
from clamm.util import config
from clamm.streams import util
from clamm.streams import stream2tracks


def batch_stream(args):
    """
    autobatch is a program for batch streaming a listing of albums from iTunes
    to raw pcm files via shairport-sync.

    iTunes is controlled using macos' built-in `osascript` tool and simple
    javascript request templates.

    When the listings have finished streaming, the pcm files (streams)
    are processed by `stream2tracks` and converted from streams to a
    collection of flac tracks
    """

    print("INFO: Begin autobatch...")

    # fetch the album listing
    try:
        with open(args.file) as b:
            batch = json.load(b)
    except FileNotFoundError:
        sys.exit("ERROR: File with name {} not found".format(args.file))

    # iterate over albums in the listing
    for key, val in batch.items():
        util.start_shairport(util.TMPSTREAM)

        artist, album = val['artist'], val['album']
        pcm = "{}; {}.pcm".format(artist, album)

        print("INFO: {} --> begin autobatch stream of {}..."
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

        os.rename(util.TMPSTREAM, os.path.join(config["path"]["pcm"], pcm))

    print("INFO: Batch successfully finished.")


def main(args):
    batch_stream(args)
    stream2tracks.main(args)


if __name__ == '__main__':
    main()
