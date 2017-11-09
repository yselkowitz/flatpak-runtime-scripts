#!/usr/bin/python3

from functools import cmp_to_key
import dnf
import gzip
import hashlib
import os
import pickle
import re
import sys

REPO_F27 = "https://mirrors.fedoraproject.org/metalink?repo=fedora-27&arch=x86_64"
REPO_F27_UPDATES = "https://mirrors.fedoraproject.org/metalink?repo=updates-released-f27&arch=x86_64"
REPO_F27_UPDATES_TESTING = "https://mirrors.fedoraproject.org/metalink?repo=updates-testing-f27&arch=x86_64"

ignore = set()
rename = dict()

bin_ignore = [
    # A bunch of binaries built as part of nss. A few of these are
    # in /usr/lib64/nss/unsupported-tools/ as part of nss-tools, the rest are not considered
    # worth installing at all (test utilities, etc.)
    'addbuiltin', 'atob', 'baddbdir', 'bltest', 'btoa', 'certcgi', 'chktest', 'conflict',
    'crmftest', 'dbtest', 'derdump', 'dertimetest', 'digest', 'ecperf', 'encodeinttest',
    'fipstest', 'httpserv', 'listsuites', 'makepqg', 'mangle', 'multinit', 'nonspr10',
    'ocspclnt', 'ocspresp', 'oidcalc', 'p7content', 'p7env', 'p7sign', 'p7verify',
    'pk11gcmtest', 'pk11mode', 'pk1sign', 'pkix-errcodes', 'pp', 'pwdecrypt', 'remtest',
    'rsaperf', 'sdrtest', 'secmodtest', 'selfserv', 'shlibsign', 'signtool', 'strsclnt',
    'symkeyutil', 'tstclnt', 'vfychain', 'vfyserv',

    # Script added into nss by openembedded
    'signlibs.sh',

    # /usr/share/doc/aspell/aspell-import in Fedora
    'aspell-import',

    # Removed in perl-5.27
    'c2ph',

    # Removed - https://lists.fedorahosted.org/archives/list/elfutils-devel@lists.fedorahosted.org/thread/22LIIMXI6EDGCOIO6QFSBUO2KHEXIGSJ/
    'eu-ld',

    # compatibility perl script in zenity for something quite old, not packaged in fedora
    'gdialog',

    # An openembedded thing
    # "Tool that installs the GNU config.guess / config.sub into a directory tree"
    'gnu-configize',

    # GPG test program (https://git.gnupg.org/cgi-bin/gitweb.cgi?p=gnupg.git;a=tree;f=tests)
    'gpgscm',

    # An implementation of tar for cross-platform compatibility, disabled in gnupg2.spec
    'gpgtar',

    # Removed from gtk-doc
    # https://git.gnome.org/browse/gtk-doc/commit/?id=46df4354abed5724697fd5e39630c5bbc6637cc4
    'gtkdoc-mktmpl',

    # Versioned python-3.5 binaries
    'idle3.5', 'pydoc3.5', 'python3.5', 'python3.5-config', 'python3.5m',  'python3.5m-config', '2to3-3.5',

    # installed in openembedded with a coreutils suffix along with the more normal version
    'kill.coreutils', 'uptime.coreutils',

    # nettle utilities not currently packaged in fedora
    # (https://src.fedoraproject.org/rpms/nettle/c/2ec204e2de17006b566c9ff7d90ec65ca1680ed5?branch=master)
    'nettle-hash', 'nettle-lfib-stream', 'nettle-pbkdf2', 'pkcs1-conv', 'sexp-conv',

    # Not built by default as of util-linux-2.29
    '/usr/bin/pg',

    # These are installed as <name>-64 in Fedora, we just ignore them because they will be
    # pulled in by the corresponding library
    'gdk-pixbuf-query-loaders', 'gtk-query-immodules-2.0',
    'gio-querymodules', 'gtk-query-immodules-3.0',

    # Removed in krb5-1.13 (https://web.mit.edu/kerberos/krb5-1.13/README-1.13.5.txt)
    'krb5-send-pr',

    # Removed in util-linux-2.30'
    'tailf',

    # OpenEmbedded uses Debian's ca-certificates, Fedora is different
    'update-ca-certificates',

    #########################################################################
    # In the freedesktop runtime for some reason, doesn't seem useful
    'bsdcat',

    # Same as 'openssl rehash', but as a perl script (openssl-perl)
    'c_rehash',

    # From pulseaudio, wrapper script to start a pulseaudio server as if it was ESD (pulseaudio-esound-compat)
    'esdcompat',

    # Just need the library (gcab)
    'gcab',

    # Probably not useful in the runtime or the SDK (gstreamer-plugins-base-tools)
    'gst-device-monitor-1.0', 'gst-discoverer-1.0', 'gst-play-1.0',

    # Python utilities (python2-tools)
    'idle', 'smtpd.py',

    # Python3 utilities (python3-tools)
    'idle3', '2to3',

    # A binary from cups, we just need the libraries (cups-libs)
    'ipptool',

    # Minimal profiler (glibc-utils)
    'pcprofiledump',

    # (pcre-tools)
    'pcre2grep', 'pcre2test',

    # Random test program from libproxy (libproxy-bin)
    'proxy',

    # Tools from libvpx (libvpx-utils)
    'vpxdec', 'vpxenc',
]
ignore.update('/usr/bin/' + x for x in bin_ignore)

bin_rename = {
    # lcms2 compiled with --program-suffix=2 in Fedora, even though there are no actual
    # conflicts between lcms and lcms2 - jpegicc was renamed to jpgicc, etc.
    'jpgicc': 'jpgicc2',
    'linkicc': 'linkicc2',
    'psicc': 'psicc2',
    'tificc': 'tificc2',
    'transicc': 'transicc2',
}
rename.update({ '/usr/bin/' + k: '/usr/bin/' + v for k, v in bin_rename.items() })

lib_ignore = [
    # Symlink created in freedesktop.org flatpak runtime, not standard
    'libEGL_indirect.so.0',

    # Removed in gpgme-1.9.0
    'libgpgme-pthread.so.11',

    # Not enabled in fedora (consider fixing)
    'libharfbuzz-gobject.so.0',

    # Part of glibc
    'libssp.so.0',
]
ignore.update('/usr/lib64/' + x for x in lib_ignore)

fonts_ignore = {
    # Added in 2.36
    'dejavu/DejaVuMathTeXGyre.ttf',
}
ignore.update('/usr/share/fonts/' + x for x in fonts_ignore)

lib_rename = {
    # Newer in Fedora
    'libhunspell-1.3.so.0': 'libhunspell-1.5.so.0',
    'libwebp.so.6': 'libwebp.so.7',
    'libwebpmux.so.2': 'libwebpmux.so.3',
    'libpcre2-posix.so.1': 'libpcre2-posix.so.2',
    'libvpx.so.3': 'libvpx.so.4',
    'libkadm5clnt_mit.so.9': 'libkadm5clnt_mit.so.11',
    'libkadm5srv_mit.so.9': 'libkadm5srv_mit.so.11',

    # Newer in Flatpak runtime
    'libprocps.so.6': 'libprocps.so.4', # procps-3.10 vs. procps-3.12
    'libgif.so.7': 'libgif.so.4', # giflib 4 vs giflib-5 - https://bugzilla.redhat.com/show_bug.cgi?id=822844

    # Fedora arch-handling
    'ld-linux.so.2': 'ld-linux-x86-64.so.2',
}
rename.update({ '/usr/lib64/' + k: '/usr/lib64/' + v for k, v in lib_rename.items() })

include_ignore = {
    # https://git.gnome.org/browse/at-spi2-core/commit/?id=1eb223bb48464d707290ef540581e9763b0ceee8
    'at-spi-2.0/atspi/atspi-gmain.c',

    # Removed in 7.55 https://github.com/curl/curl/commit/73a2fcea0b4adea6ba342cd7ed1149782c214ae3
    'curl/curlbuild-64.h', 'curl/curlbuild.h', 'curl/curlrules.h',

    # Not enabled on Fedora
    'harfbuzz/hb-gobject-enums.h',
    'harfbuzz/hb-gobject-structs.h',
    'harfbuzz/hb-gobject.h',

    # https://github.com/hunspell/hunspell/commit/99675e791d123cbe1be914b1a49dd83062134301
    'hunspell/affentry.hxx', 'hunspell/affixmgr.hxx', 'hunspell/baseaffix.hxx', 'hunspell/dictmgr.hxx',
    'hunspell/filemgr.hxx','hunspell/hashmgr.hxx','hunspell/hunzip.hxx','hunspell/langnum.hxx',
    'hunspell/phonet.hxx','hunspell/replist.hxx','hunspell/suggestmgr.hxx',
}
ignore.update('/usr/include/' + x for x in include_ignore)

include_rename = {
    'assuan.h': 'libassuan2/assuan.h',
    'nss3/nssck.api': 'nss3/templates/nssck.api',
}
rename.update({ '/usr/include/' + k: '/usr/include/' + v for k, v in include_rename.items() })

nspr_include = [
    'nspr.h', 'plarena.h', 'plarenas.h', 'plbase64.h', 'plerror.h', 'plgetopt.h', 'plhash.h',
    'plstr.h', 'pratom.h', 'prbit.h', 'prclist.h', 'prcmon.h', 'prcountr.h', 'prcpucfg.h',
    'prcvar.h', 'prdtoa.h', 'prenv.h', 'prerr.h', 'prerror.h', 'prinet.h', 'prinit.h',
    'prinrval.h', 'prio.h', 'pripcsem.h', 'private/pprio.h', 'private/pprthred.h', 'private/prpriv.h',
    'prlink.h', 'prlock.h', 'prlog.h', 'prlong.h', 'prmem.h', 'prmon.h', 'prmwait.h', 'prnetdb.h',
    'prolock.h', 'prpdce.h', 'prprf.h', 'prproces.h', 'prrng.h', 'prrwlock.h', 'prshm.h', 'prshma.h',
    'prsystem.h', 'prthread.h', 'prtime.h', 'prtpool.h', 'prtrace.h', 'prtypes.h', 'prvrsion.h',
    'prwin16.h', 'stropts.h', 'obsolete/pralarm.h', 'obsolete/probslet.h', 'obsolete/protypes.h', 'obsolete/prsem.h'
]
rename.update({ '/usr/include/' + x: '/usr/include/nspr4/' + x for x in nspr_include })

pc_ignore = {
    # Not enabled on Fedora
    'harfbuzz-gobject.pc',

    # https://github.com/ostroproject/ostro-os/blob/master/meta/recipes-support/libassuan/libassuan/libassuan-add-pkgconfig-support.patch
    'libassuan.pc',

    # http://cgit.openembedded.org/openembedded-core/tree/meta/recipes-support/libgpg-error/libgpg-error/pkgconfig.patch
    'gpg-error.pc',

    # http://cgit.openembedded.org/openembedded-core/tree/meta/recipes-support/libgcrypt/files/0001-Add-and-use-pkg-config-for-libgcrypt-instead-of-conf.patch
    'libgcrypt.pc',
}
ignore.update('/usr/lib64/pkgconfig/' + x for x in pc_ignore)

pc_rename = {
    'python-3.5.pc': 'python-3.6.pc',
    'python-3.5m.pc': 'python-3.6m.pc',
}
rename.update({ '/usr/lib64/pkgconfig/' + k: '/usr/lib64/pkgconfig/' + v for k, v in pc_rename.items() })
rename.update({ '/usr/share/pkgconfig/' + k: '/usr/share/pkgconfig/' + v for k, v in pc_rename.items() })

ignore_patterns = [
    # Flatpak runtime has a versioned gawk-4.1.3
    r'/usr/bin/gawk-.*',

    # Architecture specific aliases for gcc, binutils, etc
    r'^/usr/bin/x86_64-unknown-linux-.*',

    # From NSPR, intentionally not installed on Fedora
    r'/usr/include/md/.*',

    # .install files litter the include directories of openembedded
    r'.*/\.install$'
]
ignore_compiled = [re.compile(x) for x in ignore_patterns]

rename_patterns = [
    (r'^/usr/include/c\+\+/6.2.0/(.*)', r'/usr/include/c++/7/\1'),
    (r'^/usr/include/c\+\+/7/x86_64-unknown-linux/(.*)', r'/usr/include/c++/7/x86_64-redhat-linux/\1'),
    (r'^/usr/lib64/pkgconfig/(.*proto.pc)', r'/usr/share/pkgconfig/\1'),
    (r'^/usr/share/fonts/liberation-fonts/(.*)', r'/usr/share/fonts/liberation/\1'),
]
rename_compiled = [(re.compile(a), b) for a, b in rename_patterns]

def package_cmp(a, b):
    if a.arch == 'i686' and b.arch != 'i686':
        return 1
    if a.arch != 'i686' and b.arch == 'i686':
        return -1
    c = - a.evr_cmp(b)
    if c < 0:
        return -1
    elif c == 0:
        return 0
    else:
        return 1

class Progress(dnf.callback.DownloadProgress):
    def __init__(self, name):
        self.name = name
        self.hashes = -1
    def start(self, total_files, total_size, total_drpms=0):
        pass
    def progress(self, payload, done):
        if payload.download_size == 0:
            return
        hashes = int(60 * done / payload.download_size)
        if hashes != self.hashes:
            hashline = "[" + "#" * hashes + " " * (60 - hashes) + "]"
            if self.hashes != -1:
                print("\r", end="")
            print("{} - {}k - {}".format(self.name, int(payload.download_size / 1024), hashline), end="")
            self.hashes = hashes
    def end(self, payload, status, message):
        if status == dnf.callback.STATUS_OK:
            print(" - DONE")
        else:
            print

class PackageInfo(object):
    def __init__(self):
        self.base = dnf.Base()

        self._add_repo(self.base, 'f27', metalink=REPO_F27)
        self._add_repo(self.base, 'f27-updates', metalink=REPO_F27_UPDATES)
        self._add_repo(self.base, 'f27-updates-testing', metalink=REPO_F27_UPDATES_TESTING)

        self.base.fill_sack(load_available_repos=True, load_system_repo=False)

    def _add_repo(self, base, reponame, repourl=None, metalink=None):
        repo = dnf.repo.Repo(reponame, self.base.conf)
        if repourl is not None:
            repo.baseurl = repourl
        elif metalink is not None:
            repo.metalink = metalink
        else:
            raise RuntimeError("Either baseurl or metalink must be specified")
        repo.set_progress_bar(Progress(reponame))
        repo.load()
        repo.enable()
        base.repos.add(repo)

    def repo_hash(self):
        h = hashlib.sha256()
        for r in sorted(self.base.repos.all(), key=lambda x: x.name):
            repomd_file = os.path.join(r._cachedir, 'repodata/repomd.xml')
            with open(repomd_file, 'rb') as f:
                h.update(f.read())
        return h.hexdigest()

if len(sys.argv) != 2:
    print("Usage: resolve-files.py INFILE", file=sys.stderr)
    sys.exit(1)

inpath = sys.argv[1]
if not inpath.endswith('.files'):
    print("INFILE must have .files suffix", file=sys.stderr)
    sys.exit(1)

base_path = inpath[:-len('.files')]

def warn(msg):
    print("{}: \033[31m{}\033[39m".format(inpath, msg), file=sys.stderr)

def start(msg):
    print("{}: \033[90m{} ... \033[39m".format(inpath, msg), file=sys.stderr, end="")
    sys.stderr.flush()

def done():
    print("\033[90mdone\033[39m", file=sys.stderr)

start("Reading file list")

to_resolve = []
with open(inpath) as f:
    for l in f:
        r = l.rstrip()
        if r.startswith('/usr/lib/'):
            r = '/usr/lib64/' + r[len('/usr/lib/'):]
        to_resolve.append(r)

to_resolve.sort()

done()

pkgs = PackageInfo()

files_map = None

# We need to look up a lot of file dependencies. dnf/libsolv is not fast at doing
# this (at least when we look up files one-by-one) so we create a hash table that
# maps from *all* files in the distribution to the "best" package that provides
# the file. To further speed this up, we pickle the result and store it, and only
# recreate it when the DNF metadata changes. We gzip the pickle to save space
# (70M instead of 700M), this slows things down by about 2 seconds.
#
repo_hash = pkgs.repo_hash()
f = None
try:
    f = gzip.open('cache/files.map.gz', 'rb')
    with f:
        old_repo_hash = f.read(64).decode('utf-8')
        if old_repo_hash == repo_hash:
            start("Reading cached file map")
            files_map = pickle.load(f)
            done()
except FileNotFoundError:
    pass
except (pickle.UnpicklingError, EOFError) as e:
    done()
    warn("Failed to load cache/files.map.gz:", e)

if files_map is None:
    start("Creating file map")
    files_map = {}
    for p in pkgs.base.sack.query().filter():
        for f in p.files:
            old = files_map.get(f, None)
            if old is None or package_cmp(p, old) < 0:
                files_map[f] = p

    for k, v in files_map.items():
        files_map[k] = v.name
    done()

    start("Writing file map to cache")
    with gzip.open('cache/files.map.gz', 'wb') as f:
        f.write(repo_hash.encode('utf-8'))
        pickle.dump(files_map, f)
    done()

found_packages = set()

start("Resolving files to packages")

matched_file = open(base_path + '.matched', 'w')
unmatched_file = open(base_path + '.unmatched', 'w')
unmatched_count = 0

for r in to_resolve:
    if r in ignore:
        continue

    skip = False
    for p in ignore_compiled:
        if p.match(r) is not None:
            skip = True
    if skip:
        continue

    if r in rename:
        r = rename[r]

    for p, replacement in rename_compiled:
        if p.match(r) is not None:
            r = p.sub(replacement, r)

    if r.startswith('/usr/lib64/'):
        search = [r, '/lib64/' + os.path.basename(r)]
    elif r.startswith('/usr/bin/'):
        search = [r, '/bin/' + os.path.basename(r), '/usr/sbin/' + os.path.basename(r), '/sbin/' + os.path.basename(r)]
    else:
        search = [r]

    if r.startswith('/usr/lib64/libLLVM'):
        # freedesktop SDK builds "split" LLVM libraries
        found_packages.add('llvm-libs')
        continue

    for s in search:
        providing = files_map.get(s, None)
        if providing is not None:
            break

    if providing is None:
        print(r, file=unmatched_file)
        unmatched_count += 1
    else:
        found_packages.add(providing)
        print("{}: {}".format(r, providing), file=matched_file)

unmatched_file.close()
matched_file.close()

with open(base_path + '.packages', 'w') as f:
    for p in sorted(found_packages):
        print(p, file=f)

done()

if unmatched_count > 0:
    warn("{} unmatched files, see {}".format(unmatched_count, base_path + ".unmatched"))
