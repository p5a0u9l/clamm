"""
streams module contains classes, programs, tools for creating
and processing audio streams.
"""

import os
from os.path import join
import wave
from glob import glob
import json
import time
import sys
from subprocess import Popen

import matplotlib.pyplot as plt
from tqdm import trange
import numpy as np
import taglib
from nltk import distance
import itunespy

from clamm.config import config
from clamm import util
from clamm import audiolib

# constants, globals
plt.switch_backend("agg")
TMPSTREAM = os.path.join(util.resolve(config["path"]["pcm"]), "temp.pcm")
DF = config["streams"]["downsample_factor"]
DF = 4410 * 10
FS = 44100
FS_DEC = FS / DF
SAMP2MIN = 1 / FS / 60
MS2SEC = 1 / 1000
MS2MIN = MS2SEC / 60


class StreamError(Exception):
    """ StreamError """
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class Stream():
    """ Stream """
    def __init__(self, streampath):
        """ """
        self.pcmpath = streampath
        self.wavpath = streampath.replace("pcm", "wav")
        self.query = []
        self.artist = []
        self.album = []
        self.name = []
        self.threshold = 8

    def pcm2wav(self):
        """ pcm2wav """
        if not os.path.exists(self.wavpath):
            audiolib.pcm2wav(self.pcmpath, self.wavpath)

    def decode_path(self):
        """artist/album names from stream name
        """
        tmp = self.pcmpath.replace(".pcm", "")
        [artist, album] = tmp.split(";")
        self.artist, self.album = os.path.split(artist)[-1], album.strip()
        util.printr("Found and Parsed {} --> {} as target...".format(
            self.artist, self.album))
        self.name = "{}; {}".format(self.artist, self.album)

        return self

    def itunes_query(self):
        """seek an iTunes ``collection_id`` by iterating over albums
        of from a search artist and finding the minimum
        ``nltk.distance.edit_distance``
        """
        min_dist = 10000
        for aquery in itunespy.search_album(self.artist):
            dist = distance.edit_distance(aquery.collection_name, self.album)
            if dist < min_dist:
                min_dist = dist
                min_query = aquery

        if min_dist < self.threshold:
            self.query = itunespy.lookup(id=min_query.collection_id)[0]

        if not self.query:
            sys.exit("ERROR: album search failed...")

        return self

    def prepare_target(self):
        artist_dir = join(
            util.resolve(config["path"]["library"]),
            self.query.artist_name)
        self.target = join(artist_dir, self.query.collection_name)

        if not os.path.exists(artist_dir):
            os.mkdir(artist_dir)
        if not os.path.exists(self.target):
            os.mkdir(self.target)

        return self

    def flacify(self):
        """convert all wav files in target directory to flac files
        """
        map(
            audiolib.wav2flac,
            glob(join(self.target, "*wav")))
        return self

    def tagify(self):
        """Use itunes_query to populate audio track tags.
        """
        for i, track in enumerate(self.query.get_tracks()):
            tracknum = "%0.2d" % (i + 1)
            globber = glob(join(self.target, tracknum + "*flac"))
            flac = taglib.File(globber[0])
            flac.tags["ALBUM"] = [self.query.collection_name]
            flac.tags["ALBUMARTIST"] = [self.query.artist_name]
            flac.tags["ARTIST"] = [track.name]
            flac.tags["TRACKNUMBER"] = [str(track.number)]
            flac.tags["DATE"] = [self.query.release_date]
            flac.tags["LABEL"] = [self.query.copyright]
            flac.tags["GENRE"] = [self.query.primary_genre_name]
            flac.tags["TITLE"] = [track.name]
            flac.tags["COMPILATION"] = ["0"]
            flac.save()
            flac.close()


class Album():
    """Process an audio stream into an Album

    Attributes
    ----------
    wavstream: wave.Wave_read
        Read access to wave file

    framerate: int
        rate, in Hz, of channel samples

    track_list: list
        list of itunespy.track.Track objects containing track tags

    wavstream: wave.File

    """

    def __init__(self, stream):
        self.wavstream = wave.open(stream.wavpath)

        # itunes
        self.track_list = stream.query.get_tracks()
        self.n_track = len(self.track_list)
        self.current = 0
        self.track = []

        # inherit from query
        self.target = stream.target
        self.name = stream.query.collection_name
        self.release_date = stream.query.release_date
        self.copyright = stream.query.copyright
        self.genre = stream.query.primary_genre_name
        self.artist = stream.query.artist_name

        # debug
        self.err = {"dur": [], "pos": []}
        self.cumtime = 0

    def cur_track_start(self):
        """find audio signal activity that exceeds threshold and persists
        call this the start frame of a track
        """
        track = self.track[self.current]
        threshold = 500
        persistence = 1
        found_count = 0
        preactivity_offset = 1 * FS_DEC
        firstindex = 0
        if self.current > 0:
            firstindex = self.track[self.current - 1].end_frame / DF

        index = firstindex
        while found_count <= persistence:
            if self.envelope[index] > threshold:
                found_count += 1
            else:
                found_count = 0
            index += 1

        # subtract off persistence and a preactivity_offset
        activity = index - persistence - preactivity_offset
        if activity < firstindex:
            activity = firstindex
        track.start_frame = activity * DF

    def cur_track_stop(self):
        """find the min energy point around a reference
        """
        track = self.track[self.current]
        n_samp_track = int(track.duration * MS2SEC * FS_DEC)
        reference = track.start_frame / DF + n_samp_track
        # +- 5 seconds around projected end frame
        excursion = 5 * FS_DEC
        curpos = reference - excursion
        go_till = np.min(
            [reference + excursion, self.wavstream.getnframes() / DF])
        local_min = 1e9
        local_idx = -1

        while curpos < go_till:
            if self.envelope[curpos] < local_min:
                local_min = self.envelope[curpos]
                local_idx = curpos
            curpos += 1

        track.end_frame = local_idx * DF
        track.n_frame = track.end_frame - track.start_frame

    def locate_track(self):
        """ find track starts/stops within stream
        """

        # find start of track (find activity)
        self.cur_track_start()

        # find end of track (find local min)
        self.cur_track_stop()

        return self

    def status(self):
        """ status """
        track = self.track[self.current]
        trackname = track.name.strip().replace("/", ";")

        # status prints
        print("{}".format(trackname))
        self.err["dur"].append(track.n_frame / FS - track.duration / 1000)
        self.err["pos"].append(track.start_frame / FS - self.cumtime)
        print("\tESTIMATED duration: %.2f sec         --> position: %.2f sec" %
              (track.n_frame / FS, track.start_frame / FS))
        print("\tEXPECTED            %.2f sec         -->           %.2f sec" %
              (track.duration / 1000, self.cumtime))
        print("\tERROR\t   (%.2f, %.2f) sec \t     --> (%.2f, %.2f) sec" %
              (np.mean(self.err["dur"]), np.std(self.err["dur"]),
               np.mean(self.err["pos"]), np.std(self.err["pos"])))

        self.cumtime += track.duration / 1000

        return self

    def finalize(self):
        """ finalize """
        with wave.open(self.track.path, 'w') as wavtrack:
            self.wavstream.setpos(self.track.start_frame)
            y = np.fromstring(
                self.wavstream.readframes(self.n_frame),
                dtype=np.int16)
            y = np.reshape(y, (int(y.shape[0] / 2), 2))
            wavtrack.setnchannels(2)
            wavtrack.setsampwidth(2)
            wavtrack.setnframes(self.n_frame)
            wavtrack.setframerate(self.wavstream.getframerate())
            wavtrack.writeframes(y)

    def process(self):
        """encapsulate the substance of Album processing
        """
        # iterate and initialize tracks
        for i in range(self.n_track):
            self.track.append(Track(self.track_list[i]))
            self.track[i].set_path(i, self.target)

        # compute audio power envelope
        self.envelope = wave_envelope(self.wavstream)

        # truncate zeros in beginning
        first_nz = np.nonzero(self.envelope)[0][0] - FS_DEC * 3
        self.envelope = self.envelope[first_nz:-1]
        self.imageit()

        # test envelope to expected
        n_sec_env = len(self.envelope) / FS_DEC
        n_sec_exp = sum([t.duration * MS2SEC for t in self.track])
        if abs(1 - n_sec_env / n_sec_exp) > .05:
            raise StreamError("envelope does not match expected duration")

        # iterate and process tracks
        for i in range(self.n_track):
            self.locate_track().status()
            self.current += 1

        self.imageit()

        # close the wav stream
        self.wavstream.close()

        return self

    def imageit(self):
        """ imageit """
        x_data = self.envelope < 20**2
        y = self.envelope / (np.max(self.envelope) * 0.008)
        n = np.shape(x_data)[0]
        n_min = int(n / FS_DEC / 60)

        plt.figure(figsize=(3 * n_min, 4))
        plt.plot(x_data, marker=".", linestyle='')
        # plt.plot(y, marker=".", linestyle='', markersize=3)
        plt.plot(y, marker=".", linestyle='')
        plt.ylim(0, 1.1)

        marks = np.cumsum([t.duration * MS2SEC * FS_DEC for t in self.track])
        [plt.axvline(x_data=mark, color="b", linestyle="--") for mark in marks]

        saveit('image')


class Track():
    def __init__(self, itrack):
        # copy from itunespy.Track
        self.duration = itrack.track_time
        self.name = itrack.track_name
        self.artist = itrack.artist_name
        self.number = itrack.track_number

        # streamy attrs
        self.start_frame = 0
        self.end_frame = 0
        self.n_frame = 0

    def set_path(self, i, root):
        self.index = i
        self.path = join(
            root, "%0.2d %s.wav" % (self.index + 1, self.name))


def get_mean_stereo(wav, N):
    """grab samples from one channel (every other sample) of frame
    """
    x_data = np.fromstring(wav.readframes(N), dtype=np.int16)
    return np.mean(np.reshape(x_data, (2, -1)), axis=0)


def wave_envelope(wavstream):
    """wave_envelope
    """

    print("computing audio energy at {} downsample rate...".format(DF))
    n_window = int(np.floor(wavstream.getnframes() / DF)) - 1
    x_data = np.zeros(n_window)
    for i in trange(n_window):
        x_data[i] = np.var(get_mean_stereo(wavstream, DF))

    return x_data


def start_shairport(filepath):
    """make sure no duplicate processes and start up shairport-sync
    """

    Popen(['killall', 'shairport-sync'])
    time.sleep(2)

    Popen(['{} {} > "{}"'.format(
        config['bin']['shairport-sync'], "-o=stdout", filepath)], shell=True)

    time.sleep(1)

    print("INFO: shairport up and running.")


def is_started(filepath):
    """test to see if recording has started
    """

    # reset seconds counter
    global seconds
    seconds = 0
    (init_size, last_size) = util.size_sampler(filepath)
    return last_size > init_size


class SimpleState(object):
    def __init__(self, filepath):
        self.count = 0
        self.filepath = filepath

    def get_state(self, state):
        """ return the file size, sampled with a 1 second gap to
        determine if the file is being written to.
        """

        init_size = os.path.getsize(self.filepath)
        time.sleep(1)
        last_size = os.path.getsize(self.filepath)

        self.count += 2    # one for size_sampler and one for main loop
        if self.count % 60 == 0:
            sys.stdout.write(".")
            sys.stdout.flush()

        if state == "finishd":
            return last_size == init_size

        elif state == "startd":
            return last_size > init_size


def generate_playlist(artist, album):
    """ generate_playlist """
    sed_program = 's/SEARCHTERM/"{} {}"/g'.format(
        artist, album).replace(":", "").replace("&", "")
    osa_prog = join(util.resolve(config["path"]["osa"]), "program.js")
    osa_temp = join(util.resolve(config["path"]["osa"]), "template.js")
    with open(osa_prog, "w") as osa:
        Popen([config['bin']['sed'], sed_program, osa_temp], stdout=osa)

    Popen([config['bin']['osascript'], osa_prog])


def dial_itunes(artist, album):
    """run apple script and attempt to uniquely locate the
    artist/album pair.
    """

    generate_playlist(artist, album)
    time.sleep(2)   # allow time to build playlist
    osa_prog = join(util.resolve(config["path"]["osa"]), "play")
    Popen([config['bin']['osascript'], osa_prog])


def saveit(name):
    """ saveit """
    savepath = join(util.resolve(config["path"]["envelopes"]), name + ".png")
    print("saving to {}".format(savepath))
    plt.savefig(savepath, bbox_inches='tight')


def image_audio_envelope_with_tracks_markers(markers, stream):
    """track-splitting validation image
    """

    x_data = wave_envelope(stream.wavpath)

    downsamp = config["streams"]["downsample_factor"]
    efr = 44100 / downsamp
    starts = [mark[0] / downsamp for mark in markers]
    stops = [starts[i] + mark[1] / downsamp for i, mark in enumerate(markers)]
    n = np.shape(x_data)[0]
    n_min = int(n / efr / 60)

    # create image (one inch per minute of audio)
    plt.figure(figsize=(n_min, 10))
    plt.plot(x_data, marker=".", linestyle='', markersize=0.2)
    [plt.axvline(
        x_data=start, color="b", linestyle="--",
        linewidth=0.3) for start in starts]
    [plt.axvline(
        x_data=stop, color="r", linestyle="--",
        linewidth=0.3) for stop in stops]
    saveit(stream.name)


# --------
# Programs
# --------
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
        with open(listing) as fptr:
            batch = json.load(fptr)
    except OSError:
        util.printr(
            "Stream successfully started, " +
            "waiting for finish (one dot per min.)...")

        # wait for stream to finish
        while not monitor.get_state("finishd"):
            time.sleep(1)
        util.printr("Stream successfully finished.")

        os.rename(TMPSTREAM, pcm_path)
        os.rename(TMPSTREAM, pcm_path)

    util.printr("Batch successfully finished.")


def stream2tracks(streampath):
    """process raw pcm stream to tagged album tracks.
    """
    util.printr("Begin stream2tracks...")

    # initialize the stream
    stream = Stream(streampath)
    stream.decode_path().itunes_query().prepare_target().pcm2wav()

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
    streams = glob(os.path.join(util.resolve(config["path"]["pcm"]), "*pcm"))
    for streampath in streams:
        stream2tracks(streampath)
