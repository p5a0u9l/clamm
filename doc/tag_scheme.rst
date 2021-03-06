.. _tag-scheme-label:

**************
tagging scheme
**************

The basic strategy is create a tag library consisting of representative entries for each tag entity. The library (or database) serves as the definitive representation of a COMPOSER/ARTIST. When new files are synchronized to the library, a matching entry is sought within the existing entries. If a match is found the tags of each audio file are updated to match the representation in the database. If a match can't be found, the entity is added to the database.

An audio file can be characterized by a number of tag fields

Composer
========

A COMPOSER composes a piece of music. Classical music generally differs from most genres of popular music in that the performer (ARTIST) is not the same person(s) as the COMPOSER. Example entry::

        "Isaac Albéniz": {
            "nationality": "Spanish",
            "period": "Classical/Spanish Folk",
            "full_name": "Isaac Albéniz",
            "abbreviated": "Albéniz",
            "sort": "Albéniz, Isaac",
            "borndied": "1860-1909",
            "permutations": [
                "Albéniz, Isaac",
                "Isaac Albéniz",
                "Albeniz, arr. Christopher Parkening",
                "Albéniz",
                "Albéniz, Isaac (1860-1909)"
            ]
        }

Field summary
-------------

A few of the notable fields, along with their tag file mappings, are

``full_name``: COMPOSER
^^^^^^^^^^^^^^^^^^^^^^^
The name to display

``nationality``: COMPOSER_NATIONALITY
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Where the composer was born and/or lived during their active years.

``period``: COMPOSER_PERIOD
^^^^^^^^^^^^^^^^^^^^^^^^^^^
A description of the primary sub-genre associated with the composer.

`borndied`: COMPOSER_DATES
^^^^^^^^^^^^^^^^^^^^^^^^^^
The vital dates of the composer's life.

Artist
======

ARTIST performs the music of the audio file and generally presents more of a challenge than does the  COMPOSERs.


Often a piece will list multiple performers. For example.

