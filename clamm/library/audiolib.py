#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
import sys
import re
from os import walk
from os.path import join
import os

# local
from clamm.library import tags, util
config = util.config
from clamm.tags import walker

persist_composer = ""

class AudioLib():
    """ external interface to audiolib module
    """
    def __init__(self, args):
        import pdb; pdb.set_trace()
        self.root = args.dir
        self.ltfa = LibTagFileAction(args)
        return self

    def synchronize(self):
        """ special hook for ensuring the tag database and the library file tags are sync'd
        """
        walker(self.root, self.ltfa.synchronize_composer)
        walker(self.root, self.ltfa.synchronize_artist)

    def initialize(self):
        """ special hook for consuming new music into library"""
        walker(self.root, self.ltfa.audio2preferred_format)
        walker(self.root, self.ltfa.synchronize_composer)
        walker(self.root, self.ltfa.prune_artist_tags)
        walker(self.root, self.ltfa.remove_junk_tags)
        walker(self.root, self.ltfa.handle_composer_as_artist)
        walker(self.root, self.ltfa.synchronize_artist)

class LibTagFile():
    def __init__(self, args):
        """ super class for tagfile action classes """

        # arg unpack
        self.args = args
        self.tagdb = tags.TagDatabase()
        self.action = self.args.sub_cmd
        self.tagdb.update_sets()

class LibTagFileAction(LibTagFile):
    def __init__(self, args):
        """
        LibTagFileAction is a collection of library tagfile action methods

        each action method should follow a methodical implementation
            1. each recieves a tagfile as an input
            2. each has access to argparser tui args and must use consistent Namespace references
            3. each has the option/necessity to create a persistent result
            4. each should define a follow-up action upon completion of tags.walker
        """

        LibTagFile.__init__(self, args)

        # wrap methods in dictionary for dynamic access
        self.func = {}
        for attr in dir(self):
            fobject = eval('self.{}'.format(attr))
            if hasattr(fobject, '__func__'):
                self.func[attr] = fobject

    def audio2preferred_format(self, tagfile, **kwargs):
        """ using ffmpeg, convert arbitrary audio file to preferred_type, flac by default

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
            util.log_missing_tag("COMPILATION", tagfile)

        if sq.operators[0] == "AND":
            include = True
            for i, filt in enumerate(sq.filters):
                key = sq.keys[i]
                try:
                    if filt[key] not in tags[key]: include = False
                except KeyError:
                    include = False
                    util.log_missing_tag(key, tagfile)

        elif sq.operators[0] == "OR":
            include = False

            for i, filt in enumerate(sq.filters):
                key = sq.keys[i]
                if filt[key] in tags[key]: include = True

        if include: self.playlist.append(tagfile.path)

    def show_tag_usage(self, tagfile, **kwargs):
        """Find (and print) all values (usages) of the input tag field.
        $ ./library.py show_tag_usage TCM
        """
        self.found_tags.extend([val for key, val in tagfile.tags.items() if key == self.tag_key])

    def get_tag_sets(self, tagfile, **kwargs):
        """Find (and print) all occurences of tag fields that contain the input string.
        $ ./library.py get_tag_sets ASIN
        """
        self.found_tags.extend([key.upper() for key, val in tagfile.tags.items() if key.find(self.tag_key) > -1])

    def prune_artist_tags(self, tagfile, **kwargs):
        tags = tagfile.tags

        # make sure we have at least the basics
        if not set(config["library"]["tags"]["keep_artist"]).intersection(set(tags)): return

        # apply deletion
        tagfile.tags = {key: val for key, val in tags.items() \
                if key not in config["library"]["tags"]["prune_artist"]}

        # write to file
        util.commit_to_tagfile(tagfile)

    def remove_junk_tags(self, tagfile, **kwargs):
        tags = tagfile.tags

        # apply deletion
        tagfile.tags = {key: val for key, val in tags.items() \
                if key not in config["library"]["tags"]["junk"]}

        # write to file
        util.commit_to_tagfile(tagfile)

    def delete_tag_by_name(self, tagfile, **kwargs):
        """Remove (with optional safety check) all occurences of input tag from library
        $ ./library.py /path/containing/unwanted/tracks delete_tag_by_name -t ASIN
        """
        untag = self.tag_key
        is_globber = '*' in untag
        tags = tagfile.tags

        if untag not in tags and not is_globber: return

        # apply deletion
        if is_globber:
            untag = self.tag_key.replace("*", "")
            tagfile.tags = {key: val for key, val in tags.items() if untag not in key}
        else:
            tagfile.tags = {key: val for key, val in tags.items() if key != untag}

        util.commit_to_tagfile(tagfile)

    def change_tag_by_name(self, tagfile, **kwargs):
        """
        manually update a single tag field
        $ ./library.py /path/containing/target/tracks change_tag_by_name -t ARTIST -v "Bob Hope"
        """

        curkey = self.tag_key
        if not curkey in tagfile.tags.keys(): curval = ""
        else: curval = tagfile.tags[curkey]

        # get the new tag value (input arg or manual)
        if self.tag_val:
            new_val = self.tag_val
        else:
            new_val = input("Changing {} tag...\n\tCurrent Value: {}\n\tEnter new: ".format(curkey, curval))

        tagfile.tags[curkey] = new_val

        # commit the change to the file
        util.commit_to_tagfile(tagfile)

    def handle_composer_as_artist(self, tagfile, **kwargs):
        """
        test for and handle composer in artist fields
        $ ./library.py /path/containing/target/tracks handle_composer_as_artist
        """

        # existence test
        aset = util.get_artist_tagset(tagfile)
        acom = aset.intersection(self.tagdb.sets["composer"])

        # null hyp action
        if not acom: return

        # detection action (check each ARTIST field and diff where found)
        for key, val, in tagfile.tags.items():
            if key.find("ARTIST") > -1:
                atags = re.split(util.SPLIT_REGEX, ', '.join(val))
                aset = set([val.strip() for val in atags])
                if aset.difference(acom):
                    tagfile.tags[key] = util.messylist2tagstr(list(aset.difference(acom)))
                else:
                    tagfile.tags[key] = input('Enter name: ')

        util.commit_to_tagfile(tagfile)

    def synchronize_artist(self, tagfile, **kwargs):
        """
            Verify there is an artist entry in tags.json for each artist found in tagfile.
            Find arrangement that is best fit for a given file.
            Sync files to library.
        """
        [self.tagdb.verify_artist(name) for name in util.get_artist_tagset(tagfile)]
        arrange = self.tagdb.verify_arrangement(tagfile, \
                skipflag=config["database"]["skip_existing_arrangements"])

        if not arrange: return
        if config["database"]["sync_to_library"]: arrange.apply(tagfile);

    def synchronize_composer(self, tagfile, **kwargs):
        """
            Synchronize the tags database fields to the given file fields
        """
        global persist_composer
        if not "COMPOSER" in tagfile.tags.keys():
            util.pretty_dict(tagfile.tags.items())
            if not input("Accept last input: {} ? [CR]".format(persist_composer)):
                cname = persist_composer
            else:
                cname = input("Enter composer name: ")
        else:
            cname = tagfile.tags["COMPOSER"]

        persist_composer = cname
        ckey = self.tagdb.verify_composer(cname)
        citem = self.tagdb.composer[ckey]

        if config["database"]["sync_to_library"]:
            # sync the values and commit to file
            util.commit_on_delta(tagfile, "COMPOSER", citem["full_name"])
            util.commit_on_delta(tagfile, "COMPOSER_ABBREVIATED", citem["abbreviated"])
            util.commit_on_delta(tagfile, "COMPOSER_DATE", citem["borndied"])
            util.commit_on_delta(tagfile, "COMPOSER_PERIOD", citem["period"])
            util.commit_on_delta(tagfile, "COMPOSER_SORT", citem["sort"])

    def find_multi_instrumentalists(self, tagfile, **kwargs):
        """ find/inspect input artists who have > 1 instrument fields """
        aset = util.get_artist_tagset(tagfile)
        for aname in aset:
            artistname = self.tagdb.match_from_perms(aname)
            if artistname == self.tag_key:
                util.pretty_dict(tagfile.tags.items())
                sys.exit()

    def get_artist_counts(self, tagfile, **kwargs):
        """ count/record artist occurences (to use as ranking) """
        aset = util.get_artist_tagset(tagfile)
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

class LibTagFileFollowUp(LibTagFile):
    def __init__(self, args):
        """ collection of library tagfile follow-up methods """

        LibTagFile.__init__(self, args)

        # persistent containers to hold results over a libwalk
        self.found_tags = []
        self.instrument_groupings = {}
        self.playlist = []

        # define follow-up actions
        if util.COUNT > 0: print("\n{} tagfiles updated.".format(util.COUNT))

        # wrap action methods in dictionary for programmatic lookup
        self.func = {}
        for attr in dir(self):
            fobject = eval('self.{}'.format(attr))
            if hasattr(fobject, '__func__'):
                self.func[attr] = fobject

    def audio2preferred_format(self, tagfile, **kwargs):
        pass

    def playlist(self, tagfile, **kwargs):
        pass

    def show_tag_usage(self, tagfile, **kwargs):
        pass

    def get_tag_sets(self, tagfile, **kwargs):
        pass

    def prune_artist_tags(self, tagfile, **kwargs):
        pass

    def remove_junk_tags(self, tagfile, **kwargs):
        pass

    def delete_tag_by_name(self, tagfile, **kwargs):
        pass

    def change_tag_by_name(self, tagfile, **kwargs):
        pass

    def handle_composer_as_artist(self, tagfile, **kwargs):
        pass

    def synchronize_artist(self, tagfile, **kwargs):
        pass

    def synchronize_composer(self, tagfile, **kwargs):
        pass

    def find_multi_instrumentalists(self, tagfile, **kwargs):
        pass

    def get_artist_counts(self, tagfile, **kwargs):
        pass

    def get_arrangement_set(self, tagfile, **kwargs):
        pass

