#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# __author__ Paul Adams

"""
1. Manually compile a listing of ARTIST; ALBUM targets
    For each line in the recipe file:
        2. use itunes-remote (or something similar) to automate finding and starting playback of the correct stream
        3, shairport-sync should be quiescent and ready to receive the bits
        4. a method of recognizing when the album playback has completed will be necessary to take finalize actions

    5 With a wav/ folder full of captured/converted streams, process each wav

    6. for each wav in wavs:
        run stream2tracks

    7. the library now has a number of new folder/albums, each containing a number of tracks
"""

# built-ins
import os
from subprocess import Popen
import json
import time
import sys

ssync = "shairport-sync"
global seconds

def generate_playlist(artist, album):
    sed_program = 's/SEARCHTERM/"{} {}"/g'.format(artist, album).replace(":", "").replace("&", "")
    with open("osa-program.js", "w") as osa:
        Popen(['/usr/bin/sed', sed_program, 'osa-template.js'], stdout=osa)

    Popen(['/usr/bin/osascript', 'osa-program.js'])

def dial_itunes(artist, album):
    """ run apple script and attempt to uniquely locate the artist/album pair """

    generate_playlist(artist, album)
    time.sleep(2) # time to build playlist
    Popen(['/usr/bin/osascript', 'osa-play'])

def start_shairport(pcm):
    """ make sure no doubles, start up shairport-sync """
    Popen(['killall', ssync]);
    Popen(['{} -o=stdout > "{}"'.format(ssync, pcm)], shell=True)
    time.sleep(1)

def size_sampler(pcm):
    s0 = os.path.getsize(pcm); time.sleep(1); s1 = os.path.getsize(pcm)
    return (s0, s1)

def is_started(pcm):
    global seconds

    seconds = 0
    (s0, s1) = size_sampler(pcm)
    return s1 > s0

def is_finished(pcm):
    (s0, s1) = size_sampler(pcm)
    global seconds

    seconds += 2 # one for size_sampler and one for main loop
    if seconds % 60 == 0:
        sys.stdout.write(".")
        sys.stdout.flush()

    return s1 == s0

def main():
    with open("batch_album_listing.json") as b: batch = json.load(b)

    for key, val in batch.items():
        artist, album, pcm = val['artist'], val['album'], "{}; {}.pcm".format(val['artist'], val['album'])

        print("INFO: {} --> begin autobatch stream of {}...".format(time.ctime(), pcm))
        start_shairport(pcm);
        print("INFO: {} up and running.".format(ssync))

        print("INFO: talking to iTunes...")
        dial_itunes(artist, album)

        while not is_started(pcm): time.sleep(1)
        print("INFO: Stream successfully started, now waiting for finish (one dot per minute)...")

        while not is_finished(pcm): time.sleep(1)
        print("INFO: Stream successfully finished.")

        os.rename(pcm, os.path.join("pcm", pcm))

    print("INFO: Batch successfully finished.")
    print("INFO: Converting PCMs to WAVs...")
    Popen(['./pcm2wav.sh'])
    print("INFO: Success.")

if __name__ == '__main__': main()
