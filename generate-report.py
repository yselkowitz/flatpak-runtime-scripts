#!/usr/bin/python3

from jinja2 import Environment, FileSystemLoader, select_autoescape
import locale
import os
import subprocess
import sys

def start(msg):
    print("{}: \033[90m{} ... \033[39m".format(os.path.basename(sys.argv[0]), msg), file=sys.stderr, end="")
    sys.stderr.flush()

def done():
    print("\033[90mdone\033[39m", file=sys.stderr)

class Package(object):
    def __init__(self, name):
        self.name = name
        self.freedesktop_platform = 0
        self.freedesktop_platform_files = None
        self.gnome_platform = 0
        self.gnome_platform_files = None
        self.freedesktop_sdk = 0
        self.freedesktop_sdk_files = None
        self.gnome_sdk = 0
        self.gnome_sdk_files = None
        self.live = 0
        self.rf26 = 0

    @property
    def runtimes(self):
        return self.freedesktop_platform or self.gnome_platform or self.freedesktop_sdk or self.gnome_sdk

    @property
    def klass(self):
        k = ""
        if self.live and not self.runtimes:
            k = "live-only"
        if self.gnome_platform and not self.live:
            k = "not-on-live"

        if self.modules in ("", "installer"):
            k += " build"

        return k

    @property
    def modules(self):
        return package_to_module.get(self.name, "")

    @property
    def note(self):
        if self.gnome_platform and not self.live:
            return "platform package not on Live image"
        else:
            return ""

    def files_str(self, which):
        files = getattr(self, which + '_files')
        if files is None:
            return ''
        elif len(files) <= 3:
            return ' '.join(files)
        else:
            return ' '.join(files[:3]) + ' ...'

    @property
    def freedesktop_platform_files_str(self):
        return self.files_str('freedesktop_platform')

    @property
    def freedesktop_sdk_files_str(self):
        return self.files_str('freedesktop_sdk')

    @property
    def gnome_platform_files_str(self):
        return self.files_str('gnome_platform')

    @property
    def gnome_sdk_files_str(self):
        return self.files_str('gnome_sdk')

class Letter(object):
    def __init__(self, letter):
        self.letter = letter
        self.packages = []

#
# Get information about packages
#

packages = dict()
def add_package(name, which, level):
    pkg = packages.get(name, None)
    if pkg is None:
        pkg = Package(name)
        packages[name] = pkg
    if getattr(pkg, which) < level:
        setattr(pkg, which, level)

def add_packages(filename, which, resolve_deps=False):
    start("Adding packages from {}".format(filename))
    with open(filename) as f:
        packages = list(line.strip() for line in f)

    for package in packages:
        add_package(package, which, level=2)

    if resolve_deps:
        output = subprocess.check_output(['fedmod', 'resolve-deps'] + packages, encoding='utf-8')
        dep_packages = list(line.strip() for line in output.split())

        for package in dep_packages:
            add_package(package, which, level=1)
    done()

def add_package_files(filename, which):
    with open(filename) as f:
        for line in f:
            f, p = line.strip().split()
            f = f[:-1] # strip trailing :
            pkg = packages[p]
            old = getattr(pkg, which + '_files')
            if old is not None:
                old.append(f)
            else:
                setattr(pkg, which + '_files', [f])

add_packages('out/freedesktop-Platform.packages', 'freedesktop_platform', resolve_deps=True)
add_packages('out/freedesktop-Sdk.packages', 'freedesktop_sdk', resolve_deps=True)
add_packages('out/gnome-Platform.packages', 'gnome_platform', resolve_deps=True)
add_packages('out/gnome-Sdk.packages', 'gnome_sdk', resolve_deps=True)
add_packages('f27-live.packages', 'live')
add_packages('f26-flatpak-runtime.packages', 'rf26')

add_package_files('out/freedesktop-Platform.matched', 'freedesktop_platform')
add_package_files('out/freedesktop-Sdk.matched', 'freedesktop_sdk')
add_package_files('out/gnome-Platform.matched', 'gnome_platform')
add_package_files('out/gnome-Sdk.matched', 'gnome_sdk')

letters_map = dict()
for k, v in packages.items():
    l = v.name[0].upper()
    letter = letters_map.get(l, None)
    if letter is None:
        letter = Letter(l)
        letters_map[l] = letter
    letter.packages.append(v)

letters = []
for k in sorted(letters_map.keys()):
    letter = letters_map[k]
    letter.packages.sort(key=lambda p: locale.strxfrm(p.name))
    letters.append(letter)

start("Loading package to module map")
package_to_module = dict()

output = subprocess.check_output(['fedmod', 'list-rpms', '--list-modules'], encoding='utf-8')
for l in output.split('\n'):
    fields = l.strip().split()
    if len(fields) != 2:
        continue
    package_to_module[fields[0]] = fields[1][1:-1]
done()

#
# Get summary information for unmatched files
#

def count_lines(fname):
    with open(fname) as f:
        return len(list(f))

unmatched_counts = {
    'freedesktop_platform': count_lines('out/freedesktop-Platform.unmatched'),
    'gnome_platform': count_lines('out/gnome-Platform.unmatched'),
    'freedesktop_sdk': count_lines('out/freedesktop-Sdk.unmatched'),
    'gnome_sdk': count_lines('out/gnome-Sdk.unmatched'),
}

#
# Generate the report
#

env = Environment(
    loader=FileSystemLoader('.'),
    autoescape=select_autoescape(['html', 'xml']),
    trim_blocks=True,
    lstrip_blocks=True
)

template = env.get_template('report-template.html')

with open('report.html', 'w') as f:
    f.write(template.render(letters=letters, unmatched=unmatched_counts, package_to_module=package_to_module))
