#/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
from subprocess import call
import re

# external
from translate import Translator

# locals
artist_tag_names = ["ALBUMARTIST_CREDIT", "ALBUM ARTIST", "ARTIST", "ARTIST_CREDIT", "ALBUMARTIST"]
from clamm import util
def get_translation(search_string):
    """ occasionally artist name will be in non-Latin characters """

    tr = Translator(input("Enter from language: "), 'en')
    return tr.translate(search_string)

def get_artist_tagset(tagfile):
    tags = tagfile.tags
    atags = {t: re.split(util.SPLIT_REGEX, ', '.join(tags[t])) for t in artist_tag_names if t in tags.keys()}
    aset = set([v.strip() for val in atags.values() for v in val])
    return aset

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

def messylist2tagstr(alist):
    s, delim = "", "; "
    for i, item in enumerate(alist):
        if isinstance(item, list): item = item[0]
        if i == len(alist) - 1: delim = ""
        s += "{}{}".format(item, delim)

    return s

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

