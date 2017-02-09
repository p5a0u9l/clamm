#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
from os.path import join
import wave
import os

# external
import numpy as np
import itunespy
import matplotlib.pyplot as plt

# locals
import clamm.util as cutil
from clamm.util import config


class Stream():
    def __init__(self, streampath):
        """ """
        self.path = streampath
        self.decode_stream_path()

    def decode_stream_path(self):
        """ artist/album names from stream name """
        [artist, album] = self.path.replace(".wav", "").split(";")
        artist, album = os.path.split(artist)[-1], album.strip()
        cutil.printr("Found and Parsed {} --> {} as target...".format(
            self.artist, self.album))
        return (artist, album)

    def itunes_lookup(artist, album):
        query = []
        for aquery in itunespy.search_album(artist):
            d = distance.edit_distance(aquery.collection_name, album)
            # print("{} --> distance: {}".format(aquery.collection_name, d))
            if d < 5:
                query = itunespy.lookup(id=aquery.collection_id)[0]
                break

        if not query:
            print("album search failed...")
            sys.exit()

        return query

    def prep_album_target_dir(query):
        artist_dir = join(config["path"]["library"], query.artist_name)
        target = join(artist_dir, query.collection_name)

        if not os.path.exists(artist_dir):
            os.mkdir(artist_dir)
        if not os.path.exists(target):
            os.mkdir(target)

        return target


class AlbumStream():
    """
        given a wav file object, an itunes Album query, and a target directory,
        locate the tracks within the stream, create new flac tracks,
        and populate with metadata
    """

    def __init__(self, wav, query, tgt):
        """ """
        # wav file
        self.wav = wav
        self.framerate = wav.getframerate()

        # itunes
        self.itunes = query
        self.tracks = self.itunes.get_tracks()

        # current track position propertis
        self.curtrack = ""
        self.curtrackpath = ""
        self.last_track_end = 0
        self.start_frame = 0
        self.n_frame = 0

        self.target = tgt
        self.splits = []
        self.err = {"dur": [], "pos": []}
        self.cumtime = 0

    def read_wav_mono(self, N):
        """ grab samples from one channel (every other sample) of frame """
        return np.fromstring(self.wav.readframes(N), dtype=np.int16)[:2:-1]

    def find_end_frame(self, reference):
        """ find the min energy point around a reference """
        excursion = 10*self.framerate
        n_read = int(0.02*self.framerate)
        start_at = reference - excursion
        go_till = np.min([reference + excursion, self.wav.getnframes()])
        self.wav.setpos(start_at)
        local_min = 1e9
        local_idx = -1

        while self.wav.tell() < go_till:
            wav_power = np.std(self.read_wav_mono(n_read))
            if wav_power < local_min:
                local_min = wav_power
                local_idx = self.wav.tell()

        self.end_frame = local_idx

    def find_start_frame(self):
        """ find audio signal activity that exceeds threshold and persists """
        not_found = True
        THRESH = 10
        persistence = 10
        n_read = 100
        found_count = 0

        # start where left off
        self.wav.setpos(self.last_track_end)

        while not_found:
            y = np.std(self.read_wav_mono(n_read))
            if y > THRESH:
                found_count += 1
            else:
                found_count = 0

            not_found = found_count <= persistence

        activity = self.wav.tell() - persistence*n_read

        # set track start 1 second before activity location
        self.start_frame = activity - round(1*self.framerate)

    def create(self, i, track):
        """ find track starts/stops within stream """

        self.curtrack = track

        # find start of track (find activity)
        self.find_start_frame()

        # find end of track (find local min)
        reference = self.start_frame + int(
                track.track_time/1000*self.framerate)
        self.find_end_frame(reference)

        # update track split parameters
        self.n_frame = self.end_frame - self.start_frame
        self.last_track_end = self.end_frame
        self.splits.append((self.start_frame, self.n_frame))

        return self

    def consume(self, i):
        trackname = self.curtrack.track_name.strip().replace("/", ";")
        self.curtrackpath = join(
                self.target, "%0.2d %s.wav" % (i+1, trackname))

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
        print("\tERROR               (%.2f, %.2f) sec -->           "
              + "(%.2f, %.2f) sec" %
              (60*np.mean(self.err["dur"]),
               60*np.std(self.err["dur"]),
               60*np.mean(self.err["pos"]),
               60*np.std(self.err["pos"])))

        self.cumtime += self.curtrack.track_time*MS2MIN

        return self

    def finalize(self):
        with wave.open(self.curtrackpath, 'w') as wavfile:
            self.wav.setpos(self.start_frame)
            y = np.fromstring(
                    self.wav.readframes(self.n_frame), dtype=np.int16)
            y = np.reshape(y, (int(y.shape[0]/2), 2))
            wavfile.setnchannels(2)
            wavfile.setsampwidth(2)
            wavfile.setnframes(self.n_frame)
            wavfile.setframerate(self.wav.getframerate())
            wavfile.writeframes(y)

    def power_envelope(self):
        """ power_envelope """
        ds = config["stream2tracks"]["downsample_factor"]
        print("computing audio envelope of file at {} downsample rate..."
              .format(ds))
        self.wav.rewind()
        n_window = int(np.floor(self.wav.getnframes()/ds)) - 1
        x = [np.std(self.read_wav_mono(ds))**2 for i in range(n_window)]
        return np.asarray(x)


def plot_envelope_splits(x, splits, fname):
    ds = config["stream2tracks"]["downsample_factor"]
    efr = 44100/ds
    starts = [split[0]/ds for split in splits]
    stops = [starts[i] + split[1]/ds for i, split in enumerate(splits)]
    n = np.shape(x)[0]
    n_min = int(n/efr/60)

    # create figure (one inch per minute of audio)
    plt.figure(figsize=(n_min, 10))
    plt.plot(x, marker=".", linestyle='', markersize=0.2)
    [plt.axvline(x=start, color="b", linestyle="--", linewidth=0.3)
        for start in starts]
    [plt.axvline(x=stop, color="r", linestyle="--", linewidth=0.3)
        for stop in stops]
    plt.savefig(join(config["path"]["streams"], "envelopes", fname + ".png"),
                bbox_inches='tight')
