#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# local
from clamm.streams import util, albumstream


def main(streampath):
    """
    process raw pcm stream to tagged album tracks
    """

    print("INFO: Begin stream2tracks...")
    # initialize the stream
    stream = albumstream.Stream(streampath)
    stream.decode_path().iQuery().prepare_target().pcm2wav()

    # process the stream into an album
    album = albumstream.Album(stream).process()

    # finalize the stream into flac files with tags
    stream.make_flacs().tagify()

    # create an image of the audio envelope indicating where track splits
    # have been located
    util.image_audio_envelope_with_tracks_markers(album.splits, stream)

    print("INFO: Finish stream2tracks.")


if __name__ == '__main__':
    main()
