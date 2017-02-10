#!/bin/zsh

for f (pcm/*pcm) ffmpeg -hide_banner -y -f s16le -ar 44.1k -ac 2 -i "$f" "`echo $f | sed 's/pcm/wav/g'`"
