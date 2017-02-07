#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# __author__ Paul Adams

"""
1. Manually compile a listing of ARTIST; ALBUM targets
    For each line in the recipe file:
        2. use itunes-remote (or something similar) to automate finding and
            starting playback of the correct stream
        3, shairport-sync should be quiescent and ready to receive the bits
        4. a method of recognizing when the album playback has completed will
            be necessary to take finalize actions

    5 With a wav/ folder full of captured/converted streams, process each wav

    6. for each wav in wavs:
        run stream2tracks

    7. the library now has a number of new folder/albums, each containing
    a number of tracks
"""

# built-ins
import os
from subprocess import Popen
import json
import time

# local
from clamm.util import config
from clamm.streams import util
from clamm.streams import stream2tracks

TMPSTREAM = "./tmp.pcm"


def main():
    """
    executive for autobatch
    """

    # fetch the alibum listing
    path = os.path.join(config["path"]["streams"], "batch_album_listing.json")
    with open(path) as b:
        batch = json.load(b)

    # iterate over albums in the listing
    for key, val in batch.items():
        util.start_shairport(TMPSTREAM)

        artist, album = val['artist'], val['album']
        pcm = "{}; {}.pcm".format(artist, album)

        print("INFO: {} --> begin autobatch stream of {}..."
              .format(time.ctime(), pcm))

        print("INFO: talking to iTunes...")
        util.dial_itunes(artist, album)

        # wait for stream to start
        while not util.is_started(TMPSTREAM):
            time.sleep(1)
        print("INFO: Stream successfully started, "
              " now waiting for finish (one dot per minute)...")

        # wait for stream to finish
        while not util.is_finished(TMPSTREAM):
            time.sleep(1)
        print("INFO: Stream successfully finished.")

        os.rename(TMPSTREAM,
                  os.path.join(config["path"]["streams"], "pcm", pcm))

    print("INFO: Batch successfully finished.")
    print("INFO: Converting PCMs to WAVs...")
    os.chdir(config["path"]["streams"], "pcm")
    Popen(['../pcm2wav.sh'])
    print("INFO: Success.")
    print("INFO: Begin stream2tracks...")
    stream2tracks.main()


if __name__ == '__main__':
    main()
