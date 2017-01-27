#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
import wave
from glob import glob
import os
from os.path import join
import sys

# external
import taglib

# local
from clamm import util, config
from clamm.library import taghelpers,
import albumstream

def prep_album_target_dir(query):
    artist_dir = join(config["path"]["library"], query.artist_name)
    target = join(artist_dir, query.collection_name)

    if not os.path.exists(artist_dir): os.mkdir(artist_dir)
    if not os.path.exists(target): os.mkdir(target)

    return target

def decode_stream_path(stream_name):
    """ artist/album names from stream name """
    [artist, album] = stream_name.replace(".wav", "").split(";")
    artist = os.path.split(artist)[-1]
    album = album.strip()
    print("Found %s as target album" % (stream_name))
    return (artist, album)

def main():
    """ batch process wav streams to flac album tracks with metadata """

    # iterate over streams found in wav/ staging area
    for stream_path in glob(join(config["path"]["streams"], "wav", "*wav")):

        # prepare processing
        (artist, album) = decode_stream_path(stream_path)
        query = taghelpers.itunes_lookup(artist, album)
        target = prep_album_target_dir(query)

        # process a stream
        with wave.open(stream_path) as wav:
            stream = albumstream.AlbumStream(wav, query, target)

            # iterate over and process tracks derived from itunes search
            for i, track in enumerate(stream.tracks):
                stream.create(i, track).consume(i).finalize()

            # compute track-splitting validation image
            x = stream.power_envelope()
            albumstream.plot_envelope_splits(x, stream.splits, artist + ";" + album)

        # finalize the stream into flac files with tags derived from itunes query
        util.make_flacs(target)
        taghelpers.metastize(query, target)

if __name__ == '__main__': main()
