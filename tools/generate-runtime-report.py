#!/usr/bin/python3

from jinja2 import Environment, FileSystemLoader, select_autoescape
import json
import locale
import os
import re
import subprocess
import sys

def start(msg):
    print("{}: \033[90m{} ... \033[39m".format(os.path.basename(sys.argv[0]), msg), file=sys.stderr, end="")
    sys.stderr.flush()

def done():
    print("\033[90mdone\033[39m", file=sys.stderr)

def warn(msg):
    print("{}: \033[31m{}\033[39m".format(os.path.basename(sys.argv[0]), msg), file=sys.stderr)

def fedmod_output(args):
    return subprocess.check_output(['fedmod'] + args, encoding='utf-8')

_nvr_to_name_re = re.compile('^(.*)-[^-]*-[^-]*')
def nvr_to_name(nvr):
    return _nvr_to_name_re.match(nvr).group(1)

class Package(object):
    def __init__(self, name):
        self.name = name
        self.freedesktop_platform = 0
        self.freedesktop_platform_files = None
        self.freedesktop_platform_required_by = None
        self.gnome_platform = 0
        self.gnome_platform_files = None
        self.gnome_platform_required_by = None
        self.freedesktop_sdk = 0
        self.freedesktop_sdk_files = None
        self.freedesktop_sdk_required_by = None
        self.gnome_sdk = 0
        self.gnome_sdk_files = None
        self.gnome_sdk_required_by = None
        self.live = 0
        self.rf26 = 0
        self.source_package = None
        self.flag = None
        self._note = None

    @property
    def runtimes(self):
        return self.freedesktop_platform or self.gnome_platform or self.freedesktop_sdk or self.gnome_sdk

    @property
    def klass(self):
        if self.flag == 'F':
            return "flagged"
        elif self.flag == 'F?':
            return "questionable"
        elif self.flag == 'FD':
            return "flagged-dep"
        elif self.flag == 'W':
            return "waived"
        elif self.flag is not None and self.flag.startswith('E'):
            return "extra"
        elif self.gnome_platform and not self.live:
            return "questionable"

    @property
    def modules(self):
        return package_to_module.get(self.name, "")

    @property
    def note(self):
        if self._note:
            return self._note
        elif self.gnome_platform and not self.live:
            return "platform package not on Live image"
        else:
            return ""

    def why(self, which):
        files = getattr(self, which + '_files')
        if files is None:
            files_str = ''
        elif len(files) <= 3:
            files_str=  'Files: ' + ' '.join(files)
        else:
            files_str = 'Files: ' + ' '.join(files[:3]) + ' ...'

        required_by = getattr(self, which + '_required_by')
        if required_by is None:
            required_by_str = ''
        else:
            required_by = sorted(required_by, key=lambda x: x[0])
            required_by_str = '\n'.join('{} ({})'.format(req, provider) for req, provider in required_by)

        if files_str and required_by_str:
            return files_str + '\n' + required_by_str
        elif files_str:
            return files_str
        elif required_by_str:
            return required_by_str
        else:
            return ''

    @property
    def freedesktop_platform_why(self):
        return self.why('freedesktop_platform')

    @property
    def freedesktop_sdk_why(self):
        return self.why('freedesktop_sdk')

    @property
    def gnome_platform_why(self):
        return self.why('gnome_platform')

    @property
    def gnome_sdk_why(self):
        return self.why('gnome_sdk')

    def inclusion(self, which):
        level = getattr(self, which)
        if level == 0:
            return 'absent'
        elif level == 1:
            return 'dep'
        else:
            required_by = getattr(self, which + '_required_by', False)
            if required_by is False:
                return 'present'
            elif required_by is not None and len(required_by) > 0:
                return 'files'
            elif self.flag is not None and self.flag.startswith('E'):
                return 'extra'
            else:
                return 'root'

    @property
    def freedesktop_platform_inclusion(self):
        return self.inclusion('freedesktop_platform')

    @property
    def freedesktop_sdk_inclusion(self):
        return self.inclusion('freedesktop_sdk')

    @property
    def gnome_platform_inclusion(self):
        return self.inclusion('gnome_platform')

    @property
    def gnome_sdk_inclusion(self):
        return self.inclusion('gnome_sdk')

    @property
    def live_inclusion(self):
        return self.inclusion('live')

    @property
    def rf26_inclusion(self):
        return self.inclusion('rf26')

class SourcePackage(object):
    def __init__(self, name):
        self.name = name
        self.packages = []

    @property
    def modules(self):
        old_modules = self.packages[0].modules
        klass = self.klass
        if klass == "build-platform":
            new_module = "desktop-runtime"
        elif klass == "build-sdk":
            new_module = "flatpak-runtime"
        else:
            new_module = None

        if old_modules and new_module:
            return old_modules + " ⇒ " + new_module
        elif old_modules:
            return old_modules
        else:
            return new_module

    @property
    def sdk_only(self):
        return sdk_only

    @property
    def klass(self):
        if self.packages[0].modules in ("", "installer"):
            sdk_only = True
            for package in self.packages:
                if package.freedesktop_platform or package.gnome_platform:
                    sdk_only = False
            if sdk_only:
                return "build-sdk"
            else:
                return "build-platform"
        else:
            return ""

class Letter(object):
    def __init__(self, letter):
        self.letter = letter
        self.packages = []

#
# Get information about packages
#

packages = dict()
def add_package(name, which, level, only_if_exists=False, source_package=None):
    pkg = packages.get(name, None)
    if pkg is None:
        if only_if_exists:
            return
        pkg = Package(name)
        packages[name] = pkg
    if getattr(pkg, which) < level:
        setattr(pkg, which, level)
    if source_package is not None:
        pkg.source_package = source_package

def add_packages(source, which, resolve_deps=False, only_if_exists=False):
    if isinstance(source, str):
        start("Adding packages from {}".format(source))
        with open(source) as f:
            pkgs = set(line.strip() for line in f)
    else:
        pkgs = source

    if resolve_deps:
        resolved_packages = json.loads(fedmod_output(['resolve-deps', '--json'] + list(pkgs)))
        for package in resolved_packages:
            name = nvr_to_name(package['rpm'])
            srpm_name = nvr_to_name(package['srpm'])
            add_package(name, which, level=(2 if name in pkgs else 1),
                        source_package=srpm_name, only_if_exists=only_if_exists)

        for package in resolved_packages:
            for req, providers in package['requires'].items():
                provider = nvr_to_name(providers[0])
                provider_package = packages.get(provider, None)
                if provider_package is None: # filtered out of the resolve-deps output - e.g., fedora-release
                    continue
                required_by = getattr(provider_package, which + '_required_by')
                if required_by is None:
                    required_by = []
                    setattr(provider_package, which + '_required_by', required_by)
                required_by.append((nvr_to_name(package['rpm']), req))
    else:
        for package in pkgs:
            add_package(package, which, level=2, only_if_exists=only_if_exists)

    if isinstance(source, str):
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

def read_package_notes():
    comment_re = re.compile(r'\s*#.*')
    flag_re = re.compile(r'[A-Z_?]+$')
    package_re = re.compile(r'\S+')

    with open("package-notes.txt") as f:
        for line in f:
            line = comment_re.sub('', line)
            line = line.strip()
            if line == '':
                continue
            parts = line.split(":", 2)
            name = parts[0].strip()
            if not re.match(package_re, name):
                warn("Can't parse package note: {}".format(line))
                continue
            if len(parts) == 1:
                flag = note = None
            elif len(parts) == 2:
                x = parts[1].strip()
                if flag_re.match(x):
                    flag = x
                    note = None
                else:
                    note = x
                    flag = None
            elif len(parts) == 3:
                x = parts[1].strip()
                if flag_re.match(x):
                    flag = x
                    note = parts[2].strip()
                else:
                    flag = None
                    note = parts[1] + ':' + parts[2]

            yield name, note, flag

add_packages('out/freedesktop-Platform.packages', 'freedesktop_platform', resolve_deps=True)
add_packages('out/freedesktop-Sdk.packages', 'freedesktop_sdk', resolve_deps=True)
add_packages('out/gnome-Platform.packages', 'gnome_platform', resolve_deps=True)
add_packages('out/gnome-Sdk.packages', 'gnome_sdk', resolve_deps=True)
add_packages('data/f27-live.packages', 'live', only_if_exists=True)
add_packages('data/f26-flatpak-runtime.packages', 'rf26', only_if_exists=True)

add_package_files('out/freedesktop-Platform.matched', 'freedesktop_platform')
add_package_files('out/freedesktop-Sdk.matched', 'freedesktop_sdk')
add_package_files('out/gnome-Platform.matched', 'gnome_platform')
add_package_files('out/gnome-Sdk.matched', 'gnome_sdk')

# Add extra packages
extra_base = []
extra_base_sdk = []
extra = []
extra_sdk = []

for name, note, flag in read_package_notes():
    if flag == 'EB':
        extra_base.append(name)
        extra_base_sdk.append(name)
        extra.append(name)
        extra_sdk.append(name)
    elif flag == 'EB_SDK':
        extra_base_sdk.append(name)
        extra_sdk.append(name)
    elif flag == 'E':
        extra.append(name)
        extra_sdk.append(name)
    elif flag == 'E_SDK':
        extra_sdk.append(name)

add_packages(extra_base, 'freedesktop_platform', resolve_deps=True)
add_packages(extra_base_sdk, 'freedesktop_sdk', resolve_deps=True)
add_packages(extra, 'gnome_platform', resolve_deps=True)
add_packages(extra_sdk, 'gnome_sdk', resolve_deps=True)

source_packages = {}
for package in packages.values():
    source_package = source_packages.get(package.source_package, None)
    if source_package is None:
        source_package = SourcePackage(package.source_package)
        source_packages[source_package.name] = source_package
    source_package.packages.append(package)

letters_map = dict()
for k, v in source_packages.items():
    v.packages.sort(key=lambda p: locale.strxfrm(p.name))
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

output = fedmod_output(['list-rpms', '--list-modules'])
for l in output.split('\n'):
    fields = l.strip().split()
    if len(fields) != 2:
        continue
    package_to_module[fields[0]] = fields[1][1:-1]
done()

# Add package notes to packages
for name, note, flag in read_package_notes():
    pkg = packages.get(name, None)
    if pkg is None:
        warn("Package note for missing package: {}".format(name))
        continue

    if flag is not None:
        pkg.flag = flag
    if note is not None:
        pkg._note = note

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
# Generate the profiles
#
def generate_profile(outfile, which):
    with open(outfile, 'w') as f:
        for letter in letters:
            for src in letter.packages:
                for pkg in src.packages:
                    if getattr(pkg, which) != 0:
                        print(pkg.name, file=f)

generate_profile('out/runtime-base.profile', 'freedesktop_platform')
generate_profile('out/sdk-base.profile', 'freedesktop_sdk')
generate_profile('out/runtime.profile', 'gnome_platform')
generate_profile('out/sdk.profile', 'gnome_sdk')

#
# Generate the report
#

env = Environment(
    loader=FileSystemLoader('.'),
    autoescape=select_autoescape(['html', 'xml']),
    trim_blocks=True,
    lstrip_blocks=True
)

template = env.get_template('runtime-template.html')

with open('reports/runtime.html', 'w') as f:
    f.write(template.render(letters=letters, unmatched=unmatched_counts, package_to_module=package_to_module))
