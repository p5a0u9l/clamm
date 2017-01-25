#!/bin/sh

data_file=/tmp/shairport-sync-pcm
n_samp=1000
sleepy=0.3

while [ 1 ]; do
    # format as 16-bit decimal             2-channel, so   limit to N                        replace default
    #                                     every other row   samples        plot to terminal   * with cleaner .
    hexdump -v -e '/2 "%d\n"' $data_file | awk 'NR%2==1' | head -$n_samp | ./scripts/eplot | sed 's/\*/./g'
    sleep $sleepy
done

