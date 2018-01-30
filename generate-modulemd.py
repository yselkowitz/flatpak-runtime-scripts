#!/usr/bin/python3
import sys
from yaml_utils import ordered_load, ordered_dump

with open('flatpak-runtime.in.yaml') as f:
    modulemd = ordered_load(f)

def set_profile(profile_name, list_file):
    with open(list_file) as f:
        packages = [l.strip() for l in f]
    print("{}: {} packages".format(profile_name, len(packages)), file=sys.stderr)
    modulemd['data']['profiles'][profile_name] = packages

set_profile('runtime', 'out/runtime.profile')
set_profile('runtime-base', 'out/runtime-base.profile')
set_profile('sdk', 'out/sdk.profile')
set_profile('sdk-base', 'out/sdk-base.profile')

with open('flatpak-runtime.yaml', 'w') as f:
    ordered_dump(modulemd, stream=f, default_flow_style=False, encoding="utf-8")
