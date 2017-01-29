#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
import json
from collections import OrderedDict

# external
from nltk import distance

# external
import taglib

def walker(root, func, **kwargs):
    """ iterate over every audio file under the target directory
        pass the tagfile and apply action to each
    """

    for folder, _, files in walk(root, topdown=False):
        if not files: continue

        print("walked into {}...".format(folder.replace(config["path"]["library"], "$LIBRARY")))
        [func(taglib.File(join(folder, name)), **kwargs) for name in files if util.is_audio_file(name)]

class StructuredQuery():
    def __init__(self, querystr):
        self.query = querystr
        self.keys = [key for key in self.query if key in config["playlist"]["tag_keys"]]
        relations = [key for key in self.query if key in config["playlist"]["relations"]]
        self.operators = [key for key in self.query if key in config["playlist"]["operators"]]
        self.tag_vals = [key for key in self.query if \
                key not in self.keys and \
                key not in relations and \
                key not in self.operators]

        self.filters = [{self.keys[i]: self.tag_vals[i], "rel": relations[i]} for i in range(len(self.operators) + 1)]
        if not self.operators: self.operators.append("AND")

    def __repr__(self): return str(["{}".format(filt) for filt in self.filters])

class TagDatabase:
    """ a class for interfacing with a music library's tag database """
    def __init__(self):
        self.path = util.config["path"]["database"]
        self.load()
        self.arange = Arrangement()

    def dump(self):
        """ dump """
        with open(self.path, "w") as f: json.dump(self._db, f, ensure_ascii=False, indent=4)

    def load(self):
        with open(self.path, "r") as f: self._db = json.load(f)

        self.artist = self._db["artist"]
        self.composer = self._db["composer"]
        self.exceptions = self._db["exceptions"]
        self.update_sets()

    def refresh(self):
        self.dump();
        self.load()

    def match_from_perms(self, name, category="artist"):
        for key, val in self._db[category].items():
            if name in val["permutations"]:
                return key

    def closest_from_existing_set(self, qname, category="artist"):
        """ find closest match and rerun"""
        min_score = 100
        for sname in self.sets[category]:
            score = distance.edit_distance(qname, sname)
            if score < min_score:
                min_score = score
                mname = sname

        return mname

    def add_new_perm(self, key, qname, category="artist"):
        """ add a new artist/composer permutation to the item's permutation list """
        print("Adding to permutations and updating db...")
        # update
        self._db[category][key]["permutations"].append(qname)
        self.refresh()

    def add_item_to_db(self, item, category="artist"):
        """ executive for mapping a new artist/composer into the database, including calls
        to functions which attempt to automate the process and fall back on manual methods.  """

        print("Searching for information on %s..." % (item))

        page = taghelpers.wiki_query(item)

        if page:
            new = taghelpers.item_fields_from_wiki(item, page, self.sets, category=category)
        else:
            if category == "artist": new = taghelpers.artist_fields_from_manual(item)

        print("proposed item for database:")
        [print("\t{}: {}".format(key, val)) for key, val in new.items()]

        if not input("Accept? [y]/n: "):
            return new
        else:
            raise TagDatabaseError("add_item_to_db: proposed item rejected")

    def update_sets(self):
        art_set = util.perms2set(self.artist)

        # update nationalities
        alist = [self.artist[aname]["nationality"] for aname in self.artist.keys()]
        clist = [self.composer[cname]["nationality"] for cname in self.composer.keys()]
        alist.extend(clist)
        nat_set = util.messylist2set(alist)

        # update composer set
        comp_set = util.perms2set(self.composer)

        # instrument set
        alist = [self.artist[artist]["instrument"] for artist in self.artist.keys()]
        inst_set = util.messylist2set(alist)

        # compile and write to disk
        self.sets = {"artist": art_set, "composer": comp_set, "nationality": nat_set, "instrument": inst_set}
        self._db['sets'] = {key: list(val) for key, val in self.sets.items()}

    def verify_arrangement(self, tagfile, skipflag=False):
        """ Arrangements are used as a hook to synchronize artist entries in the database with
            files in the library.  """

        if "ARRANGEMENT" in tagfile.tags and skipflag: return
        if "COMPILATION" not in tagfile.tags: tagfile.tags["COMPILATION"] = ["0"]
        if tagfile.tags["COMPILATION"][0] == "1": return

        sar = self.get_sorted_arrangement(tagfile)
        if len(sar) == 0: return

        self.arange.update(sar, tagfile)
        return self.arange

    def verify_composer(self, qname):
        if isinstance(qname, list): qname = qname[0]

        if qname in self.sets["composer"]:
            return self.match_from_perms(qname, category="composer")

        # try to find an existing match
        mname = self.closest_from_existing_set(qname, category="composer")

        if not input("Given: {}\tClosest Match: {}. Accept? [<CR>]/n: ".format(qname, mname)):
            # fetch actual key and update perms
            key = self.match_from_perms(mname, category="composer")
            self.add_new_perm(key, qname, category="composer")
            return key

        if not input("Add new composer? [<CR>]/n: "):
            self.composer[qname] = self.add_item_to_db(qname, category="composer")
            self.refresh()
            return qname

        if not input("Manually enter key lookup? [<CR>]/n: "):
            key = input("aight, go 'head: ")
            self.add_new_perm(key, qname, category="composer")
            return self.match_from_perms(mname, category="composer")

    def verify_artist(self, qname):
        """ verify that the artist query name (qname) has an entry in the tag database
            if it doesn't, propose a series of steps to remedy.  """

        if qname in self._db["exceptions"]["artists_to_ignore"]: return []

        if qname in self.sets["artist"]: return self.match_from_perms(qname)

        # try to find an existing match
        mname = self.closest_from_existing_set(qname, category="artist")

        if not input("Accept %s as matching %s? " % (mname, qname)):
            # fetch actual key and update perms
            key = self.match_from_perms(mname)
            self.add_new_perm(key, qname)
            return key

        if not input("Add new artist? [<CR>]/n: "):
            self.artist[qname] = self.add_item_to_db(qname)
            self.artist[qname]["count"] = 1; # needs an initial value
            self.refresh();
            return qname

        if not input("Is Composer Permutation? [<CR>]/n: "):
            cname = self.closest_from_existing_set(qname, category="composer")

            if not input("Accept %s as matching %s? " % (cname, qname)):
                ckey = self.match_from_perms(cname, category="composer")
            else:
                ckey = input("Manually enter composer key lookup... ")

            self.add_new_perm(ckey, qname, category="composer")
            return

        if not input("Manually enter key lookup? [<CR>]/n: "):
            key = input("aight, go 'head: ")
            self.add_new_perm(key, qname)
            return self.match_from_perms(qname)

        if not input("Add new artist? [<CR>]/n: "):
            self.artist[qname] = self.add_item_to_db(qname)
            self.refresh()
            return qname

        if not input("debug? [<CR>]/n: "):
            import pdb; pdb.set_trace()

        else:
            self._db["exceptions"]["artists_to_ignore"].append(qname)
            self.refresh()
            return

    def get_sorted_arrangement(self, tagfile):
        aset = get_artist_tagset(tagfile)
        sar = {}
        for aname in aset:
            akey = self.match_from_perms(aname)
            if akey != None:
                sar[akey] = (self.artist[akey]["instrument"], self.artist[akey]["count"])

        sar = OrderedDict(sorted(sar.items(), key=lambda t: t[1][1], reverse=True))
        return sar

class Arrangement:
    def __init__(self):
        self.album_name = ""
        self.flag = False
        self.prima = 0
        self.arrangement = ""
        self.sar = ""
        self.trackc = 1
        self.artist = ""
        self.albumartist = ""

    def update(self, sar, tagfile):
        self.sar = sar

        if self.is_changed(tagfile, sar):
            self.flag = False
            self.album_name = tagfile.tags["ALBUM"]

            if len(self.sar.keys()) == 1:
                self.prima = 0
            else:
                print("ranking arrangement:\n{}\n\ttitle: {}\t\nalbum: {}\t\n".format(
                    self.sar, tagfile.tags["TITLE"], tagfile.tags["ALBUM"]))

                response = input("[#]ordering, [s]kip, ... ? ")
                try:
                    self.prima = int(response)
                except:
                    self.flag = True
                    return

        self.unpack()

    def apply(self, tagfile):
        if not self.flag:
            tagfile.tags["ARRANGEMENT"] = self.arrangement
            tagfile.tags["ALBUMARTIST"] = self.albumartist
            tagfile.tags["ARTIST"] = self.artist
            tagfile.tags = {key: val for key, val in tagfile.tags.items() if key not in util.config["prune_artist_tags"]}
            util.commit_to_tagfile(tagfile)

    def is_changed(self, tagfile, sar):
        return tagfile.tags["ALBUM"] != self.album_name or str(self.sar) != str(sar)

    def unpack(self):
        alist = [item for item in self.sar.keys()]
        self.albumartist = str(alist[self.prima])
        self.artist = messylist2tagstr(alist)
        self.arrangement = messylist2tagstr([item[0] for item in self.sar.values()])

class TagDatabaseError(Exception):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

