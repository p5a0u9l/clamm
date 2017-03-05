#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# __author__ Paul Adams

""" streams module contains classes, programs, tools for creating
and processing audio streams.
"""

# built-ins
import os
from os.path import join
import wave
from glob import glob
import json
import time
import sys
from subprocess import Popen

# external
import matplotlib
import numpy as np
import taglib
from nltk import distance
import itunespy

# local
from config import config
import clamm
import audiolib

# constants, globals
matplotlib.use("Agg")
import matplotlib.pyplot as plt
global seconds
TMPSTREAM = os.path.join(config["path"]["pcm"], "temp.pcm")


class Stream():
    def __init__(self, streampath):
        """ """
        self.pcmpath = streampath
        self.wavpath = streampath.replace("pcm", "wav")
        self.query = []
        self.THRESH = 8

    def pcm2wav(self):
        if not os.path.exists(self.wavpath):
            audiolib.pcm2wav(self.pcmpath, self.wavpath)

    def decode_path(self):
        """artist/album names from stream name
        """
        tmp = self.pcmpath.replace(".pcm", "")
        [artist, album] = tmp.split(";")
        self.artist, self.album = os.path.split(artist)[-1], album.strip()
        clamm.printr("Found and Parsed {} --> {} as target...".format(
            self.artist, self.album))
        self.name = "{}; {}".format(self.artist, self.album)

        return self

    def iQuery(self):
        """seek an iTunes ``collection_id`` by iterating over albums
        of from a search artist and finding the minimum
        ``nltk.distance.edit_distance``
        """
        min_dist = 10000
        for aquery in itunespy.search_album(self.artist):
            d = distance.edit_distance(aquery.collection_name, self.album)
            if d < min_dist:
                min_dist = d
                min_query = aquery

        if min_dist < self.THRESH:
            self.query = itunespy.lookup(id=min_query.collection_id)[0]

        if not self.query:
            sys.exit("ERROR: album search failed...")

        return self

    def prepare_target(self):
        artist_dir = join(config["path"]["library"], self.query.artist_name)
        self.target = join(artist_dir, self.query.collection_name)

        if not os.path.exists(artist_dir):
            os.mkdir(artist_dir)
        if not os.path.exists(self.target):
            os.mkdir(self.target)

        return self

    def flacify(self):
        """convert all wav files in target directory to flac files
        """
        [audiolib.wav2flac(wav) for wav in glob(join(self.target, "*wav"))]
        return self

    def tagify(self):
        """Use iQuery to populate audio track tags.
        """
        for i, track in enumerate(self.query.get_tracks()):
            tracknum = "%0.2d" % (i+1)
            globber = glob(join(self.target, tracknum + "*flac"))
            flac = taglib.File(globber[0])
            flac.tags["ALBUM"] = [self.query.collection_name]
            flac.tags["ALBUMARTIST"] = [self.query.artist_name]
            flac.tags["ARTIST"] = [track.artist_name]
            flac.tags["TRACKNUMBER"] = [str(track.track_number)]
            flac.tags["DATE"] = [self.query.release_date]
            flac.tags["LABEL"] = [self.query.copyright]
            flac.tags["GENRE"] = [self.query.primary_genre_name]
            flac.tags["TITLE"] = [track.track_name]
            flac.tags["COMPILATION"] = ["0"]
            flac.save()
            flac.close()


class Album():
    """Given a stream object, locate the tracks within the stream,
    create new flac tracks, and populate with metadata.
    """

    def __init__(self, stream):
        """ """
        # wav file
        self.wavstream = wave.open(stream.wavpath)
        self.framerate = self.wavstream.getframerate()

        # itunes
        self.itunes = stream.query
        self.tracks = self.itunes.get_tracks()

        # current track position propertis
        self.curtrack = ""
        self.curtrackpath = ""
        self.last_track_end = 0
        self.start_frame = 0
        self.n_frame = 0

        self.target = stream.target
        self.splits = []
        self.err = {"dur": [], "pos": []}
        self.cumtime = 0

    def find_end_frame(self, reference):
        """
        find the min energy point around a reference
        """
        excursion = 10*self.framerate
        n_read = int(0.02*self.framerate)
        start_at = reference - excursion
        go_till = np.min([reference + excursion, self.wavstream.getnframes()])
        self.wavstream.setpos(start_at)
        local_min = 1e9
        local_idx = -1

        while self.wavstream.tell() < go_till:
            wav_power = np.std(read_wav_mono(self.wavstream, n_read))
            if wav_power < local_min:
                local_min = wav_power
                local_idx = self.wavstream.tell()

        self.end_frame = local_idx

    def find_start_frame(self):
        """
        find audio signal activity that exceeds threshold and persists
        call this the start frame of a track
        """
        not_found = True
        THRESH = 10
        persistence = 10
        n_read = 100
        found_count = 0
        preactivity_offset = round(1*self.framerate)

        # start where left off
        self.wavstream.setpos(self.last_track_end)

        while not_found:
            y = np.std(read_wav_mono(self.wavstream, n_read))
            if y > THRESH:
                found_count += 1
            else:
                found_count = 0

            not_found = found_count <= persistence

        curpos = self.wavstream.tell()
        # subtract off persistence and a preactivity_offset
        activity = curpos - persistence*n_read - preactivity_offset
        self.start_frame = activity

    def process(self):
        """
        encapsulate the substance of Album processing
        """
        # iterate over and process tracks derived from iQuery
        for i, track in enumerate(self.tracks):
            self.curtrack = track
            self.curindex = i
            self.create().consume().finalize()

        # close the wav stream
        self.wavstream.close()

        return self

    def create(self):
        """
        find track starts/stops within stream
        """

        # find start of track (find activity)
        self.find_start_frame()

        # find end of track (find local min)
        track_duration = int(self.curtrack.track_time/1000*self.framerate)
        reference = self.start_frame + track_duration
        self.find_end_frame(reference)

        # update track split parameters
        self.n_frame = self.end_frame - self.start_frame
        self.last_track_end = self.end_frame
        self.splits.append((self.start_frame, self.n_frame))

        return self

    def consume(self):
        trackname = self.curtrack.track_name.strip().replace("/", ";")
        self.curtrackpath = join(
                self.target, "%0.2d %s.wav" % (self.curindex + 1, trackname))

        # status prints
        SAMP2MIN = 1/self.framerate/60
        MS2MIN = 1/1000/60
        print("{}".format(trackname))
        self.err["dur"].append(
                self.n_frame*SAMP2MIN - self.curtrack.track_time*MS2MIN)
        self.err["pos"].append(
                self.start_frame*SAMP2MIN - self.cumtime)
        print("\tESTIMATED duration: %.2f min         --> position: %.2f min" %
              (self.n_frame*SAMP2MIN, self.start_frame*SAMP2MIN))
        print("\tEXPECTED            %.2f min         -->           %.2f min" %
              (self.curtrack.track_time*MS2MIN, self.cumtime))
        print("\tERROR\t   (%.2f, %.2f) sec \t     --> (%.2f, %.2f) sec" %
              (60*np.mean(self.err["dur"]), 60*np.std(self.err["dur"]),
               60*np.mean(self.err["pos"]), 60*np.std(self.err["pos"])))

        self.cumtime += self.curtrack.track_time*MS2MIN

        return self

    def finalize(self):
        with wave.open(self.curtrackpath, 'w') as wavtrack:
            self.wavstream.setpos(self.start_frame)
            y = np.fromstring(
                    self.wavstream.readframes(self.n_frame),
                    dtype=np.int16)
            y = np.reshape(y, (int(y.shape[0]/2), 2))
            wavtrack.setnchannels(2)
            wavtrack.setsampwidth(2)
            wavtrack.setnframes(self.n_frame)
            wavtrack.setframerate(self.wavstream.getframerate())
            wavtrack.writeframes(y)


def read_wav_mono(wav, N):
    """grab samples from one channel (every other sample) of frame
    """

    return np.fromstring(wav.readframes(N), dtype=np.int16)[:2:-1]


def power_envelope(wavpath):
    """power_envelope
    """

    ds = config["streams"]["downsample_factor"]
    print("computing audio envelope of file at {} downsample rate..."
          .format(ds))

    with wave.open(wavpath) as wavstream:
        n_window = int(np.floor(wavstream.getnframes()/ds)) - 1
        x = [np.std(read_wav_mono(wavstream, ds))**2
             for i in range(n_window)]

    return np.asarray(x)


def start_shairport(filepath):
    """make sure no duplicate processes and start up shairport-sync
    """

    Popen(['killall', 'shairport-sync'])
    time.sleep(10)

    Popen(['{} {} > "{}"'.format(
        config['bin']['shairport-sync'], "-o=stdout", filepath)], shell=True)

    time.sleep(1)

    print("INFO: shairport up and running.")


def size_sampler(filepath):
    """ return the file size, sampled with a 1 second gap to
    determine if the file is being written to.
    """

    s0 = os.path.getsize(filepath)
    time.sleep(1)
    s1 = os.path.getsize(filepath)
    return (s0, s1)


def is_started(filepath):
    """test to see if recording has started
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
    """run apple script and attempt to uniquely locate the
    artist/album pair.
    """

    generate_playlist(artist, album)
    time.sleep(2)   # allow time to build playlist
    osa_prog = join(config["path"]["osa"], "play")
    Popen([config['bin']['osascript'], osa_prog])


def image_audio_envelope_with_tracks_markers(markers, stream):
    """track-splitting validation image
    """

    x = power_envelope(stream.wavpath)

    ds = config["streams"]["downsample_factor"]
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
    savepath = join(config["path"]["envelopes"], stream.name + ".png")
    print("saving to {}".format(savepath))
    plt.savefig(savepath, bbox_inches='tight')


# --------------------------
# Programs
# --------------------------


def listing2streams(listing):
    """a program for batch streaming a ``json`` listing of albums
    from iTunes to raw pcm files via ``shairport-sync``.

    iTunes is controlled using macos' built-in ``osascript`` tool and
    simple javascript request templates.

    When the listings have finished streaming, the pcm files (streams)
    can be processed by ``stream2tracks`` and converted from streams
    to a collection of flac tracks.
    """

    print("INFO: Begin listing2streams...")

    # fetch the album listing
    try:
        with open(listing) as b:
            batch = json.load(b)
    except FileNotFoundError:
        sys.exit("ERROR: File with name {} not found".format(listing))

    # iterate over albums in the listing
    for key, val in batch.items():

        start_shairport(TMPSTREAM)

        artist, album = val['artist'], val['album']
        pcm = "{}; {}.pcm".format(artist, album)
        pcm_path = join(config["path"]["pcm"], pcm)

        print("INFO: {} --> begin listing2streams stream of {}..."
              .format(time.ctime(), pcm))

        print("INFO: talking to iTunes...")
        dial_itunes(artist, album)

        # wait for stream to start
        while not is_started(TMPSTREAM):
            time.sleep(1)
        print("INFO: Stream successfully started, "
              " now waiting for finish (one dot per minute)...")

        # wait for stream to finish
        while not is_finished(TMPSTREAM):
            time.sleep(1)
        print("INFO: Stream successfully finished.")

        os.rename(TMPSTREAM, pcm_path)

    print("INFO: Batch successfully finished.")


def stream2tracks(streampath):
    """process raw pcm stream to tagged album tracks.
    """

    clamm.printr("Begin stream2tracks...")

    # initialize the stream
    stream = Stream(streampath)
    stream.decode_path().iQuery().prepare_target().pcm2wav()

    # process the stream into an album
    album = Album(stream).process()

    # finalize the stream into flac files with tags
    stream.flacify().tagify()

    # create an image of the audio envelope indicating where track splits
    # have been located
    image_audio_envelope_with_tracks_markers(album.splits, stream)

    print("INFO: Finish stream2tracks.")


def main(args):
    """
    main is a concatenation of listing2streams and stream2tracks
    """

    # create a batch of pcm streams by interfacing with iTunes
    listing2streams(args.listing)

    # iterate over streams found in config["path"]["pcm"]
    streams = glob(os.path.join(config["path"]["pcm"], "*pcm"))
    for streampath in streams:
        stream2tracks(streampath)


if __name__ == '__main__':
    main()
