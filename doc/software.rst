##############
Python Modules
##############

********
audiolib
********

.. automodule:: clamm.audiolib
    :members:


****
tags
****

.. automodule:: clamm.tags
    :members:

*******
streams
*******

The streams module provides two programs for working with raw audio streams.

. The second processes a stream into an album.

listing2streams
^^^^^^^^^^^^^^^
The first use case automates generating raw ``pcm`` files from iTunes using a listing of album/artist pairs in ``json`` format. Example::

    "A2": {
        "artist": "Richard Egarr, Academy of Ancient Music & Andrew Manze",
        "album": "Bach: Harpsichord Concertos - Triple Concerto"
    }

See also batch_album_listing_ under the ``templates`` directory.

.. automodule:: streams
    :members:


.. _batch_album_listing: ../clamm/templates/batch_album_listing.json
