#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
import re
from os.path import splitext, join
from os import walk
import os
from subprocess import Popen, call
import sys

# local
import clamm
from config import config
import tags


class AudioLib():
    """
    external interface to audiolib module
    """
    def __init__(self, args):
        self.root = args.dir
        self.func = args.sub_cmd
        self.ltfa = LibTagFileAction(args)

    def walker(self, func, **kwargs):
        """
        iterate over every audio file under the target directory
        pass the tagfile and apply action to each
        """
        # walk every file under root
        for folder, _, files in walk(self.root, topdown=False):
            if not files:
                continue

            print("walked into {}...".format(
                folder.replace(config["path"]["library"], "$LIBRARY")))

            self.ltfa.count["album"] += 1
            for name in files:
                if not is_audio_file(name):
                    continue
                self.ltfa.count["file"] += 1
                func(tags.SafeTagFile(join(folder, name)), **kwargs)

        # initiate post-walk follow_up
        self.follow_up()

    def follow_up(self, **kwargs):
        if self.func == "synchronize":
            after_action_review(self.ltfa.count)

    def synchronize(self):
        """
        special hook for ensuring the tag database and the library file
        tags are sync'd.
        """

        self.walker(self.ltfa.synchronize_composer)
        self.walker(self.ltfa.synchronize_artist)

    def initialize(self):
        """
        special hook for consuming new music into library.
        """

        self.walker(self.ltfa.audio2preferred_format)
        self.walker(self.ltfa.synchronize_composer)
        self.walker(self.ltfa.prune_artist_tags)
        self.walker(self.ltfa.remove_junk_tags)
        self.walker(self.ltfa.handle_composer_as_artist)
        self.walker(self.ltfa.synchronize_artist)


class LibTagFile():
    def __init__(self, args):
        """
        super class for tagfile action classes
        """

        # arg unpack
        self.args = args
        self.tagdb = tags.TagDatabase()
        self.action = self.args.sub_cmd
        self.tagdb.update_sets()

        # stats
        self.count = {"tag": 0, "track": 0, "album": 0, "file": 0}

    def write2tagfile(self, tagfile):
        (a, b) = commit_to_libfile(tagfile)
        self.count["track"] += a
        self.count["tag"] += b


class LibTagFileAction(LibTagFile):
    def __init__(self, args):
        """
        LibTagFileAction is a collection of library tag file _action_
        methods.

        Each action method follows a methodical implementation
            1. recieves a tagfile as an input
            2. has access to argparser tui args and must use consistent
                Namespace references
            3. has the option/necessity to create a persistent result
            4. should define a follow-up action upon completion of
            tags.walker
        """

        LibTagFile.__init__(self, args)

        # helper attrs
        self.last_composer = ""     # persistent storage for last composer

        # auto_suggest
        self.composer_suggest = tags.TagSuggestion(
                self.tagdb, category="composer")

        # wrap methods in dictionary for dynamic access
        self.func = {}
        for attr in dir(self):
            fobject = eval('self.{}'.format(attr))
            if hasattr(fobject, '__func__'):
                self.func[attr] = fobject

    def audio2preferred_format(self, tagfile, **kwargs):
        """
        using ffmpeg, convert arbitrary audio file to preferred_type,
        flac by default
        """

        # unpack
        (fpath, fname) = os.path.split(tagfile.path)
        fext = os.path.splitext(tagfile.path)

        # short-circuit if file is already preferred_type
        if fext == config["file"]["preferred_type"]:
            return

        # otherwise, proceed
        print("converting {} to {}...".format(fname, fext))
        src = tagfile.path
        dst = join(
                fpath, fname.replace(fext, config["file"]["preferred_type"]))

        # and the conversion itself
        with open("/dev/null", "w") as redirect:
            Popen([config["bin"]["ffmpeg"],
                  config["opt"]["ffmpeg"], "-i", src, dst],
                  stdout=redirect)

    def playlist(self, tagfile, **kwargs):
        """
        playlist filter
        """

        # unpack
        ftags = tagfile.tags
        sq = kwargs["sq"]

        try:
            if ftags["COMPILATION"][0] == "1":
                return
        except KeyError:
            tags.log_missing_tag("COMPILATION", tagfile)

        if sq.operators[0] == "AND":
            include = True
            for i, filt in enumerate(sq.filters):
                key = sq.keys[i]
                try:
                    if filt[key] not in ftags[key]:
                        include = False
                except KeyError:
                    include = False
                    tags.log_missing_tag(key, tagfile)

        elif sq.operators[0] == "OR":
            include = False

            for i, filt in enumerate(sq.filters):
                key = sq.keys[i]
                if filt[key] in ftags[key]:
                    include = True

        if include:
            self.playlist.append(tagfile.path)

    def prune_artist_tags(self, tagfile, **kwargs):
        """
        Conform artist/albumartist tag key names by applying
        config['library']['tags']['prune_artist'] rules
        e.g., ALBUMARTIST instead of ALBUM_ARTIST
        """

        ftags = tagfile.tags

        # make sure we have at least the basics
        has_minimal_artist_set = set(
                config["library"]["tags"]["keep_artist"]).intersection(
                        set(ftags))
        if not has_minimal_artist_set:
            return

        # apply deletion
        tagfile.tags = {key: val for key, val in ftags.items()
                        if key not in
                        config["library"]["tags"]["prune_artist"]}

        # write to file
        self.write2tagfile(tagfile)

    def remove_junk_tags(self, tagfile, **kwargs):
        """
        similar to prune_artist_tags, but indiscriminately removes tags in
        junk list
        """

        ftags = tagfile.tags

        # apply deletion
        tagfile.ftags = {
                key: val for key, val in ftags.items()
                if key not in config["library"]["tags"]["junk"]
                }

        # write to file
        self.write2tagfile(tagfile)

    def delete_tag_globber(self, tagfile, **kwargs):
        """
        Unlike `remove_junk_tags`, allows removing as set of similarly
        named tags, as in the MUSICBRAINZ_* tags, without cluttering
        the junk list with excessive entries.
        """

        untag = self.args.tag_key
        ftags = tagfile.tags

        # apply deletion
        tagfile.tags = {k: v for k, v in ftags.items() if untag not in untag}

        # write to file
        self.write2tagfile(tagfile)

    def change_tag_by_name(self, tagfile, **kwargs):
        """
        globally change a single tag field, applied to a directory or library
        In entire library context, useful for setting GENRE=classical,
        or COMPILATION=0, etc.
        In single album/directory context, useful for setting
        ALBUMARTIST=NAME, manually
        """

        curkey = self.args.tag_key
        newval = self.args.tag_val
        curval = ""

        # use the value, if its there
        if curkey in tagfile.tags.keys():
            curval = tagfile.tags[curkey]

        # get the new tag value (input arg or manual)
        if not newval:
            new_val = input(
                    "Changing {} tag...\n\tCurrent Value: {}\n\tEnter new: "
                    .format(curkey, curval))

        # apply the change
        tagfile.tags[curkey] = new_val

        # write to file
        self.write2tagfile(tagfile)

    def handle_composer_as_artist(self, tagfile, **kwargs):
        """
        test for and handle composer in artist fields.
        Background:
            Many taggers/publishers deal with classical music tags by
            lumping the composer in with the artist, as in
            ARTIST=JS Bach; Glenn Gould
        """

        # existence test
        aset = tags.get_artist_tagset(tagfile)
        acom = aset.intersection(self.tagdb.sets["composer"])

        # null hypothesis --> do nothing
        if not acom:
            return

        # detection action (check each ARTIST field and diff where found)
        for key, val, in tagfile.tags.items():
            if key.find("ARTIST") > -1:
                atags = re.split(clamm.SPLIT_REGEX, ', '.join(val))
                aset = set([val.strip() for val in atags])
                if aset.difference(acom):
                    tagfile.tags[key] = tags.messylist2tagstr(
                            list(aset.difference(acom)))
                else:
                    tagfile.tags[key] = input('Enter artist name: ')

        # write to file
        self.write2tagfile(tagfile)

    def synchronize_artist(self, tagfile, **kwargs):
        """
        Verify there is an artist entry in tags.json for each artist found in
        tagfile.
        Find arrangement that is best fit for a given file.
        Sync files to library.
        """

        # match artist to database entry for each artist found in tagfile
        [self.tagdb.verify_artist(name)
            for name in tags.get_artist_tagset(tagfile)]

        # hook in the arangement, defined as the pairing of
        # artist to instrument
        arrange = self.tagdb.verify_arrangement(
                tagfile,
                skipflag=config["database"]["skip_existing_arrangements"])

        if not arrange:
            return
        if config["database"]["sync_to_library"]:
            arrange.apply(tagfile)

    def synchronize_composer(self, tagfile, **kwargs):
        """
        Verify there is a corresponding entry in tags.json for
        the composer found in the tag file.
        If an entry is not found, user is prompted to add a new
        composer.
        """

        # must first assume the file is missing COMPOSER
        # and bootstrap from there
        if "COMPOSER" not in tagfile.tags.keys():
            # print the fields for context
            clamm.pretty_dict(tagfile.tags)

            # attempt to use last_composer (speeds up when adding new album)
            fmt = "Accept last input: {} ? [CR]".format(self.last_composer)
            if not input(fmt):
                cname = self.last_composer
            else:
                cname = self.composer_suggest.prompt("Enter composer name: ")
        else:
            cname = tagfile.tags["COMPOSER"]

        # update last_composer
        self.last_composer = cname

        # retrieve the composer key from the database
        ckey = self.tagdb.verify_composer(cname)

        # retrieve the composer fields from the database
        composer = self.tagdb.composer[ckey]

        # write database values to tagfile tags
        tagfile.tags["COMPOSER"] = ckey
        tagfile.tags["COMPOSER_ABBREVIATED"] = composer["abbreviated"]
        tagfile.tags["COMPOSER_DATE"] = composer["borndied"]
        tagfile.tags["COMPOSER_PERIOD"] = composer["period"]
        tagfile.tags["COMPOSER_SORT"] = composer["sort"]
        tagfile.tags["COMPOSER_NATION"] = composer["nationality"]

        # ensure the files are sync'd to database
        self.write2tagfile(tagfile)

    def get_artist_counts(self, tagfile, **kwargs):
        """
        count/record artist occurences (to use as ranking)
        """

        aset = tags.get_artist_tagset(tagfile)

        for aname in aset:
            artistname = self.tagdb.match_from_perms(aname)
            if artistname in self.instrument_groupings.keys():
                self.instrument_groupings[artistname] += 1
            else:
                self.instrument_groupings[artistname] = 1

    def get_arrangement_set(self, tagfile, **kwargs):
        """
        get set and count of instrumental groupings via sorted arrangements
        """

        # returns arrangement sorted by artist count
        sar = self.tagdb.get_sorted_arrangement(tagfile).values()

        # init/increment arrangement
        found = False
        for key, val in self.instrument_groupings.items():
            if sar == key:
                found = True
                self.instrument_groupings[key] += 1

        if not found:
            self.instrument_groupings[sar] = 1


def after_action_review(count):
    clamm.printr("AAR: file/folder count, track/album deltas")
    clamm.pretty_dict(count)


def pcm2wav(pcm_name, wav_name):
    """
    wrapper for using ffmpeg to convert a pcm file to a wav file
    """

    call(
            [config["bin"]["ffmpeg"],
                "-hide_banner",
                "-y", "-f", "s16le", "-ar", "44.1k", "-ac", "2", "-i",
                pcm_name, wav_name])

    keep_pcms = config["library"]["keep_pcms_once_wavs_made"]
    if not keep_pcms and os.path.exists(wav_name):
        os.remove(pcm_name)


def wav2flac(wav_name):
    """
    wrapper for using ffmpeg to convert a wav file to a flac file
    """
    call(
            [config["bin"]["ffmpeg"],
                "-hide_banner", "-y", "-i",
                wav_name, wav_name.replace(".wav", ".flac")])

    if not config["library"]["keep_wavs_once_flacs_made"]:
        os.remove(wav_name)


def is_audio_file(name):
    """
    readability short-cut for whether file contains known audio extension
    """
    return splitext(name)[1] in config["file"]["known_types"]


def commit_to_libfile(tagfile):
    """
    common entry point for writing values from tag database into an audio file
    """

    # check if differences (or newness) exists
    n_delta_fields, n_tracks_updated = 0, 0
    for k, v in tagfile.tags.items():
        is_new = k not in tagfile.tag_copy.keys()
        if not is_new:
            is_dif = tagfile.tags[k] != tagfile.tag_copy[k]
        if is_new or is_dif:
            n_delta_fields += 1

    # short-circuit if no changes to be made
    if n_delta_fields == 0:
        return (n_tracks_updated, n_delta_fields)

    # prompted or automatic write
    if config["database"]["require_prompt_when_committing"]:
        clamm.printr("Proposed: ")
        clamm.pretty_dict(sorted(tagfile.tags))

        if not input("Accept? [y]/n: "):
            n_tracks_updated += 1
            tagfile.save()

    else:
        n_tracks_updated += 1
        tagfile.save()
        clamm.printr(lambda: [sys.stdout.write("."), sys.stdout.flush()])

    return (n_tracks_updated, n_delta_fields)
