#!/bin/bash
set -e

nvr=$(koji list-tagged --quiet --inherit --latest f28-build appstream-data|awk '{print $1}')
path=$(koji buildinfo appstream-data-28-2.fc28 | grep noarch.rpm)
url=$(echo $path | sed s@/mnt/koji/packages/@https://kojipkgs.fedoraproject.org/packages/@)

rpm=out/$(basename $path)

[ -e $rpm ] || curl $url > $rpm

tmpdir=$(mktemp -d)
cleanup() {
    rm -rf $tmpdir
}
trap cleanup EXIT

tmpxmldir=$tmpdir/usr/share/app-info/xmls/
mkdir -p $tmpxmldir
rpm2cpio $rpm | ( cd $tmpdir && cpio -iv  './usr/share/app-info/xmls/fedora.xml.gz' )
cp $tmpxmldir/fedora.xml.gz out/fedora-appstream.xml.gz
