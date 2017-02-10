#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
import os
from os.path import join
from subprocess import Popen
import time
import sys

# externals
import matplotlib.pyplot as plt
import numpy as np

# locals
from clamm.util import config

# constants, globals
global seconds
TMPSTREAM = os.path.join(config["path"]["pcm"], "temp.pcm")


def read_wav_mono(wav, N):
    """
    grab samples from one channel (every other sample) of frame
    """

    return np.fromstring(
            wav.readframes(N),
            dtype=np.int16)[:2:-1]


def power_envelope(wavpath):
    """
    power_envelope
    """

    ds = config["stream2tracks"]["downsample_factor"]
    print("computing audio envelope of file at {} downsample rate..."
          .format(ds))

    with open(wavpath) as wavstream:
        n_window = int(np.floor(wavstream.getnframes()/ds)) - 1
        x = [np.std(read_wav_mono(wavstream, ds))**2
             for i in range(n_window)]

    return np.asarray(x)


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


def generate_playlist(artist, album):
    sed_program = 's/SEARCHTERM/"{} {}"/g'.format(
            artist, album).replace(":", "").replace("&", "")
    osa_prog = join(config["path"]["osa"], "program.js")
    osa_temp = join(config["path"]["osa"], "template.js")
    with open(osa_prog, "w") as osa:
        Popen([config['bin']['sed'], sed_program, osa_temp], stdout=osa)

    Popen([config['bin']['osascript'], osa_prog])


def dial_itunes(artist, album):
    """
    run apple script and attempt to uniquely locate the artist/album pair
    """

    generate_playlist(artist, album)
    time.sleep(2)   # allow time to build playlist
    osa_prog = join(config["path"]["osa"], "play")
    Popen([config['bin']['osascript'], osa_prog])


def image_audio_envelope_with_tracks_markers(markers, stream):
    """
    track-splitting validation image
    """

    x = power_envelope(stream.wavpath)

    ds = config["stream2tracks"]["downsample_factor"]
    efr = 44100/ds
    starts = [mark[0]/ds for mark in markers]
    stops = [starts[i] + mark[1]/ds for i, mark in enumerate(markers)]
    n = np.shape(x)[0]
    n_min = int(n/efr/60)

    # create image (one inch per minute of audio)
    plt.figure(figsize=(n_min, 10))
    plt.plot(x, marker=".", linestyle='', markersize=0.2)
    [plt.axvline(x=start, color="b", linestyle="--", linewidth=0.3)
        for start in starts]
    [plt.axvline(x=stop, color="r", linestyle="--", linewidth=0.3)
        for stop in stops]
    plt.savefig(
            join(config["path"]["envelopes"], stream.name + ".png"),
            bbox_inches='tight')
