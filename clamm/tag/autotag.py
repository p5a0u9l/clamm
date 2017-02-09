#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
from subprocess import Popen

# external
import wikipedia
import nltk

tk = nltk.tokenize.WordPunctTokenizer()


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
    """
    extract artist/composer vital date(s) from a wikipedia summary string
    """

    m = re.findall("\d{4}", summary)

    if len(m) >= 2:
        born = m[0] + "-" + m[1]
        if not input("Accept %s? [y]/n: " % (born)):
            return born

        else:
            born = m[0] + "-"
            if not input("Accept %s? [y]/n: " % (born)): return born

    elif len(m) >= 1:
        born = m[0] + "-"

        resp = input("Accept %s? [y]/n: " % (born))
        if not resp:
            return born

    else:
        return input("Enter Dates: ")


def item_fields_from_wiki(item, page, sets, category="artist"):
    """
    extract database tags/fields from a successful wikipedia query
    """

    new = {"permutations": [item]}
    print(page.summary)

    # NAME
    resp = input("Enter name (keep/[t]itle): ")
    if item != resp:
        new["permutations"].append(resp)
    new["full_name"] = resp
    if resp == "k":
        new["full_name"] = item

    # ORDINALITY
    if category == "artist":
        if input("[I]ndividual or Ensemble?"):
            new["ordinality"] = "Ensemble"
        else:
            new["ordinality"] = "Individual"

    new["borndied"] = get_borndied(page.summary)
    new["nationality"] = get_field(
            page.summary, sets["nationality"], "nationality")
    if category == "artist":
        new["instrument"] = get_field(
                page.summary, sets["instrument"], "instrument")
    elif category == "composer":
        new["period"] = input("Enter composer period: ")
        new["sort"] = swap_first_last_name(new["full_name"])
        new["abbreviated"] = new["full_name"].split(" ")[1]

    return new


def wiki_query(search_string):
    """
    fetch a query result from wikipedia and determine its relevance
    """

    # call out to wikipedia
    query = wikipedia.search(search_string)

    # print options
    print("Options: ")
    print("\t-3: Translate\n\t-2: New string\n\t-1: Die\n")

    # print query results
    print("Query returns: ")
    if query:
        cutil.pretty_dict(query.items())

    # prompt action
    idx = input("Enter choice (default to 0):")

    # default, accept the first result
    if not idx:
        return wikipedia.page(query[0])

    # handle cases
    idx = int(idx)
    if (idx) >= 0:
        return wikipedia.page(query[idx])
    elif (idx) == -1:
        return []
    elif (idx) == -2:
        return wiki_query(input("Try a new search string: "))
    elif (idx) == -3:
        wiki_query(get_translation(search_string))
    else:
        return []


def artist_fields_from_manual(artist):
    resp = input("Translate/skip/continue: t/s/[<cr>]")
    if resp:
        if resp == "t":
            artist = get_translate(artist)
        elif resp == "s":
            return

    Popen(['googler', '-n', '3', artist])

    new["permutations"] = [artist]

    resp = input("Enter name ([k]eep): ")
    if not resp:
        new["full_name"] = artist
    else:
        new["full_name"] = resp
        if artist != resp:
            new["permutations"].append(resp)

    artist = new["full_name"]

    resp = input("[I]ndividual or Ensemble?")
    if resp:
        new["ordinality"] = "Ensemble"
    else:
        new["ordinality"] = "Individual"

    new["borndied"] = input("Enter dates: ")
    new["nationality"] = input("Enter nationality: ")
    new["instrument"] = input("Enter instrument: ")

    return new
