#!/usr/bin/python3
import sys
from yaml_utils import ordered_load, ordered_dump
from util import ID_PREFIX, STREAM, RPM_BRANCH, BASEONLY, ARCH_SPECIFIC_PACKAGES

template = 'flatpak-runtime-baseonly.in.yaml' if BASEONLY else 'flatpak-runtime.in.yaml'

with open(template) as f:
    modulemd_string = f.read()

modulemd_string = modulemd_string \
    .replace('@ID_PREFIX@', ID_PREFIX) \
    .replace('@STREAM@', STREAM) \
    .replace('@RPM_BRANCH@', RPM_BRANCH)

modulemd = ordered_load(modulemd_string)

def set_profile(profile_name, list_file):
    with open(list_file) as f:
        packages = ['flatpak-runtime-config'] + [l.strip() for l in f]
    print("{}: {} packages".format(profile_name, len(packages)), file=sys.stderr)
    modulemd['data']['profiles'][profile_name]['rpms'] = [p for p in packages if p not in ARCH_SPECIFIC_PACKAGES['x86_64'] and p not in ARCH_SPECIFIC_PACKAGES['s390x']]
    modulemd['data']['profiles'][profile_name+'-x86_64']['rpms'] = [p for p in packages if p in ARCH_SPECIFIC_PACKAGES['x86_64']]
    modulemd['data']['profiles'][profile_name+'-s390x']['rpms'] = [p for p in packages if p in ARCH_SPECIFIC_PACKAGES['s390x']]

if BASEONLY:
    set_profile('runtime', 'out/runtime-base.profile')
    set_profile('sdk', 'out/sdk-base.profile')
else:
    set_profile('runtime', 'out/runtime.profile')
    set_profile('runtime-base', 'out/runtime-base.profile')
    set_profile('sdk', 'out/sdk.profile')
    set_profile('sdk-base', 'out/sdk-base.profile')

with open('flatpak-runtime.new.yaml', 'w') as f:
    ordered_dump(modulemd, stream=f, default_flow_style=False, encoding="utf-8")
