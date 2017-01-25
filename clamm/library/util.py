#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
import json
import re
from os.path import join, splitext
from subprocess import call
import sys

SPLIT_REGEX = '&\s*|,\s*|;\s*| - |:\s*|/\s*| feat. | and '
artist_tag_names = ["ALBUMARTIST_CREDIT", "ALBUM ARTIST", "ARTIST", "ARTIST_CREDIT", "ALBUMARTIST"]
COUNT = 0

def wav2flac(wav_name):
    """ use ffmpeg to convert a wav file to a flac file """
    call(["ffmpeg", "-hide_banner", "-y", "-i", wav_name, wav_name.replace("wav", "flac")])
    if not config["library"]["keep_wavs_once_flacs_made"]: os.remove(wav_name)

def is_audio_file(name): return splitext(name)[1] in config["file"]["known_types"]

def audio2flac(fpath, fname):
    fext = splitext(fname)[1]
    if fext == config["file"]["preferred_type"]: return
    print("converting {} to flac...".format(fname))
    src = join(fpath, fname)
    dst = join(fpath, fname.replace(fext, config["file"]["preferred_type"]))
    with open("/dev/null", "w") as redirect:
        call(["ffmpeg", "-hide_banner", "-y", "-i", src, dst], stdout=redirect)

def messylist2tagstr(alist):
    s, delim = "", "; "
    for i, item in enumerate(alist):
        if isinstance(item, list): item = item[0]
        if i == len(alist) - 1: delim = ""
        s += "{}{}".format(item, delim)

    return s

def perms2set(D):
    clist = list(D.keys())
    blist = [D[c]["permutations"] for c in clist]
    # flatten
    blist = [item for sublist in blist for item in sublist]
    clist.extend(blist)
    cset = messylist2set(clist)
    return cset

def messylist2set(alist):
    """ owing to laziness, these lists may contain gotchas """
    y = [item for item in alist if item.__class__ is str and len(item) > 0]
    return set(y)

def get_artist_tagset(tagfile):
    tags = tagfile.tags
    atags = {t: re.split(SPLIT_REGEX, ', '.join(tags[t])) for t in artist_tag_names if t in tags.keys()}
    aset = set([v.strip() for val in atags.values() for v in val])
    return aset

def log_missing_tag(key, tagfile):
    with open(config["path"]["troubled_tracks"]) as f:
        tt = json.load(f)
        tpath = tagfile.path.replace(config["path"]["library"], "$LIBRARY")
        if key in tt["missing_tag"].keys():
            if tpath not in tt["missing_tag"][key]:
                tt["missing_tag"][key].append(tpath)
        else:
            tt["missing_tag"][key] = [tpath]

    with open(config["path"]["troubled_tracks"], mode="w") as f:
        json.dump(tt, f, ensure_ascii=False, indent=4)

def swap_first_last_name(name_str):
    """ if name_str contains a comma (assume it is formatted as Last, First),
        invert and return First Last
        else, invert and return Last, First
    """

    comma_idx = name_str.find(",")
    name_parts = name_str.replace(",", "").split(" ")

    if comma_idx > -1:
        swapd =  "{} {}".format(name_parts[1], name_parts[0])
    else:
        swapd =  "{}, {}".format(name_parts[1], name_parts[0])

    return swapd

def commit_on_delta(tagfile, tag_key, lib_val):
    tag_dict = tagfile.tags
    no_key = tag_key not in tag_dict.keys()
    is_delta = True
    if not no_key:
        tag_val = tag_dict[tag_key]
        if isinstance(tag_val, list): tag_val = tag_val[0]
        is_delta = tag_val != lib_val

    if no_key or is_delta:
        tag_dict[tag_key] = lib_val
        tagfile.tags = tag_dict
        commit_to_tagfile(tagfile)

def commit_to_tagfile(tagfile, glob=""):
    global COUNT
    COUNT += 1
    if config["use_safety_when_committing"]:
        print("Proposed: ")
        [print("\t%s: %s" % (k, v)) for k, v in sorted(tagfile.tags.items()) if glob in k]
        if not input("Accept? [y]/n: "): tagfile.save()

    else:
        sys.stdout.write("."); sys.stdout.flush()
        tagfile.save()

class UnverifiedError(Exception):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

