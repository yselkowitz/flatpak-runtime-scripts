#!/usr/bin/python3

from jinja2 import Environment, FileSystemLoader, select_autoescape
import locale

class Package(object):
    def __init__(self, name):
        self.name = name
        self.freedesktop_platform = False
        self.freedesktop_platform_files = None
        self.gnome_platform = False
        self.gnome_platform_files = None
        self.freedesktop_sdk = False
        self.freedesktop_sdk_files = None
        self.gnome_sdk = False
        self.gnome_sdk_files = None
        self.live = False
        self.rf26 = False

    @property
    def runtimes(self):
        return self.freedesktop_platform or self.gnome_platform or self.freedesktop_sdk or self.gnome_sdk

    @property
    def klass(self):
        if self.live and not self.runtimes:
            return "live-only"
        if self.gnome_platform and not self.live:
            return "not-on-live"
        return ""

    @property
    def note(self):
        return {
            "not-on-live": "platform package not on Live image"
        }.get(self.klass, "")

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

env = Environment(
    loader=FileSystemLoader('.'),
    autoescape=select_autoescape(['html', 'xml']),
    trim_blocks=True,
    lstrip_blocks=True
)

packages = dict()
def add_package(name, which):
    pkg = packages.get(name, None)
    if pkg is None:
        pkg = Package(name)
        packages[name] = pkg
    setattr(pkg,which, True)

def add_packages(filename, which):
    with open(filename) as f:
        for line in f:
            add_package(line.strip(), which)

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

add_packages('out/freedesktop-Platform.packages', 'freedesktop_platform')
add_packages('out/freedesktop-Sdk.packages', 'freedesktop_sdk')
add_packages('out/gnome-Platform.packages', 'gnome_platform')
add_packages('out/gnome-Sdk.packages', 'gnome_sdk')
add_packages('f27-live.packages', 'live')
add_packages('f26-flatpak-runtime.packages', 'rf26')

add_package_files('out/freedesktop-Platform.matched', 'freedesktop_platform')
add_package_files('out/freedesktop-Sdk.matched', 'freedesktop_sdk')
add_package_files('out/gnome-Platform.matched', 'gnome_platform')
add_package_files('out/gnome-Sdk.matched', 'gnome_sdk')

def count_lines(fname):
    with open(fname) as f:
        return len(list(f))

unmatched_counts = {
    'freedesktop_platform': count_lines('out/freedesktop-Platform.unmatched'),
    'gnome_platform': count_lines('out/gnome-Platform.unmatched'),
    'freedesktop_sdk': count_lines('out/freedesktop-Sdk.unmatched'),
    'gnome_sdk': count_lines('out/gnome-Sdk.unmatched'),
}

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

template = env.get_template('report-template.html')

with open('report.html', 'w') as f:
    f.write(template.render(letters=letters, unmatched=unmatched_counts))

