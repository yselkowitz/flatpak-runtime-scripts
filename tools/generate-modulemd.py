#!/usr/bin/python3
import sys
from yaml_utils import ordered_load, ordered_dump
from util import ID_PREFIX, STREAM

with open('flatpak-runtime.in.yaml') as f:
    modulemd_string = f.read()

modulemd_string = modulemd_string \
    .replace('@ID_PREFIX@', ID_PREFIX) \
    .replace('@STREAM@', STREAM)

modulemd = ordered_load(modulemd_string)

def set_profile(profile_name, list_file):
    with open(list_file) as f:
        packages = ['flatpak-runtime-config'] + [l.strip() for l in f]
    print("{}: {} packages".format(profile_name, len(packages)), file=sys.stderr)
    modulemd['data']['profiles'][profile_name]['rpms'] = packages

set_profile('runtime', 'out/runtime.profile')
set_profile('runtime-base', 'out/runtime-base.profile')
set_profile('sdk', 'out/sdk.profile')
set_profile('sdk-base', 'out/sdk-base.profile')

with open('flatpak-runtime.new.yaml', 'w') as f:
    ordered_dump(modulemd, stream=f, default_flow_style=False, encoding="utf-8")
