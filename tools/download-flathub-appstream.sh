#!/usr/bin/sh

set -e

tmpdir=$(TMPDIR=/var/tmp mktemp -d)
cleanup() {
    rm -rf $tmpdir
}
trap cleanup EXIT

OSTREE="ostree --repo=$tmpdir/repo"

$OSTREE init --mode=bare-user
$OSTREE remote add --no-gpg-verify flathub https://flathub.org/repo
$OSTREE pull flathub appstream/x86_64
$OSTREE checkout --user-mode flathub/appstream/x86_64 $tmpdir/checkout

cp $tmpdir/checkout/appstream.xml.gz out/flathub-appstream.xml.gz





