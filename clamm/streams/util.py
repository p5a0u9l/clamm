#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
import os
from glob import glob
from os.path import join
from subprocess import Popen
import time
import sys

# external
import taglib

# constants, globals
from clamm.util import config
global seconds
TMPSTREAM = os.path.join(config["path"]["pcm"], "temp.pcm")


def start_shairport(filepath):
    """
    make sure no duplicate processes and start up shairport-sync
    """

    Popen(['killall', config['bin']['shairport-sync']])
    time.sleep(10)

    Popen(['{} {} > "{}"'.format(
        config['bin']['shairport-sync'],
        config['opt']['shairport-sync'],
        filepath)], shell=True)

    time.sleep(1)

    print("INFO: shairport up and running.")


def size_sampler(filepath):
    """
    return the file size, sampled with a 1 second gap to determine
    if the file is being written to and thus growing
    """

    s0 = os.path.getsize(filepath)
    time.sleep(1)
    s1 = os.path.getsize(filepath)
    return (s0, s1)


def is_started(filepath):
    """
    test to see if recording has started
    """

    # reset seconds counter
    global seconds
    seconds = 0
    (s0, s1) = size_sampler(filepath)
    return s1 > s0


def is_finished(filepath):
    (s0, s1) = size_sampler(filepath)
    global seconds

    seconds += 2    # one for size_sampler and one for main loop
    if seconds % 60 == 0:
        sys.stdout.write(".")
        sys.stdout.flush()

    return s1 == s0


def metastize(query, target):
    for i, track in enumerate(query.get_tracks()):
        tracknum = "%0.2d" % (i+1)
        globber = glob(join(target, tracknum + "*flac"))
        flac = taglib.File(globber[0])
        flac.tags["ALBUM"] = [query.collection_name]
        flac.tags["ALBUMARTIST"] = [query.artist_name]
        flac.tags["ARTIST"] = [track.artist_name]
        flac.tags["TRACKNUMBER"] = [str(track.track_number)]
        flac.tags["DATE"] = [query.release_date]
        flac.tags["LABEL"] = [query.copyright]
        flac.tags["GENRE"] = [query.primary_genre_name]
        flac.tags["TITLE"] = [track.track_name]
        flac.tags["COMPILATION"] = ["0"]
        flac.save()
        flac.close()


def generate_playlist(artist, album):
    sed_program = 's/SEARCHTERM/"{} {}"/g'.format(
            artist, album).replace(":", "").replace("&", "")
    osa_prog = join(config["path"]["streams"], "scripts", "osa-program.js")
    osa_temp = join(config["path"]["streams"], "scripts", "osa-template.js")
    with open(osa_prog, "w") as osa:
        Popen([config['bin']['sed'], sed_program, osa_temp], stdout=osa)

    Popen([config['bin']['osascript'], osa_prog])


def dial_itunes(artist, album):
    """
    run apple script and attempt to uniquely locate the artist/album pair
    """

    generate_playlist(artist, album)
    time.sleep(2)   # allow time to build playlist
    osa_prog = join(config["path"]["streams"], "scripts", "osa-play")
    Popen([config['bin']['osascript'], osa_prog])
