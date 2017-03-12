# -*- coding: utf-8 -*-
# __author__ Paul Adams

""" the tags module contains classes and functions that create an
interface to the clamm's tag database.
"""

# built-ins
from __future__ import unicode_literals, print_function
import json
from collections import OrderedDict
import copy
from subprocess import call
import re

# external
from translate import Translator
import prompt_toolkit as ptk
from nltk import distance
import taglib
import wikipedia
import nltk

# local
import audiolib
import clamm
from config import config

# globals, constants
artist_tag_names = ["ALBUMARTIST_CREDIT",
                    "ALBUM ARTIST",
                    "ARTIST",
                    "ARTIST_CREDIT",
                    "ALBUMARTIST"]
tk = nltk.tokenize.WordPunctTokenizer()


class SafeTagFile(taglib.File):
    """ Allow for consistent file tagging.

    Subclasses ``taglib.File`` and creates a deep copy of a
    ``taglib.File`` objects

    Parameters
    ----------
    filepath: str
        the absolute file path to the audio file.

    Attributes
    ----------
    tag_copy: taglib.File
        a copy that allows for before/after comparison.

    """
    def __init__(self, filepath):
        taglib.File.__init__(self, filepath)
        self.tag_copy = copy.deepcopy(self.tags)


class StructuredQuery():
    def __init__(self, querystr):
        self.query = querystr
        self.keys = [key for key in self.query
                     if key in config["playlist"]["tag_keys"]]
        relations = [key for key in self.query
                     if key in config["playlist"]["relations"]]
        self.operators = [key for key in self.query
                          if key in config["playlist"]["operators"]]
        self.tag_vals = [key for key in self.query if
                         key not in self.keys and
                         key not in relations and
                         key not in self.operators]

        self.filters = [{self.keys[i]: self.tag_vals[i], "rel": relations[i]}
                        for i in range(len(self.operators) + 1)]
        if not self.operators:
            self.operators.append("AND")

    def __repr__(self):
        return str(["{}".format(filt) for filt in self.filters])


class Suggestor():
    """ Auto-suggestion support

    Implements ``prompt_toolkit.auto_suggest.AutoSuggestFromHistory``
    by populating history with a list of items from one of the tag
    database sets.

    Parameters
    ----------
    tagdb: tags.TagDatabase
        provides access to the sets in ``tags.json``.

    category: str, optional
        Inidicate which set category to populate the history
        with, one of {artist, composer, instrument, nationality, period}.
        Default is *artist*.
    """
    def __init__(self, tagdb, category="artist"):
        self.history = ptk.history.InMemoryHistory()
        for item in tagdb.sets[category]:
            self.history.append(item)

    def prompt(self, pmsg):
        r = ptk.prompt(
                pmsg,
                history=self.history,
                auto_suggest=ptk.auto_suggest.AutoSuggestFromHistory(),
                enable_history_search=True,
                on_abort=ptk.interface.AbortAction.RETRY)
        return r


class TagDatabase:
    """
    Primary object for interaction with the library tag database.

    Manages ``tags.json``, including adding new artists/composers.

    Attributes
    ----------
    path: str
        path to ``tags.json`` file, set via ``config["path"]["database"]``

    arange: Arrangement
        Arrangement instance used for verifying track instrumental
        arrangement.

    new_item: dict
        container for new item to be added to database. _item_ can be one of
        {artist, composer, arrangement}
    """

    def __init__(self):
        self.path = config["path"]["database"]
        self.load()
        self.arange = Arrangement()
        self.new_item = {}

        # auto_suggest
        self.suggest = {
                "artist": Suggestor(self, category="artist"),
                "composer": Suggestor(self, category="composer"),
                "period": Suggestor(self, category="period"),
                "instrument": Suggestor(self, category="instrument"),
                "nationality": Suggestor(self, category="nationality")}

        self.update_sets()

    def dump(self):
        """ dump """
        with open(self.path, "w") as f:
            json.dump(self._db, f, ensure_ascii=False, indent=4)

    def load(self):
        with open(self.path, "r") as f:
            self._db = json.load(f)

        self.artist = self._db["artist"]
        self.composer = self._db["composer"]
        self.exceptions = self._db["exceptions"]
        self.sets = self._db["sets"]

    def refresh(self):
        self.dump()
        self.load()
        self.update_sets()

    def update_sets(self):
        """
        update the tag sets by scanning the database and compiling
        artist, nationality, composer, instrument, and period
        """

        # update artists
        artists = perms2set(self.artist)

        # update period
        clist = [self.composer[cname]["period"]
                 for cname in self.composer.keys()]
        periods = messylist2set(clist)

        # update nationalities
        for aname in self.artist.keys():
            if "instrument" not in self.artist[aname]:
                self.artist[aname]["instrument"] = "null"
            if "nationality" not in self.artist[aname]:
                self.artist[aname]["nationality"] = "null"
        alist = [self.artist[aname]["nationality"]
                 for aname in self.artist.keys()]
        clist = [self.composer[cname]["nationality"]
                 for cname in self.composer.keys()]
        alist.extend(clist)
        nationalities = messylist2set(alist)

        # update composer set
        composers = perms2set(self.composer)

        # instrument set
        ilist = [self.artist[artist]["instrument"]
                 for artist in self.artist.keys()]
        instruments = messylist2set(ilist)

        # compile and write to disk
        self.sets = {
                "period": periods,
                "artist": artists,
                "composer": composers,
                "nationality": nationalities,
                "instrument": instruments}
        self._db['sets'] = {key: list(val) for key, val in self.sets.items()}

    def match_from_perms(self, name, category="artist"):
        for key, val in self._db[category].items():
            if name in val["permutations"]:
                return key
        raise KeyNotFoundError(
                "No match from permutations for {}...".format(name))

    def add_new_perm(self, key, perm, category="artist"):
        """
        add a new name permutation to the item's permutation list
        """

        clamm.printr("Adding to permutations and updating db...")
        self._db[category][key]["permutations"].append(perm)
        self.refresh()

    def add_new_item(self, category="artist"):
        """
        inserts a new item into the tag db after prompting
        for approval
        """
        # on approval, add the new artist/composer to the database
        clamm.printr("proposed item for database:")
        clamm.pretty_dict(self.new_item)
        if not input("Accept? [y]/n: "):
            self._db[category][self.new_item["full_name"]] = self.new_item
            self.refresh()
        else:
            raise TagDatabaseError("get_new_item: proposed item rejected")

    def get_new_item(self, item, category="artist"):
        """
        resolves fields for a new item by attempting auto-population
        via `item_fields_from_wiki`, and falls back on
        `item_fields_from_manual`.
        returns the database key of the new item
        """

        clamm.printr("Searching for information on %s..." % (item))

        # attempt to match the item to a wiki entry
        page = wiki_query(item)

        if page:
            # if match is found, autotag with verification
            self.item_fields_from_wiki(item, page, category=category)
        else:
            # otherwise, fall back on manual entry
            self.item_fields_from_manual(item, category=category)

        # update the database
        self.add_new_item(category=category)

        # return the key (presumably still available in new_item)
        return self.new_item["full_name"]

    def item_fields_from_wiki(self, item, page, category="artist"):
        """
        auto-populate database tags a successful wikipedia query
        """

        new = {"permutations": [item]}
        print(page.summary)

        # NAME
        resp = input("Enter name (keep/[t]itle): ")

        if item != page.title:
            new["permutations"].append(page.title)

        new["full_name"] = page.title
        if resp == "k":
            new["full_name"] = item

        new["borndied"] = get_borndied(page.summary)
        new["nationality"] = self.get_field(
                page.summary, category="nationality")

        # category specific
        if category == "artist":
            new["count"] = 1    # initial value
            if input("[I]ndividual or Ensemble?"):
                new["ordinality"] = "Ensemble"
            else:
                new["ordinality"] = "Individual"

            new["instrument"] = self.get_field(
                    page.summary, category="instrument")

        else:
            new["period"] = self.suggest["period"].prompt(
                    "Enter composer period: ")
            new["sort"] = swap_first_last_name(new["full_name"])
            new["abbreviated"] = new["full_name"].split(" ")[1]

        # store the result
        self.new_item = new

    def item_fields_from_manual(self, item, category="artist"):
        """
        alternative to `item_fields_from_wiki` in case `wiki_query` is
        not successful.

        fetches new item fields manually with help from auto-suggestion
        """
        resp = input("Translate/skip/continue: t/s/[<cr>]")
        if resp:
            if resp == "t":
                item = get_translation(item)
            elif resp == "s":
                return

        call(['googler', '-n', '3', item])

        new = {"permutations": [item]}

        resp = input("Enter name ([k]eep): ")
        if not resp:
            new["full_name"] = item
        else:
            new["full_name"] = resp
            if item != resp:
                new["permutations"].append(resp)

        item = new["full_name"]

        if category == "artist":
            resp = input("[I]ndividual or Ensemble?")
            if resp:
                new["ordinality"] = "Ensemble"
            else:
                new["ordinality"] = "Individual"
            new["instrument"] = self.suggest["instrument"].prompt(
                    "Enter instrument: ")
        else:
            new["period"] = self.suggest["period"].prompt(
                    "Enter composer period: ")
            new["sort"] = swap_first_last_name(new["full_name"])
            new["abbreviated"] = new["full_name"].split(" ")[1]

        new["borndied"] = input("Enter dates: ")
        new["nationality"] = self.suggest["nationality"].prompt(
                "Enter nationality: ")

        # store the result
        self.new_item = new

    def verify_arrangement(self, artist_set, tagfile, skipflag=False):
        """
        Arrangements are used to synchronize artist entries
        in the database with files in the library.
        """

        if "ARRANGEMENT" in tagfile.tags and skipflag:
            return
        if "COMPILATION" not in tagfile.tags:
            tagfile.tags["COMPILATION"] = ["0"]
        # not interested in arrangements for compilations
        if tagfile.tags["COMPILATION"][0] == "1":
            return

        sar = self.get_sorted_arrangement(tagfile, artist_set=artist_set)
        # if len(sar) == 0:
        #     return
        self.arange.update(sar, tagfile)
        return self.arange

    def verify_composer(self, qname):
        """Verify the queried composer is in the database.

        Returns the tag database key given the query name found in
        the tag file by verifying the query name has a match in the
        tag database. If it doesn't, initiates ``tags.add_new_item``
        and then returns the key.

        Parameters
        ----------
        qname: str
            query name from audiofile tags

        Returns
        -------
        key: str
            Key to composer entry

        """

        if isinstance(qname, list):
            qname = qname[0]

        # easiest, the qname is known
        if qname in self.sets["composer"]:
            return self.match_from_perms(qname, category="composer")

        # otherwise, try to find an existing edit_distance match
        mname = get_nearest_name(qname, self.sets["composer"])
        response = input(
                "Given: {}\tClosest Match: {}. Accept? [<CR>]/n: "
                .format(qname, mname))

        # fetch actual key and update perms
        if not response:
            key = self.match_from_perms(mname, category="composer")
            self.add_new_perm(key, qname, category="composer")
            return key

        # fall back 1, `add_new_item` to tags
        if not input("Add new composer? [<CR>]/n: "):
            new_key = self.get_new_item(qname, category="composer")
            return new_key

        # fall back 2, enter key manully (assuming something has gone wrong)
        if not input("Manually enter key lookup? [<CR>]/n: "):
            key = self.suggest["composer"].prompt("aight, go 'head: ")
            self.add_new_perm(key, qname, category="composer")
            return self.match_from_perms(mname, category="composer")

    def verify_artist(self, qname):
        """Verify the queried artist is in the database.

        Returns the tag database key given the query name found in
        the tag file. If it doesn't, initiates ``tags.add_new_item``
        and then returns the key.

        Parameters
        ----------
        qname: str
            query name from audiofile tags

        Returns
        -------
        key: str
            Key to artist entry
        """

        # first, deal with the misfits by bailing out
        if qname in self._db["exceptions"]["artists_to_ignore"]:
            return []

        # if we already know this artist, job done
        if qname in self.sets["artist"]:
            key = self.match_from_perms(qname)
            return key

        # if above fails, possibly nearest neighbor is correct?
        nearest = get_nearest_name(qname, self.sets["artist"])

        if not input("Accept {} as matching {}? ".format(nearest, qname)):
            # fetch actual key and update perms
            key = self.match_from_perms(nearest)
            self.add_new_perm(key, qname)
            return key

        # Hook in the new artist process if reach this point
        if not input("Add new artist? [<CR>]/n: "):
            new_key = self.get_new_item(qname)
            return new_key

        # It's also possible that the artist is really a composer
        if not input("Is Composer Permutation? [<CR>]/n: "):
            cname = get_nearest_name(qname, self.sets["composer"])

            if not input("Accept %s as matching %s? " % (cname, qname)):
                ckey = self.match_from_perms(cname, category="composer")
            else:
                ckey = self.suggest["composer"].prompt(
                        "Manually enter composer key... ")

            self.add_new_perm(ckey, qname, category="composer")
            return []

        # Maybe there's an error in the database and we can enter
        # the key manually
        if not input("Manually enter artist key? [<CR>]/n: "):
            man_key = self.suggest["artist"].prompt("aight, go 'head: ")
            actual_key = self.match_from_perms(man_key)
            return actual_key

        # One more chance to add a new artist
        if not input("Add new artist? [<CR>]/n: "):
            new_key = self.get_new_item(qname)
            return new_key

        # Allow some introspection before dying
        if not input("debug? [<CR>]/n: "):
            import bpdb
            bpdb.set_trace()

        # Declare a misfit and walk away in disgust
        else:
            self._db["exceptions"]["artists_to_ignore"].append(qname)
            self.refresh()
            return []

    def get_sorted_arrangement(self, tagfile, artist_set=None):
        """Compile a sorted instrument/ARTIST arrangement.

        Order audiofile ARTIST tags by library frequency ranking.

        Parameters
        ----------
        tagfile: SafeTagFile
            taglib.File subclass containing audio file's tags
        artist_set: set
            Unique listing of ARTISTs associated with ``tagfile``.

        Returns
        -------
        sar: OrderedDict
            Arrangement sorted by ARTIST's library frequency.
        """
        if artist_set is not None:
            sar = {aname: (
                self.artist[aname]["instrument"],
                self.artist[aname]["count"]) for aname in artist_set}
        else:
            artist_set = get_artist_tagset(tagfile)
            sar = {}
            for aname in artist_set:
                akey = self.match_from_perms(aname)
                if akey is not None:
                    sar[akey] = (self.artist[akey]["instrument"],
                                 self.artist[akey]["count"])

        sar = OrderedDict(sorted(
            sar.items(), key=lambda t: t[1][1], reverse=True))
        return sar

    def get_field(self, summary, category="nationality"):
        """ Get a given category field from the Wikipedia summary.

        Guess the tag value by matching the category sets against the
        summary words. If guessing fails, fall back on manual entry
        with ``tags.Suggestor``.

        Parameters
        ----------
        tagfile: SafeTagFile
            ``taglib.File`` subclass containing audiofile's tags
        category: str, optional
            Indicates the type of field, on of {instrument,
            nationality, period}. Default is *nationality*.

        Returns
        -------
        result: str
            The value for the sought field.
        """
        known_set = self.sets[category]
        guess = [word for word in tk.tokenize(summary) if word in known_set]
        guess = list(set(guess))    # make sure entries are unique
        result = None

        while guess:
            g = guess.pop(0)
            resp = input("guessing, accept %s? [y]/n: " % (g))
            if not resp:
                result = g
                break

        if result is None:
            result = self.suggest[category].prompt(
                    "Enter {}: ".format(category))

        return result


class Arrangement:
    """ Manage the instrument/artist grouping for an audio file.

    Attributes
    ----------
    album: str
        Name of current album

    commit_flag: bool
        If ``False``, prevents arrangement from being written to file.

    prima: int
        Index into sorted artist list indicating which artist should be
        treated as ALBUM_ARTIST.

    arrangement: str
        current instrumental ARRANGMENT. If more than one ARTIST,
        list of instruments is semicolon delimited and order identical
        to ARTIST.

    sar: OrderedDict
        sorted arrangement compiled by ``tags.get_sorted_arrangement``

    trackc: int
        track count associated with current album.

    artist: str
        current ARTIST name. If more than one ARTIST, list is semicolon
        delimited.

    albumartist: str
        current ALBUM_ARTIST name
    """

    def __init__(self):
        self.album = ""
        self.commit_flag = False
        self.prima = 0
        self.arrangement = ""
        self.sar = ""  # sorted arrangement
        self.trackc = 1
        self.artist = ""
        self.albumartist = ""

    def update(self, sar, tagfile):
        """Conditionally update album/artist attributes.

        The default value for ``prima`` corresponds to the highest
        ranking (via ARTIST frequency count) ``artist``. This behavior
        can be changed via
        ``config["database"]["prompt_for_album_artist"]`` to prompt
        for a custom ordering.
        """
        self.sar = sar

        if self.is_changed(tagfile, sar):
            self.commit_flag = True
            self.album = tagfile.tags["ALBUM"]
            self.prima = 0  # default value

            if len(self.sar.keys()) > 1 and \
                    config["database"]["prompt_for_album_artist"]:

                clamm.printr("ranking arrangement:")
                print("\n\tarrangement: {}\n\ttitle: {}\n\talbum: {}"
                      .format(
                          self.sar,
                          tagfile.tags["TITLE"],
                          tagfile.tags["ALBUM"]))

                response = input("[#]ordering, [s]kip, ... ? ")

                if isinstance(eval(response), int):
                    self.prima = int(response)
                else:
                    clamm.printr(
                            "Unable to parse response, using default ordering")

        self.unpack()

    def apply(self, tagfile):
        if self.commit_flag:
            tagfile.tags["ARRANGEMENT"] = self.arrangement
            tagfile.tags["ALBUMARTIST"] = self.albumartist
            tagfile.tags["ARTIST"] = self.artist
            tagfile.tags = {key: val for key, val in tagfile.tags.items()
                            if key not in
                            config["library"]["tags"]["prune_artist"]}
            audiolib.commit_to_libfile(tagfile)

    def is_changed(self, tagfile, sar):
        """ Test if album or artist has changed.

        Returns
        -------
        is_changed: bool
            True if either ``tagfile`` or ``sar`` has changed.
        """

        is_diff_album = tagfile.tags["ALBUM"] != self.album
        is_delta_sar = str(self.sar) != str(sar)
        return is_diff_album or is_delta_sar

    def unpack(self):
        alist = [item for item in self.sar.keys()]
        self.albumartist = str(alist[self.prima])
        self.artist = messylist2tagstr(alist)
        messylist = [item[0] for item in self.sar.values()]
        self.arrangement = messylist2tagstr(messylist)


class KeyNotFoundError(Exception):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class TagDatabaseError(Exception):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


def get_borndied(summary):
    """ gets born/died dates

    Use a regexp to extract artist/composer date(s) from a wikipedia
    summary string. If regexp fails, fall back on user prompt.

    Parameters
    ----------
    summary: str
        the summary corresponding to a wikipedia query.

    Returns
    -------
    borndied: str
        Dates of subject birth and death. Example format is 1910-1990.
    """

    m = re.findall("\d{4}", summary)

    if len(m) >= 2:
        borndied = m[0] + "-" + m[1]
        if not input("Accept %s? [y]/n: " % (borndied)):
            return borndied

        else:
            borndied = m[0] + "-"
            if not input("Accept %s? [y]/n: " % (borndied)):
                return borndied

    elif len(m) >= 1:
        borndied = m[0] + "-"

        resp = input("Accept %s? [y]/n: " % (borndied))
        if not resp:
            return borndied

    else:
        return input("Enter Dates: ")


def wiki_query(search):
    """ Perform a Wikipedia search

    Fetches a result from wikipedia and prompts user to select correct
    page, if one exists.

    Parameters
    ----------
    search: str
        The query

    Returns
    -------
    if query is successful, returns a wikipedia.page object
    otherwise, returns None
    """

    # call out to wikipedia
    results = wikipedia.search(search)

    # print options
    clamm.printr("options: ")
    print("\t\t-3: Translate\n\t\t-2: New string\n\t\t-1: Die\n")

    # print query results
    clamm.printr("query returns: ")
    if results:
        for i, r in enumerate(results):
            print("\t\t{}: {}".format(i, r))

    # prompt action
    idx = input("Enter choice (default to 0):")

    # default, accept the first result
    if not idx:
        return wikipedia.page(results[0])

    # handle cases
    idx = int(idx)
    if (idx) >= 0:
        return wikipedia.page(results[idx])
    elif (idx) == -1:
        return []
    elif (idx) == -2:
        return wiki_query(input("Try a new search string: "))
    elif (idx) == -3:
        wiki_query(get_translation(search))
    else:
        return []


def get_translation(search):
    """Translate non-Latin characters

    occasionally artist name will be in non-Latin characters. Prompts
    the user to supply the *From* language.

    Parameters
    ----------
    search: str
        the search string

    Returns
    -------
    search string translated to Latin characters.
    """

    tr = Translator(input("Enter from language: "), 'en')
    return tr.translate(search)


def get_artist_tagset(tagfile):
    tags = tagfile.tags
    atags = {t: re.split(clamm.SPLIT_REGEX,
             ', '.join(tags[t])) for t in artist_tag_names
             if t in tags.keys()}
    aset = set([v.strip() for val in atags.values() for v in val])
    return aset


def get_nearest_name(qname, name_set):
    """return closest match by finding minimum
    ``nltk.distance.edit_distance``

    Parameters
    ----------
    qname: str
        query name against which seeking match

    name_set: set
        set of names of which qname is possible member

    Returns
    -------
    the element from ``name_set`` which minimizes distance to ``qname``.
    """
    min_score = 100
    for sname in name_set:
        score = distance.edit_distance(qname, sname)
        if score < min_score:
            min_score = score
            mname = sname

    return mname


def perms2set(D):
    clist = list(D.keys())
    blist = [D[c]["permutations"] for c in clist]
    # flatten
    blist = [item for sublist in blist for item in sublist]
    clist.extend(blist)
    cset = messylist2set(clist)
    return cset


def messylist2set(alist):
    """owing to laziness, these lists may contain gotchas
    """
    y = [item for item in alist if item.__class__ is str and len(item) > 0]
    return set(y)


def messylist2tagstr(alist):
    s, delim = "", "; "
    for i, item in enumerate(alist):
        if isinstance(item, list):
            item = item[0]
        if i == len(alist) - 1:
            delim = ""
        s += "{}{}".format(item, delim)

    return s


def swap_first_last_name(name_str):
    """ Toggle first/last name order

    Parameters
    ----------
    name_str (str)
        Name formatted as either "First Last" or "Last, First"

    Returns
    -------
    swapd (str)
        Name format toggled
    """

    comma_idx = name_str.find(",")
    name_parts = name_str.replace(",", "").split(" ")

    if comma_idx > -1:
        swapd = "{} {}".format(name_parts[1], name_parts[0])
    else:
        swapd = "{}, {}".format(name_parts[1], name_parts[0])

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
