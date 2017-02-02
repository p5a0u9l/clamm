#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
import sys
import re
from os.path import join
from os import walk
import os

# local
from clamm.library import util as libutil
from clamm.tag import util as tagutil
from clamm import util as cutil
from clamm.util import config
from clamm.tag import tags

class AudioLib():
    """external interface to audiolib module
    """
    def __init__(self, args):
        self.root = args.dir
        self.func = args.sub_cmd
        self.ltfa = LibTagFileAction(args)

    def __repr__(self):
        print("Root: {}".format(self.root))

    def walker(self, func, **kwargs):
        """iterate over every audio file under the target directory
        pass the tagfile and apply action to each
        """
        # walk every file under root
        for folder, _, files in walk(self.root, topdown=False):
            if not files: continue

            print("walked into {}...".format(folder.\
                    replace(config["path"]["library"], "$LIBRARY")))

            self.ltfa.count["album"] += 1
            for name in files:
                if not libutil.is_audio_file(name): continue
                self.ltfa.count["file"] += 1
                func(tags.SafeTagFile(join(folder, name)), **kwargs)

        # initiate post-walk follow_up
        self.follow_up()

    def follow_up(self, **kwargs):
        if self.func == "synchronize":
            after_action_review(self.ltfa.count)

    def synchronize(self):
        """ special hook for ensuring the tag database and the library file tags are sync'd
        """
        self.walker(self.ltfa.synchronize_composer)
        self.walker(self.ltfa.synchronize_artist)

    def initialize(self):
        """ special hook for consuming new music into library"""
        self.walker(self.ltfa.audio2preferred_format)
        self.walker(self.ltfa.synchronize_composer)
        self.walker(self.ltfa.prune_artist_tags)
        self.walker(self.ltfa.remove_junk_tags)
        self.walker(self.ltfa.handle_composer_as_artist)
        self.walker(self.ltfa.synchronize_artist)

class LibTagFile():
    def __init__(self, args):
        """ super class for tagfile action classes """

        # arg unpack
        self.args = args
        self.tagdb = tags.TagDatabase()
        self.action = self.args.sub_cmd
        self.tagdb.update_sets()

        # stats
        self.count = {"tag": 0, "track": 0, "album": 0, "file": 0}

    def write2tagfile(self, tagfile):
        (a, b) = libutil.commit_to_libfile(tagfile)
        self.count["track"] += a; self.count["tag"] += b

class LibTagFileAction(LibTagFile):
    def __init__(self, args):
        """ LibTagFileAction is a collection of library tagfile action methods
            each action method should follow a methodical implementation
                1. each recieves a tagfile as an input
                2. each has access to argparser tui args and must use consistent Namespace references
                3. each has the option/necessity to create a persistent result
                4. each should define a follow-up action upon completion of tags.walker
        """

        LibTagFile.__init__(self, args)

        # helper attrs
        self.last_composer = "" # persistent storage for last composer

        # wrap methods in dictionary for dynamic access
        self.func = {}
        for attr in dir(self):
            fobject = eval('self.{}'.format(attr))
            if hasattr(fobject, '__func__'):
                self.func[attr] = fobject

    def audio2preferred_format(self, tagfile, **kwargs):
        """ using ffmpeg, convert arbitrary audio file to preferred_type,
            flac by default
        """

        # unpack
        (fpath, fname), fext = os.path.split(tagfile.path), os.path.splitext(tagfile.path)

        # short-circuit if file is already preferred_type
        if fext == config["file"]["preferred_type"]: return

        # otherwise, proceed
        print("converting {} to {}...".format(fname, fext))
        src = tagfile.path
        dst = join(fpath, fname.replace(fext, config["file"]["preferred_type"]))

        # and the conversion itself
        with open("/dev/null", "w") as redirect:
            call([config["bins"]["ffmpeg"], \
                    config["opts"]["ffmpeg"], "-i", src, dst], stdout=redirect)

    def playlist(self, tagfile, **kwargs):
        """ playlist filter """

        # unpack
        tags = tagfile.tags
        sq = kwargs["sq"]

        try:
            if tags["COMPILATION"][0] == "1": return
        except KeyError:
            tagutil.log_missing_tag("COMPILATION", tagfile)

        if sq.operators[0] == "AND":
            include = True
            for i, filt in enumerate(sq.filters):
                key = sq.keys[i]
                try:
                    if filt[key] not in tags[key]: include = False
                except KeyError:
                    include = False
                    tagutil.log_missing_tag(key, tagfile)

        elif sq.operators[0] == "OR":
            include = False

            for i, filt in enumerate(sq.filters):
                key = sq.keys[i]
                if filt[key] in tags[key]: include = True

        if include: self.playlist.append(tagfile.path)

    def prune_artist_tags(self, tagfile, **kwargs):
        """ apply config rules to conform artist/albumartist tags """

        tags = tagfile.tags

        # make sure we have at least the basics
        if not set(config["library"]["tags"]["keep_artist"]).intersection(set(tags)): return

        # apply deletion
        tagfile.tags = {key: val for key, val in tags.items() \
                if key not in config["library"]["tags"]["prune_artist"]}

        # write to file
        self.write2tagfile(tagfile)

    def remove_junk_tags(self, tagfile, **kwargs):
        """ similar to prune_artist_tags, but indiscriminately
            removes tags in junk list
        """
        tags = tagfile.tags

        # apply deletion
        tagfile.tags = {key: val for key, val in tags.items() \
                if key not in config["library"]["tags"]["junk"]}

        # write to file
        self.write2tagfile(tagfile)

    def delete_tag_globber(self, tagfile, **kwargs):
        """ Unlike remove_junk_tags, allows removing as set of similarly named tags,
        as in the MUSICBRAINZ_* tags, without cluttering the junk list with excessive entries
        """
        untag = self.args.tag_key
        tags = tagfile.tags

        # apply deletion
        tagfile.tags = {k: v for k, v in tags.items() if untag not in key}

        # write to file
        self.write2tagfile(tagfile)

    def change_tag_by_name(self, tagfile, **kwargs):
        """ globally change a single tag field, applied to a directory or library
        Usage:
            In entire library context, useful for setting GENRE=classical, or COMPILATION=0, etc.
            In single album/directory context, useful for setting ALBUMARTIST=NAME, manually
            If no tag value is given as input, user is prompted for a value
        """

        curkey = self.args.tag_key
        newval = self.args.tag_val
        curval = ""

        # use the value, if its there
        if curkey in tagfile.tags.keys():
            curval = tagfile.tags[curkey]

        # get the new tag value (input arg or manual)
        if not newval:
            new_val = input("Changing {} tag...\n\tCurrent Value: {}\n\tEnter new: "\
                        .format(curkey, curval))

        # apply the change
        tagfile.tags[curkey] = new_val

        # write to file
        self.write2tagfile(tagfile)

    def handle_composer_as_artist(self, tagfile, **kwargs):
        """ test for and handle composer in artist fields.
        Background:
            Many taggers/publishers deal with classical music tags by lumping the composer in
            with the artist, as in ARTIST=JS Bach; Glenn Gould
        """

        # existence test
        aset = tagutil.get_artist_tagset(tagfile)
        acom = aset.intersection(self.tagdb.sets["composer"])

        # null hypothesis --> do nothing
        if not acom: return

        # detection action (check each ARTIST field and diff where found)
        for key, val, in tagfile.tags.items():
            if key.find("ARTIST") > -1:
                atags = re.split(cutil.SPLIT_REGEX, ', '.join(val))
                aset = set([val.strip() for val in atags])
                if aset.difference(acom):
                    tagfile.tags[key] = tagutil.messylist2tagstr(list(aset.difference(acom)))
                else:
                    tagfile.tags[key] = input('Enter name: ')

        # write to file
        self.write2tagfile(tagfile)

    def synchronize_artist(self, tagfile, **kwargs):
        """ Verify there is an artist entry in tags.json for each artist found in tagfile.
            Find arrangement that is best fit for a given file.  Sync files to library.
        """

        # match artist to database entry for each artist found in tagfile
        [self.tagdb.verify_artist(name) for name in tagutil.get_artist_tagset(tagfile)]

        # hook in the arangement, defined as the pairing of artist to instrument
        arrange = self.tagdb.verify_arrangement(tagfile, \
                skipflag=config["database"]["skip_existing_arrangements"])

        if not arrange: return
        if config["database"]["sync_to_library"]: arrange.apply(tagfile);

    def synchronize_composer(self, tagfile, **kwargs):
        """ Synchronize the tags database fields to the given file fields
        """

        # must first assume the file is missing COMPOSER, and bootstrap from there
        if not "COMPOSER" in tagfile.tags.keys():
            # print the fields for context
            cutil.pretty_dict(tagfile.tags)

            # attempt to use last_composer (speeds up when adding new album)
            if not input("Accept last input: {} ? [CR]".format(self.last_composer)):
                cname = self.last_composer
            else:
                cname = input("Enter composer name: ")
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
        tagfile.tags["COMPOSER_NATIONALITY"] = composer["nationality"]

        # ensure the files are sync'd to database
        self.write2tagfile(tagfile)

    def get_artist_counts(self, tagfile, **kwargs):
        """ count/record artist occurences (to use as ranking) """
        aset = tagutil.get_artist_tagset(tagfile)
        for aname in aset:
            artistname = self.tagdb.match_from_perms(aname)
            if artistname in self.instrument_groupings.keys():
                self.instrument_groupings[artistname] += 1
            else:
                self.instrument_groupings[artistname] = 1

    def get_arrangement_set(self, tagfile, **kwargs):
        """ instrumental groupings via artist db """
        sar = self.tagdb.get_sorted_arrangement(tagfile).values()

        found = False
        for key, val in self.instrument_groupings.items():
            if sar == key:
                found = True
                self.instrument_groupings[key] += 1

        if not found: self.instrument_groupings[sar] = 1

def after_action_review(count):
    cutil.printr("AAR: file/folder count, track/album deltas")
    cutil.pretty_dict(count)
