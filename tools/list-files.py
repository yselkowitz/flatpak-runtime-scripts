#!/usr/bin/python3

import os
import re
import sys

sdk = len(sys.argv) > 1 and sys.argv[1] == '--sdk'

def output_dir(d):
    for f in sorted(os.listdir(d)):
        full = os.path.join(d, f)
        if not os.path.isdir(full):
            print(os.path.join(d, f))

def output_dir_recurse(d):
    for dirName, subdirs, files in os.walk(d):
            for f in sorted(files):
              print(os.path.join(dirName, f))

output_dir('/usr/bin')

for f in os.listdir('/usr/lib'):
    full = os.path.join('/usr/lib', f)
    if (re.match(r'^.*\.so\.\d+$', f) is not None or
        re.match(r'^.*\.so$', f) is not None and not os.path.islink(full)):
        print(full)

output_dir_recurse('/usr/share/fonts')
output_dir_recurse('/usr/share/themes')

if sdk:
    output_dir_recurse('/usr/include')
    output_dir('/usr/lib/pkgconfig')
    output_dir('/usr/share/pkgconfig')

# import pkgutil
# for f in pkgutil.iter_modules():
#     try:
#         path = f[0].path
#         if path.find('site-packages') < 0:
#             continue
#     except AttributeError:
#         continue
#     if not(f[1].startswith('_')):
#         print(f, 'python3dist({})'.format(f[1]))

