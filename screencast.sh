#!/bin/bash

echo "Click a window to capture"
xwininfo > "/tmp/$$_xwinf"

WIDTH="$(grep Width "/tmp/$$_xwinf" | perl -pe "s/\D+(\d+)\D+/\1/g")"
HEIGHT="$(grep Height "/tmp/$$_xwinf" | perl -pe "s/\D+(\d+)\D+/\1/g")"
OFFX="$(grep 'Absolute upper-left X' "/tmp/$$_xwinf" | perl -pe "s/\D+(\d+)\D+/\1/g")"
OFFY="$(grep 'Absolute upper-left Y' "/tmp/$$_xwinf" | perl -pe "s/\D+(\d+)\D+/\1/g")"

rm -f "/tmp/$$_xwinf"

echo "Run:"
echo ffmpeg \
    -f alsa \
    -i default \
    -f x11grab \
    -r 15 \
    -s "${WIDTH}x${HEIGHT}" \
    -i ":0.0+$OFFX,$OFFY" \
    /tmp/screencast.mp4
