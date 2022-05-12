import gzip
import hashlib
import pickle
import rpm
import os
import sys
import xml.etree.ElementTree as ET
import xml.sax

STREAM = 'f36'
ID_PREFIX = 'org.fedoraproject'
# branch of flatpak-rpm-macros and flatpak-runtime-config
RPM_BRANCH = 'f36'
DATASET_ARG = '--dataset=f36'
# If this is True, then we'll use the "base" profiles (freedesktop-based) as the main profiles
BASEONLY = False

XDG_CACHE_HOME = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")

# This needs to be in sync with fedmod
REPOS = [
    "f36--fedora",
    "f36--updates",
]

# packages that are only available on specific architectures
ARCH_SPECIFIC_PACKAGES = {}

ARCH_SPECIFIC_PACKAGES['x86_64'] = [
    "fftw-libs-quad",
    "glibc-headers-x86",
    "libipt",
    "libquadmath",
    "libquadmath-devel",
    "libvmaf",
    "libvmaf-devel",
    "svt-av1-libs",
]

_log_name = None

def set_log_name(name):
    global _log_name
    _log_name = name

def warn(msg):
    print("{}: \033[31m{}\033[39m".format(_log_name, msg), file=sys.stderr)

def error(msg):
    print("{}: \033[31m{}\033[39m".format(_log_name, msg), file=sys.stderr)
    sys.exit(1)

def start(msg):
    print("{}: \033[90m{} ... \033[39m".format(_log_name, msg), file=sys.stderr, end="")
    sys.stderr.flush()

def done():
    print("\033[90mdone\033[39m", file=sys.stderr)

def package_cmp(p1, p2):
    n1, e1, v1, r1, a1 = p1
    n2, e2, v2, r2, a2 = p2

    if a1 == 'i686' and a2 != 'i686':
        return 1
    if a1 != 'i686' and a2 == 'i686':
        return -1

    if n1.startswith('compat-') and not n2.startswith('compat-'):
        return 1
    elif n2.startswith('compat-') and not n1.startswith('compat-'):
        return -1

    if n1.startswith('python2-') and n2.startswith('python3-'):
        return 1
    elif n1.startswith('python3-') and n2.startswith('python2-'):
        return -1

    if n1 < n2:
        return -1
    elif n1 > n2:
        return 1

    if e1 is None:
        e1 = '0'
    if e2 is None:
        e2 = '0'

    return - rpm.labelCompare((e1, v1, r1), (e2, v2, r2))

class FilesMapHandler(xml.sax.handler.ContentHandler):
    def __init__(self, cb):
        self.cb = cb
        self.package_info = None
        self.name = None
        self.arch = None
        self.epoch = None
        self.version = None
        self.release = None
        self.file = None
        self.package_info = None

    def startElement(self, name, attrs):
        if name == 'package':
            self.name = attrs['name']
            self.arch = attrs['arch']
        elif name == 'version':
            if self.name is not None:
                self.epoch = attrs['epoch']
                self.version = attrs['ver']
                self.release = attrs['rel']
        elif name == 'file':
            self.file = ''

    def endElement(self, name):
        if name == 'package':
            self.package_info = None
        elif name == 'file':
            if self.package_info is None:
                self.package_info = (self.name, self.epoch, self.version, self.release, self.arch)
            self.cb(self.package_info, self.file)
            self.file = None

    def characters(self, content):
        if self.file is not None:
            self.file += content

def foreach_file(repo_info, cb):
    for repo in REPOS:
        start("Scanning files for {}".format(repo))
        repo_dir, repomd_contents = repo_info[repo]
        root = ET.fromstring(repomd_contents)

        ns = {'repo': 'http://linux.duke.edu/metadata/repo'}
        filelists_location = root.find("./repo:data[@type='filelists']/repo:location", ns).attrib['href']
        filelists_path = os.path.join(repo_dir, filelists_location)
        if os.path.commonprefix([filelists_path, repo_dir]) != repo_dir:
            done()
            error("{}: filelists directory is outside of repository".format(repo_dir))

        handler = FilesMapHandler(cb)
        with gzip.open(filelists_path, 'rb') as f:
            xml.sax.parse(f, handler)

        done()

class PackageMapHandler(xml.sax.handler.ContentHandler):
    def __init__(self, cb):
        self.cb = cb
        self.name = None
        self.sourcerpm = None
        self.chars = None

    def startElement(self, name, attrs):
        if name == 'package':
            pass
        elif name in ('name', 'rpm:sourcerpm'):
            self.chars = ''

    def endElement(self, name):
        if name == 'package':
            self.cb(self.name, self.sourcerpm)
            self.name = None
            self.sourcerpm = None
        elif name == 'name':
            self.name = self.chars
            self.chars = None
        elif name == 'rpm:sourcerpm':
            self.sourcerpm = self.chars
            self.chars = None

    def characters(self, content):
        if self.chars is not None:
            self.chars += content

def foreach_package(repo_info, cb):
    for repo in REPOS:
        start("Scanning files for {}".format(repo))
        repo_dir, repomd_contents = repo_info[repo]
        root = ET.fromstring(repomd_contents)

        ns = {'repo': 'http://linux.duke.edu/metadata/repo'}
        filelists_location = root.find("./repo:data[@type='primary']/repo:location", ns).attrib['href']
        filelists_path = os.path.join(repo_dir, filelists_location)
        if os.path.commonprefix([filelists_path, repo_dir]) != repo_dir:
            done()
            error("{}: filelists directory is outside of repository".format(repo_dir))

        handler = PackageMapHandler(cb)
        with gzip.open(filelists_path, 'rb') as f:
            xml.sax.parse(f, handler)

        done()

def get_repo_cacheable(name, generate):
    hash_text = ''
    repos_dir = os.path.join(XDG_CACHE_HOME, "fedmod/repos")
    repo_info = {}
    for repo in REPOS:
        repo_dir = os.path.join(repos_dir, repo, 'x86_64')
        repomd_path = os.path.join(repo_dir, 'repodata/repomd.xml')
        try:
            with open(repomd_path, 'rb') as f:
                repomd_contents = f.read()
        except (OSError, IOError):
            print("Cannot read {}, try 'fedmod " + DATASET_ARG + " fetch-metadata'".format(repomd_path), file=sys.stderr)
            sys.exit(1)

        repo_info[repo] = (repo_dir, repomd_contents)
        hash_text += '{}|{}\n'.format(repo, hashlib.sha256(repomd_contents).hexdigest())

    repo_hash = hashlib.sha256(hash_text.encode("UTF-8")).hexdigest()

    cache_path = os.path.join('out', name + ".gz")

    try:
        with gzip.open(cache_path, 'rb') as f:
            old_repo_hash = f.read(64).decode('utf-8')
            if old_repo_hash == repo_hash:
                start("Reading " + name)
                data = pickle.load(f)
                done()

                return data
    except FileNotFoundError:
        pass

    data = generate(repo_info)

    start("Writing " + name)
    with gzip.open(cache_path, 'wb') as f:
        f.write(repo_hash.encode('utf-8'))
        pickle.dump(data, f)
    done()

    return data

