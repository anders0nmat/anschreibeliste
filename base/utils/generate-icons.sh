#!/bin/bash

cd ../static/

convert () {
    local src_path="$1.svg"
    local dst_name="$3"
    if [ -z "$dst_name" ]; then
        dst_name="$1-$2x$2"
    fi

    local dst_path="$dst_name.png"

    echo -n "Exporting $dst_path... "
    inkscape --export-filename=$dst_path -w $2 -h $2 $src_path
    echo "Done."
}

if command -v inkscape > /dev/null 2>&1; then
    convert appicon 180 apple-touch-icon
    convert favicon 96
    convert favicon 48 favicon
    convert appicon 192 web-app-manifest-192x192.png
    convert appicon 512 web-app-manifest-512x512.png

else
    echo "inkscape is required"
fi