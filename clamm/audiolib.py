""" an interface to a classical music audio library.
"""

import re
import os
from os.path import join
import sys
import time
import subprocess

from colorama import Fore

from clamm import config
from clamm import tags
from clamm import util


class AudioLib():
    """ external interface to audiolib module
    """

    def __init__(self, args):
        self.args = args
        self.root = self.args.dir
        self.func = self.args.sub_cmd
        self.ltfa = LibTagFileAction(self.args)

    def walker(self, func, **kwargs):
        """
        Recursively walks the directories/sub-directories under
        :py:attr:`~root` and applies specified function to each audio
        file encountered.

        Parameters
        ----------
        func: function
            action to apply to audio files.
        """
        util.printr("walking with %s..." % (str(func)))

        for folder, _, files in os.walk(self.root, topdown=False):
            if not files:
                continue

            if config["verbosity"] > 2:
                util.printr("walked into {}...".format(
                    folder.replace(config["path"]["library"], "$LIBRARY")))
            else:
                util.printr(lambda: [
                    sys.stdout.write(Fore.GREEN + "." + Fore.WHITE),
                    sys.stdout.flush()])

            self.ltfa.count["album"] += 1

            for name in files:
                if not util.is_audio_file(name):
                    continue
                self.ltfa.count["file"] += 1
                func(tags.SafeTagFile(join(folder, name)), **kwargs)

        # initiate post-walk follow_up
        self.follow_up()

    def follow_up(self, **kwargs):
        """ follow up """
        after_action_review(self.ltfa.count)

        if self.func == "playlist":
            pass

        elif self.func == "recently_added":
            # now, write the accumulated list to a simple pls file format
            pl_name = "recently-added-{}".format(time.ctime()[:10])
            pl_path = os.path.join(config["path"]["playlist"], pl_name)
            with open(pl_path, mode="w") as playlist_file:
                [playlist_file.write("{}\n".format(track))
                 for track in self.ltfa.the_playlist]

            # finally, tell cmus to add the playlist to its catalog
            subprocess.call([
                "cmus-remote", config["opt"]["cmus-remote"],
                "pl-import " + pl_path])

        elif self.func == "get_artist_counts":
            for key, val in self.ltfa.artist_count.items():
                self.ltfa.tagdb.artist[key]["count"] = val

            self.ltfa.tagdb.refresh()

    def synchronize(self):
        """
        synchronize the audiofile's composer/artist/arrangement tags
        with the tag database
        """

        self.walker(self.ltfa.synchronize_composer)
        self.walker(self.ltfa.synchronize_artist)
        self.walker(self.ltfa.synchronize_arrangement)

    def initialize(self):
        """
        initialize a new music library of audiofiles
        """

        self.walker(self.ltfa.audio2preferred_format)
        self.walker(self.ltfa.synchronize_composer)
        self.walker(self.ltfa.prune_artist_tags)
        self.walker(self.ltfa.remove_junk_tags)
        self.walker(self.ltfa.handle_composer_as_artist)
        self.walker(self.ltfa.synchronize_artist)


class LibTagFile():
    """
    super class for LibTagFileAction

    Attributes
    ----------
    args: Namespace
        command line arguments, forwarded from clamm.

    """

    def __init__(self, args):
        # arg unpack
        self.args = args
        self.tagdb = tags.TagDatabase()
        self.action = self.args.sub_cmd
        self.tagdb.update_sets()

        # stats
        self.count = {"tag": 0, "track": 0, "album": 0, "file": 0}

    def write2tagfile(self, tagfile):
        """ write2tagfile """
        (atrack, atag) = util.commit_to_libfile(tagfile)
        self.count["track"] += atrack
        self.count["tag"] += atag


class LibTagFileAction(LibTagFile):
    """ LibTagFileAction """

    def __init__(self, args):
        """a collection of library tag file _action_ methods.

        Each action method follows a structure:
            1. recieves a tagfile as an input
            2. has access to argparser cli args and must use consistent
               Namespace references
            3. has the option to create a persistent result
            4. has the option define a follow-up action upon completion of
               walker
        """

        LibTagFile.__init__(self, args)

        # helper attrs
        self.the_playlist = []         # persistent storage for playlist
        self.last_composer = ""     # persistent storage for last composer
        self.artist_count = {}      # persistent storage for count of artist

        self.instrument_groupings = {}

        # auto_suggest
        self.artist_suggest = tags.Suggestor(self.tagdb, category="artist")

        self.composer_suggest = tags.Suggestor(self.tagdb, category="composer")

        # wrap methods in dictionary for dynamic access
        self.func = {}
        for attr in dir(self):
            fobject = eval('self.{}'.format(attr))
            if hasattr(fobject, '__func__'):
                self.func[attr] = fobject

    def audio2preferred_format(self, tagfile, **kwargs):
        """
        using ``ffmpeg``, convert arbitrary audio file to a
        preferred type, ``flac`` by default
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
            subprocess.Popen(
                ["ffmpeg", config["opt"]["ffmpeg"],
                 "-i", src, dst], stdout=redirect)

    def recently_added(self, tagfile, **kwargs):
        """generate a recently added playlist by looking at the
        date of the parent directory.
        """
        parent = os.path.split(tagfile.path)[0]
        age_in_days = (time.time() - os.stat(parent).st_ctime) / \
            util.SEC_PER_DAY
        if age_in_days < config["library"]["recently_added_day_age"]:
            self.the_playlist.append(tagfile.path)

    def make_playlist(self, tagfile, **kwargs):
        """ playlist filter
        """

        # unpack
        ftags = tagfile.tags
        query = kwargs["query"]

        try:
            if ftags["COMPILATION"][0] == "1":
                return
        except KeyError:
            tags.log_missing_tag("COMPILATION", tagfile)

        if query.operators[0] == "AND":
            include = True
            for i, filt in enumerate(query.filters):
                key = query.keys[i]
                try:
                    if filt[key] not in ftags[key]:
                        include = False
                except KeyError:
                    include = False
                    tags.log_missing_tag(key, tagfile)

        elif query.operators[0] == "OR":
            include = False

            for i, filt in enumerate(query.filters):
                key = query.keys[i]
                if filt[key] in ftags[key]:
                    include = True

        if include:
            self.the_playlist.append(tagfile.path)

    def prune_artist_tags(self, tagfile, **kwargs):
        """Conform artist/albumartist tag key names by applying
        config['library']['tags']['prune_artist'] rules

        Example
            ALBUMARTIST instead of ALBUM_ARTIST
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
        """similar to prune_artist_tags, but removes all tags that
        are in ``config["library"]["tags"]["junk"]``
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
        """Unlike ``remove_junk_tags``, allows removing as glob of
        similarly named tags, as in the MUSICBRAINZ_* tags, without
        cluttering  ``config["library"]["tags"]["junk"]`` with
        excessive entries.
        """

        untag = self.args.key
        ftags = tagfile.tags

        # apply deletion
        tagfile.tags = {k: v for k, v in ftags.items() if untag not in untag}

        # write to file
        self.write2tagfile(tagfile)

    def change_tag_by_name(self, tagfile, **kwargs):
        """
        globally change a single tag field, applied to a directory
        or library.

        Examples
        --------
            $ clamm library -d ~/path/to/album/ action \
                    --change_tag_by_name -k ALBUMARTIST -v 'Richard Egarr'

        """
        # apply the change
        tagfile.tags[self.args.key] = [self.args.val]

        # write to file
        self.write2tagfile(tagfile)

    def handle_composer_as_artist(self, tagfile, **kwargs):
        """test for and handle composer in artist fields.

        Background
            Many taggers/publishers deal with classical music tags by
            lumping the composer in with the artist, as in
            ``ARTIST=JS Bach; Glenn Gould``
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
                atags = re.split(util.SPLIT_REGEX, ', '.join(val))
                aset = set([val.strip() for val in atags])
                if aset.difference(acom):
                    tagfile.tags[key] = tags.messylist2tagstr(
                        list(aset.difference(acom)))
                else:
                    tagfile.tags[key] = raw_input('Enter artist name: ')

        # write to file
        self.write2tagfile(tagfile)

    def synchronize_arrangement(self, tagfile, **kwargs):
        """Find arrangement that is best fit for a given file.
        """

        aset = tags.get_artist_tagset(tagfile)

        # arrangement, defined as the pairing of artist to instrument
        arrange = self.tagdb.verify_arrangement(
            aset,
            tagfile,
            skipflag=config["database"]["skip_existing_arrangements"])

        if not arrange:
            return

        arrange.apply(tagfile)

    def synchronize_artist(self, tagfile, **kwargs):
        """Verify there is an artist entry in ``tags.json`` for each
        artist found in audiofile.
        Will not update ARTIST/ALBUMARTIST until arrangement is verified
        """

        for name in tags.get_artist_tagset(tagfile):
            self.tagdb.verify_artist(name, tagfile)

    def synchronize_composer(self, tagfile, **kwargs):
        """Verify there is a corresponding entry in ``tags.json`` for
        the composer found in the audiofile.

        If an entry is not found, prompt to add a new composer.
        """

        # must first assume the file is missing COMPOSER
        # and bootstrap from there
        if "COMPOSER" not in tagfile.tags.keys():
            # print the fields for context
            util.pretty_dict(tagfile.tags)

            # attempt to use last_composer (speeds up when adding new album)
            fmt = "Accept last input: {}? [CR] ".format(self.last_composer)
            if not raw_input(fmt):
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
        tagfile.tags["COMPOSER"] = [ckey]
        tagfile.tags["COMPOSER_ABBREVIATED"] = [composer["abbreviated"]]
        tagfile.tags["COMPOSER_DATE"] = [composer["borndied"]]
        tagfile.tags["COMPOSER_PERIOD"] = [composer["period"]]
        tagfile.tags["COMPOSER_SORT"] = [composer["sort"]]
        tagfile.tags["COMPOSER_NATION"] = [composer["nationality"]]

        # ensure the files are sync'd to database
        self.write2tagfile(tagfile)

    def get_artist_counts(self, tagfile, **kwargs):
        """count/record artist occurences (to use as ranking)
        """

        aset = tags.get_artist_tagset(tagfile)

        for aname in aset:
            artistname = self.tagdb.match_from_perms(aname)
            if artistname is None:
                continue
            if artistname in self.artist_count.keys():
                self.artist_count[artistname] += 1
            else:
                self.artist_count[artistname] = 1

    def get_arrangement_set(self, tagfile, **kwargs):
        """get set and count of instrumental groupings via sorted
        arrangements
        """

        # returns arrangement sorted by artist count
        sar = self.tagdb.get_sorted_arrangement(tagfile).values()

        # init/increment arrangement
        found = False
        for key, _ in self.instrument_groupings.items():
            if sar == key:
                found = True
                self.instrument_groupings[key] += 1

        if not found:
            self.instrument_groupings[sar] = 1


def after_action_review(count):
    """ after_action_review """
    util.printr(
        "\n%15s: %5d %10s: %5d\n%15s: %5d %10s: %5d"
        % ("changed tags", count["tag"],
           "tracks", count["track"], "counted folder",
           count["album"], "files", count["file"]))
