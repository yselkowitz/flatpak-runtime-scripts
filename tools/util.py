from dataclasses import dataclass
import gzip
import hashlib
from pathlib import Path
import pickle
import rpm
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
import xml.sax

RELEASE = 'f39'
ID_PREFIX = 'org.fedoraproject'
TAG = f'{RELEASE}-flatpak-runtime-packages'
TAG_ARG = f'--tag={TAG}'
# If this is True, then we'll use the "base" profiles (freedesktop-based) as the main profiles
BASEONLY = False

XDG_CACHE_HOME = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")

# packages that are only available or required on specific architectures
ARCH_SPECIFIC_PACKAGES = {}

ARCH_SPECIFIC_PACKAGES['aarch64'] = [
    "binutils-gprofng",
    "libhwasan",
]

ARCH_SPECIFIC_PACKAGES['ppc64le'] = [
    "libquadmath",
    "libquadmath-devel",
]

ARCH_SPECIFIC_PACKAGES['s390x'] = [
    "glibc-headers-s390",
]

ARCH_SPECIFIC_PACKAGES['x86_64'] = [
    "binutils-gprofng",
    "fftw-libs-quad",
    "glibc-headers-x86",
    "intel-mediasdk",
    "libhwasan",
    "libipt",
    "libquadmath",
    "libquadmath-devel",
    "libvmaf",
    "libvmaf-devel",
    "libvpl",
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

    if (n1.startswith('jack-audio-connection-kit')
            and n2.startswith('pipewire-jack-audio-connection-kit')):
        return 1
    elif (n1.startswith('pipewire-jack-audio-connection-kit')
            and n2.startswith('jack-audio-connection-kit')):
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


@dataclass
class RepoInfo():
    metadata_path: Path
    repomd_contents: bytes

    @staticmethod
    def fetch():
        metadata_path = Path(subprocess.check_output([
            "flatpak-module-depchase", TAG_ARG, "fetch-metadata", "--print-location"
        ], universal_newlines=True).strip())

        with open(metadata_path / "repomd.xml", "rb") as f:
            repomd_contents = f.read()

        return RepoInfo(metadata_path, repomd_contents)

    def get_metadata_file(self, type_):
        root = ET.fromstring(self.repomd_contents)
        ns = {'repo': 'http://linux.duke.edu/metadata/repo'}
        location_element = root.find(f"./repo:data[@type='{type_}']/repo:location", ns)
        assert location_element is not None
        location = location_element.attrib['href']
        path = self.metadata_path.parent / location
        if Path(os.path.commonpath([path, self.metadata_path])) != self.metadata_path:
            raise RuntimeError(f"{self.metadata_path}: {type} file is outside of repository")

        return path


class FilesMapHandler(xml.sax.ContentHandler):
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


def foreach_file(repo_info: RepoInfo, cb):
    start(f"Scanning files for {TAG}")
    filelists_path = repo_info.get_metadata_file("filelists")

    handler = FilesMapHandler(cb)
    with gzip.open(filelists_path, 'rb') as f:
        xml.sax.parse(f, handler)

    done()


class PackageMapHandler(xml.sax.ContentHandler):
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


def foreach_package(repo_info: RepoInfo, cb):
    start(f"Scanning files for {TAG}")

    primary_path = repo_info.get_metadata_file("primary")
    handler = PackageMapHandler(cb)
    with gzip.open(primary_path, 'rb') as f:
        xml.sax.parse(f, handler)

    done()


def get_repo_cacheable(name, generate):
    repo_info = RepoInfo.fetch()
    repo_hash = hashlib.sha256(repo_info.repomd_contents).hexdigest()

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
