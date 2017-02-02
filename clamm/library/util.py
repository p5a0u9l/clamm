#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
from subprocess import call
from os.path import join, splitext
import sys

# local
from clamm import util as cutil
from clamm.util import config

def wav2flac(wav_name):
    """ use ffmpeg to convert a wav file to a flac file """
    call([config["bins"]["ffmpeg"], config["opts"]["ffmpeg"], "-i", \
            wav_name, wav_name.replace("wav", "flac")])
    if not config["library"]["keep_wavs_once_flacs_made"]:
        os.remove(wav_name)

def is_audio_file(name): return splitext(name)[1] in config["file"]["known_types"]

def make_flacs(target):
    """ convert wav files in target to flac files, clean up wav files"""
    [wav2flac(wav) for wav in glob(join(target, "*wav"))]

def commit_to_libfile(tagfile):
    """ final stop for writing values from tag database into an audio file """

    # record if differences exist
    n_delta_fields, n_tracks_updated = 0, 0

    for k, v in tagfile.tags.items():
        is_new = k not in tagfile.tag_copy.keys()
        if not is_new:
            is_dif = tagfile.tags[k] != tagfile.tag_copy[k]
        if is_new or is_dif:
            n_delta_fields += 1

    # short-circuit if no changes to be made
    if n_delta_fields == 0: return (n_tracks_updated, n_delta_fields)

    # prompted or automatic write
    if config["database"]["require_prompt_when_committing"]:
        cutil.printr("Proposed: "); cutil.pretty_dict(sorted(tagfile.tags))

        if not input("Accept? [y]/n: "):
            n_tracks_updated += 1
            tagfile.save()

    else:
        n_tracks_updated += 1
        tagfile.save()
        cutil.printr(lambda: [sys.stdout.write("."), sys.stdout.flush()])

    return (n_tracks_updated, n_delta_fields)

