#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
from subprocess import call
import re

# external
import itunespy
from nltk import distance
import wikipedia
from translate import Translator
import nltk

tk = nltk.tokenize.WordPunctTokenizer();

def get_translation(search_string):
    """ occasionally artist name will be in non-Latin characters """

    tr = Translator(input("Enter from language: "), 'en')
    return tr.translate(search_string)

def get_field(summary, known_set, name):
    guess = [word for word in tk.tokenize(summary) if word in known_set]
    guess = list(set(guess)) # make sure entries are unique

    if name == "nationality" and guess:
        g = guess.pop(0)
        resp = input("Accept %s? [y]/n: " % (g))
        while resp and guess:
            g = guess.pop(0)
            resp = input("Accept %s? [y]/n: " % (g))

        if not resp:
            return g

        else:
            return input("Enter %s: " % (name))

    else:
        resp = [g for g in guess if not input("Accept %s? [y]/n: " % (g))]

        if not resp:
            return input("Enter %s: " % (name))

        else:
            return resp

def get_borndied(summary):
    """ extract artist/composer vital date(s) from a wikipedia summary string """

    m = re.findall("\d{4}", summary)

    if len(m) >= 2:
        born = m[0] + "-" + m[1]
        if not input("Accept %s? [y]/n: " % (born)):
            return born

        else:
            born = m[0] +"-"
            if not input("Accept %s? [y]/n: " % (born)): return born

    elif len(m) >= 1:
        born = m[0] +"-"

        resp = input("Accept %s? [y]/n: " % (born))
        if not resp: return born

    else:
        return input("Enter Dates: ")

def item_fields_from_wiki(item, page, sets, category="artist"):
    """ extract database tags/fields from a successful wikipedia query """

    new = {"permutations": item}
    print(page.summary)

    # NAME
    resp = input("Enter name (keep/[t]itle): ")
    if item != resp: new["permutations"].append(resp)
    new["full_name"] = resp
    if resp == "k": new["full_name"] = item

    # ORDINALITY
    if category == "artist":
        resp = input("[I]ndividual or Ensemble?")
        if resp: new["ordinality"] = "Ensemble"
        else: new["ordinality"] = "Individual"

    new["borndied"] = get_borndied(page.summary)
    new["nationality"] = get_field(page.summary, sets["nationality"], "nationality")
    if category == "artist":
        new["instrument"] = get_field(page.summary, sets["instrument"], "instrument")
    elif category == "composer":
        new["period"] = input("Enter composer period: ")
        new["sort"] = swap_first_last_name(new["full_name"])
        new["abbreviated"] = new["full_name"].split(" ")[1]

    return new

def wiki_query(search_string):
    """ featch a query result from wikipedia and determine its relevance """

    # call out to wikipedia
    query = wikipedia.search(search_string)

    # print options
    print("Options: ")
    print("\t-3: Translate\n\t-2: New string\n\t-1: Die\n")

    # print query results
    print("Query returns: ")
    if query: [print("\t%d: %s" % (i, v)) for i, v in enumerate(query)]

    # prompt action
    idx = input("Enter choice: ")

    # default, accept the first result
    if not idx: return wikipedia.page(query[0])

    # handle cases
    idx = int(idx)
    if (idx) >= 0: return wikipedia.page(query[idx])
    elif (idx) == -1: return []
    elif (idx) == -2: return wiki_query(input("Try a new search string: "))
    elif (idx) == -3: wiki_query(get_translation(search_string))
    else: return []

def artist_fields_from_manual(artist):
    new_a = {}
    resp = input("Translate/skip/continue: [t/s/<cr>]")
    if resp:
        if resp == "t":
            artist = get_translate(artist)
        elif resp == "s":
            return

    call(['googler', '-n', '3', artist])

    new_a["permutations"] = [artist]

    resp = input("Enter name ([k]eep): ")
    if not resp:
        new_a["full_name"] = artist
    else:
        new_a["full_name"] = resp
        if artist != resp:
            new_a["permutations"].append(resp)

    artist = new_a["full_name"]
    resp = input("[I]ndividual or Ensemble?")

    if resp: new_a["ordinality"] = "Ensemble"
    else: new_a["ordinality"] = "Individual"

    new_a["borndied"] = input("Enter dates: ")
    new_a["nationality"] = input("Enter nationality: ")
    new_a["instrument"] = input("Enter instrument: ")
    return new_a

def itunes_lookup(artist, album):
    query = []
    for aquery in itunespy.search_album(artist):
        d = distance.edit_distance(aquery.collection_name, album)
        # print("{} --> distance: {}".format(aquery.collection_name, d))
        if d < 5:
            query = itunespy.lookup(id=aquery.collection_id)[0]
            break

    if not query:
        print("album search failed...")
        sys.exit()

    return query

