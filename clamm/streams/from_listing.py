"""create a batch of pcm streams by interfacing with iTunes
"""

import os
import time
import subprocess
import json


from clamm import config
from clamm import util


TMPSTREAM = os.path.join(config["path"]["wav"], "temp.wav")


def dial_itunes(artist, album):
    """run apple script and attempt to uniquely locate the
    artist/album pair.
    """

    util.printr("talking to iTunes...")
    util.generate_playlist(artist, album)
    time.sleep(2)   # allow time to build playlist
    osa_prog = os.path.join(config["path"]["osa"], "play")
    subprocess.Popen(['osascript', osa_prog])


def main(listing):
    """a program for batch streaming a ``json`` listing of albums
    from iTunes to raw pcm files via ``shairport-sync``.

    iTunes is controlled using macos' built-in ``osascript`` tool and
    simple javascript request templates.

    When the listings have finished streaming, the pcm files (streams)
    can be processed by ``stream2tracks`` and converted from streams
    to a collection of flac tracks.
    """

    util.printr("Begin streams.from_listing...")

    # fetch the album listing
    with open(listing) as fptr:
        batch = json.load(fptr)

    # iterate over albums in the listing
    for key, val in batch.items():

        util.start_shairport(TMPSTREAM)

        artist, album = val['artist'], val['album']
        wav = "{}; {}.wav".format(artist, album)
        wav_path = os.path.join(config["path"]["wav"], wav)

        util.printr("{} --> begin listing2streams stream of {}..."
                    .format(time.ctime(), wav))

        dial_itunes(artist, album)

        monitor = util.SimpleState(TMPSTREAM)
        while not monitor.get_state("startd"):
            time.sleep(1)

        util.printr("Stream successfully started, "
                    " now waiting for finish (one dot per minute)...")

        while not monitor.get_state("finishd"):
            time.sleep(1)

        util.printr("Stream successfully finished.")

        os.rename(TMPSTREAM, wav_path)

    util.printr("Batch successfully finished.")


if __name__ == "__main__":
    main()
