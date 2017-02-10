#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
from os.path import join
import wave
from glob import glob
import os
import sys

# external
import taglib
from nltk import distance
import numpy as np
import itunespy

# locals
import clamm.util as cutil
from clamm.util import config
from clamm.library import util as libutil
from clamm.streams import util


class Stream():
    def __init__(self, streampath):
        """ """
        self.pcmpath = streampath
        self.wavpath = streampath.replace("pcm", "wav")
        self.query = []

    def pcm2wav(self):
        libutil.pcm2wav(self.pcmpath, self.wavpath)

    def decode_path(self):
        """
        artist/album names from stream name
        """
        self.name = self.pcmpath.replace(".pcm", "")
        [artist, album] = self.name.split(";")
        self.artist, self.album = os.path.split(artist)[-1], album.strip()
        cutil.printr("Found and Parsed {} --> {} as target...".format(
            self.artist, self.album))

        return self

    def iQuery(self):
        for aquery in itunespy.search_album(self.artist):
            d = distance.edit_distance(aquery.collection_name, self.album)
            # print("{} --> distance: {}".format(aquery.collection_name, d))
            if d < 5:
                self.query = itunespy.lookup(id=aquery.collection_id)[0]
                break

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

    def make_flacs(self):
        """
        convert all wav files in target directory to flac files
        """
        [libutil.wav2flac(wav) for wav in glob(join(self.target, "*wav"))]
        return self

    def tagify(self):
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
    """
    given a stream object, locate the tracks within the stream,
    create new flac tracks, and populate with metadata
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
            wav_power = np.std(util.read_wav_mono(self.wavstream, n_read))
            if wav_power < local_min:
                local_min = wav_power
                local_idx = self.wavstream.tell()

        self.end_frame = local_idx

    def find_start_frame(self):
        """
        find audio signal activity that exceeds threshold and persists
        """
        not_found = True
        THRESH = 10
        persistence = 10
        n_read = 100
        found_count = 0

        # start where left off
        self.wavstream.setpos(self.last_track_end)

        while not_found:
            y = np.std(util.read_wav_mono(self.wavstream, n_read))
            if y > THRESH:
                found_count += 1
            else:
                found_count = 0

            not_found = found_count <= persistence

        activity = self.wavstream.tell() - persistence*n_read

        # set track start 1 second before activity location
        self.start_frame = activity - round(1*self.framerate)

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
        print("\tERROR               (%.2f, %.2f) sec -->           "
              + "(%.2f, %.2f) sec" %
              (60*np.mean(self.err["dur"]),
               60*np.std(self.err["dur"]),
               60*np.mean(self.err["pos"]),
               60*np.std(self.err["pos"])))

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
