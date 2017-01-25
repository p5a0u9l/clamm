#!/bin/sh

# options
# -y force overwrite of output file
# -t duration the length o time to record for
# -report log debug report
# -hide_banner no copywrite notice

artist_name=$1
album_name=$2
duration=$3
frame_rate="44.1k"
input_pipe=/tmp/shairport-sync-pcm
output_file_path=$HOME/apple_music_streams
output_file="$output_file_path/$artist_name;$album_name.flac"
echo $output_file

ffmpeg -y -report -hide_banner -f s16le -ar $frame_rate -ac 2 -i $input_pipe -t $duration $output_file

