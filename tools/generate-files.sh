#!/bin/bash

out=$1
base=$(basename $out)

case $base in
    freedesktop-*)
	ns=org.freedesktop
	version=19.08
	;;
    gnome-*)
	ns=org.gnome
	version=3.34
	;;
    *)
	echo 1>&2 "Can't identify runtime for $base"
	exit 1
	;;
esac

case $base in
    *-Platform.files)
	sdk=
	type=Platform
	;;
    *-Sdk.files)
	sdk=--sdk
	type=Sdk
	;;
    *)
	echo 1>&2 "Can't identify type for $base"
	exit 1
	;;
esac

runtime="$ns.$type/x86_64/$version"

echo "$base: listing files in $runtime"

flatpak run \
        --file-forwarding \
        --command=/usr/bin/python3 $runtime @@ tools/list-files.py @@ $sdk \
        > $out.tmp && mv $out.tmp $out || rm $out.tmp
