#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
import wave
from os.path import join
from glob import glob

# local
from clamm.util import config
from clamm.streams import util, albumstream


def main():
    """ batch process wav streams to flac album tracks with metadata """

    # iterate over streams found in wav/ staging area
    for stream_path in glob(join(config["path"]["streams"], "wav", "*wav")):

        # prepare processing
        (artist, album) = util.decode_stream_path(stream_path)
        query = util.itunes_lookup(artist, album)
        target = util.prep_album_target_dir(query)

        # process a stream
        with wave.open(stream_path) as wav:
            stream = albumstream.AlbumStream(wav, query, target)

            # iterate over and process tracks derived from itunes search
            for i, track in enumerate(stream.tracks):
                stream.create(i, track).consume(i).finalize()

            # compute track-splitting validation image
            x = stream.power_envelope()
            albumstream.plot_envelope_splits(
                    x, stream.splits, artist + ";" + album)

        # finalize the stream into flac files with tags
        # derived from itunes query
        util.make_flacs(target)
        util.metastize(query, target)


if __name__ == '__main__':
    main()
