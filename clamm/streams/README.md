# streams description

## Contents

*   pcm

o   target directory for raw audio piped into a `pcm` file

*   wav

o   target directory for the output of `pcm` files converted to `wav` files

*   archive

o   resting home for processed `wav` streams

*   envelopes

o   container for `png` images produced by `stream2tracks.py` and used for validating effectiveness of track splitting.

## Steps to Create a New Wav Stream

### Create the PCM file

*   Stream audio to a new raw pulse-code modulation (PCM) file using the naming scheme

    ARTIST; ALBUM.pcm

NOTE:

Audio streaming can be achieved by several different means. The one which initiated this project
was capturing the output digital stream from an Analog-to-Digital Converter (ADC) receiving an analog audio
stream from a vinyl record player. This being the first step in a digitization project.

Another means can be using open-source software which accepts a digital stream from an arbitrary
source and provides hooks for forwarding that stream to different file streams.

An example of this second method is [mike brady's](https://github.com/mikebrady)
awesome [shairport-sync](https://github.com/mikebrady/shairport-sync)

Example command can be used,

    shairport-sync -o=stdout > "ARTIST; ALBUM.pcm"

*   Move the `pcm` file to the `pcm` directory.

*   Repeat for `N` audio streams

### Convert PCMs to wav files

*   Execute `./pcm2wav.sh`

o   Calls `ffmpeg` and adds `wav` header using the following, assumed, stream parameters

44.1 kHz sampling rate, 16 bit (little endian) resolution, 2 channel stereo interleaved

### Convert wav Streams to Tracks

*   Run `stream2tracks.py`

*   Files in `wav` can be moved to `archive`. The `wav` folder is a staging area or `stream2tracks.py`.
