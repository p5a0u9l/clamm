#!/bin/sh

/usr/local/bin/metaflac --export-tags-to=tmp.txt "$1"
/usr/local/bin/vim tmp.txt
/usr/local/bin/metaflac --remove-all-tags --import-tags-from=tmp.txt "$1"
rm tmp.txt

