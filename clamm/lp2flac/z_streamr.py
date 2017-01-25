#!/usr/bin/env python

import pyaudio
import zmq
import socket
import sys
import time
import wave
from subprocess import Popen, call
from glob import glob
from os.path import join
import os

# Record over network usage example
# on remote machine
#$ ./streamr.py callisto stream sound
# on local machine
#$ ./streamr.py callisto listen disk filename

# setup options
ip = sys.argv[1]
role = sys.argv[2] # stream/listen
device = sys.argv[3] # disk/sound

# setup pyaudio
pa = pyaudio.PyAudio()
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 48000

# setup zmq
ctx = zmq.Context()
lu = {'stream': [zmq.PUB, 'from'], 'listen': [zmq.SUB, 'to']}
sock = ctx.socket(lu[role][0])

# setup wave
if device == 'disk':
    disk_target = sys.argv[4]

    if role == 'listen':
        wav = wave.open(disk_target, 'wb')
        wav.setnchannels(CHANNELS)
        wav.setsampwidth(pa.get_sample_size(pyaudio.paInt16))
        wav.setframerate(RATE)

    elif role == 'stream':
        flac_files = glob(join(disk_target, '*.flac'))

        wav_file = "/Users/paul/tmp.wav"
        if os.path.exists(wav_file):
            os.remove(wav_file)

        call(['ffmpeg', '-loglevel', 'quiet', '-i', flac_files[0], wav_file])
        wav = wave.open(wav_file, 'rb')

def callback(data, frame_count, time_info, status):
    if role == 'listen':
        data = sock.recv()

        if device == 'disk': wav.writeframes(data)

    elif role == 'stream':
        if device == 'disk': data = wav.readframes(1024)

        sock.send(data)

    return (data, pyaudio.paContinue)

def init_zmq():
    tcp = "tcp://%s:5555" % socket.gethostbyname(ip)
    if role == 'listen':
        # zmq
        sock.connect(tcp)
        sock.setsockopt(zmq.SUBSCRIBE, '')

    elif role == 'stream':
        # zmq
        sock.bind(tcp)

if role == 'listen':
    stream = pa.open(format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        output=True,
        stream_callback=callback)

elif role == 'stream':
    stream = pa.open(format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        stream_callback=callback)

print "%sing %s %s on %s" % (role, lu[role][1], device, ip)

init_zmq()

while stream.is_active():
    time.sleep(0.1)

# stop stream
stream.stop_stream()
stream.close()

# close pyaudio/zmq
pa.terminate()

def album():
    init_zmq()
    stream = init_stream()

    for flac in flac_files:

        if os.path.exists(wav_file):
            os.remove(wav_file)

        call(['ffmpeg', '-loglevel', 'quiet', '-i', flac, wav_file])
        wav = wave.open(wav_file, 'rb')

        while stream.is_active():
            time.sleep(0.1)

        # stop stream
        stream.stop_stream()
        stream.close()

    # close pyaudio/zmq
    pa.terminate()
