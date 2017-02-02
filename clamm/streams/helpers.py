#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

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
    sed_program = 's/SEARCHTERM/"{} {}"/g'.format(artist, album).replace(":", "").replace("&", "")
    with open("osa-program.js", "w") as osa:
        Popen(['/usr/bin/sed', sed_program, 'osa-template.js'], stdout=osa)

    Popen(['/usr/bin/osascript', 'osa-program.js'])

def dial_itunes(artist, album):
    """ run apple script and attempt to uniquely locate the artist/album pair """

    generate_playlist(artist, album)
    time.sleep(2) # time to build playlist
    Popen(['/usr/bin/osascript', 'osa-play'])

