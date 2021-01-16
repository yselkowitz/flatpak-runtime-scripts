#!/usr/bin/python3

import os
import re
import sys

import util
from util import start, done, warn

if len(sys.argv) != 2:
    print("Usage: resolve-files.py INFILE", file=sys.stderr)
    sys.exit(1)

inpath = sys.argv[1]
if not inpath.endswith('.files'):
    print("INFILE must have .files suffix", file=sys.stderr)
    sys.exit(1)

util.set_log_name(inpath)

base_path = inpath[:-len('.files')]
is_platform = "-Platform" in base_path
is_sdk = "-Sdk" in base_path

############################################################

ignore = set()
rename = dict()

bin_ignore = [
    # /usr/share/doc/aspell/aspell-import in Fedora
    'aspell-import',

    # Part of dbus-x11, pulls in a pile of X11 stuff
    'dbus-launch',

    # fcitx is not our input method
    'fcitx', 'fcitx-autostart', 'fcitx-configtool', 'fcitx-dbus-watcher', 'fcitx-diagnose', 'fcitx-remote', 'fcitx4-config',
    'createPYMB', 'mb2org', 'mb2txt', 'readPYBase', 'readPYMB', 'scel2org', 'txt2mb',

    # compatibility perl script in zenity for something quite old, not packaged in fedora
    'gdialog',

    # GPG test program (https://git.gnupg.org/cgi-bin/gitweb.cgi?p=gnupg.git;a=tree;f=tests)
    'gpgscm',

    # An implementation of tar for cross-platform compatibility, disabled in gnupg2.spec
    'gpgtar',

    # Versioned python-3.8 binaries
    'pydoc3.8', 'python3.8', 'python3.8-config', 'python3.8m',  'python3.8m-config', '2to3-3.8',
    'easy_install-3.8', 'pip3.8', 'pyvenv-3.8',

    # nettle utilities not currently packaged in fedora
    # (https://src.fedoraproject.org/rpms/nettle/c/2ec204e2de17006b566c9ff7d90ec65ca1680ed5?branch=master)
    'nettle-hash', 'nettle-lfib-stream', 'nettle-pbkdf2', 'pkcs1-conv', 'sexp-conv',

    # These are installed as <name>-64 in Fedora, we just ignore them because they will be
    # pulled in by the corresponding library
    'gdk-pixbuf-query-loaders', 'gtk-query-immodules-2.0',
    'gio-querymodules', 'gtk-query-immodules-3.0',

    # Removed in krb5-1.13 (https://web.mit.edu/kerberos/krb5-1.13/README-1.13.5.txt)
    'krb5-send-pr',

    # OpenEmbedded uses Debian's ca-certificates, Fedora is different
    'update-ca-certificates',

    #########################################################################
    'aomdec', 'aomenc',

    # In the freedesktop runtime for some reason, doesn't seem useful
    'bsdcat',

    # built out of libarchive, doesn't seem useful to have in the runtime
    'bsdcpio',

    # just want cyrus-sasl-libs
    'pluginviewer', 'saslauthd', 'sasldblistusers2', 'saslpasswd2', 'testsaslauthd',

    # cups-printerapp - just want cups-libs
    'ippeveprinter',

    # just want libdav1d
    'dav1d',

    # From pulseaudio, wrapper script to start a pulseaudio server as if it was ESD (pulseaudio-esound-compat)
    'esdcompat',

    # flac - jut want the library
    'flac', 'metaflac',

    # flex??
    'flex', 'flex++',

    # Just need the library (gcab)
    'gcab',

    # giflib-utils
    'gif2rgb', 'gifbuild', 'gifclrmp', 'gifecho',
    'giffix', 'gifinto', 'giftext', 'giftool',

    # gitk
    'gitk',

    # gnutls-utils
    'certtool', 'gnutls-cli', 'gnutls-cli-debug',
    'gnutls-serv', 'ocsptool',
    'p11tool', 'psktool', 'srptool',

    # Probably not useful in the runtime or the SDK (gstreamer-plugins-base-tools)
    'gst-device-monitor-1.0', 'gst-discoverer-1.0', 'gst-play-1.0',

    # krb5-server
    'kadmin.local', 'kadmind', 'kdb5_util', 'kprop', 'kpropd', 'kproplog', 'krb5kdc',
    'sclient', 'sserver',

    # Just need the ibus libraries and input methods
    'ibus', 'ibus-daemon', 'ibus-setup',

    # A binary from cups, we just need the libraries (cups-libs)
    'ipptool',

    # glibc-utils
    'mtrace', 'pcprofiledump', 'xtrace',

    # libidn2
    'idn2',

    # libtasn1-tools
    'asn1Coding', 'asn1Decoding', 'asn1Parser',

    # lame
    'lame',

    # openssh
    'ssh-keygen',

    # openssh-clients
    'scp', 'sftp', 'ssh', 'ssh-add', 'ssh-agent', 'ssh-keyscan',

    # openssl
    'openssl',

    # (pcre-tools)
    'pcregrep', 'pcretest',
    'pcre2grep', 'pcre2test',

    #pulseaudio-utils
    'pacat', 'pacmd', 'pactl', 'padsp', 'pamon',
    'paplay', 'parec', 'parecord', 'pax11publish',

    # pipewire-utils
    'pw-cat', 'pw-cli', 'pw-dot', 'pw-dump', 'pw-metadata', 'pw-mididump', 'pw-midiplay', 'pw-midirecord', 'pw-mon', 'pw-play', 'pw-profiler', 'pw-record', 'pw-reserve',
    'spa-acp-tool', 'spa-inspect', 'spa-monitor', 'spa-resample',

    # libsndfile-utils
    'sndfile-cmp', 'sndfile-concat', 'sndfile-convert', 'sndfile-deinterleave',
    'sndfile-info', 'sndfile-interleave', 'sndfile-metadata-get', 'sndfile-metadata-set',
    'sndfile-play', 'sndfile-salvage',

    # speex-tools
    'speexdec', 'speexenc',

    # 'libtiff-tools
    'fax2ps', 'fax2tiff', 'pal2rgb', 'ppm2tiff', 'raw2tiff', 'tiff2bw', 'tiff2pdf', 'tiff2ps', 'tiff2rgba',
    'tiffcmp', 'tiffcp', 'tiffcrop', 'tiffdither', 'tiffdump', 'tiffinfo', 'tiffmedian', 'tiffset', 'tiffsplit',

    # Random test program from libproxy (libproxy-bin)
    'proxy',

    # Tools from libvpx (libvpx-utils)
    'vpxdec', 'vpxenc',

    ##############

    # texinfo-tex
    'pdftexi2dvi', 'texi2dvi', 'texi2pdf', 'texindex',
]
ignore.update('/usr/bin/' + x for x in bin_ignore)

# development tools in the freedesktop runtime
platform_bin_ignore = [
    'fftw-wisdom', 'fftw-wisdom-to-conf',
    'make',
    'm4',
    'orcc',
    'yelp-build', 'yelp-check', 'yelp-new',
]
if is_platform:
    ignore.update('/usr/bin/' + x for x in platform_bin_ignore)

bin_rename = {
    'clang-10': 'clang',
    # lcms2 compiled with --program-suffix=2 in Fedora, even though there are no actual
    # conflicts between lcms and lcms2 - jpegicc was renamed to jpgicc, etc.
    'jpgicc': 'jpgicc2',
    'linkicc': 'linkicc2',
    'psicc': 'psicc2',
    'tificc': 'tificc2',
    'transicc': 'transicc2',
    'vala-0.50': 'vala-0.48',
    'vala-gen-introspect-0.50': 'vala-gen-introspect-0.48',
    'valac-0.50': 'valac-0.48',
    'vapigen-0.50': 'vapigen-0.48',
}
rename.update({ '/usr/bin/' + k: '/usr/bin/' + v for k, v in bin_rename.items() })

lib_ignore = [
    # Symlink created in freedesktop.org flatpak runtime, not standard
    'libEGL_indirect.so.0',

    # Part of glibc
    'libssp.so.0',
]
ignore.update('/usr/lib64/' + x for x in lib_ignore)

lib_rename = {
    # Newer in Fedora
    'libaom.so.0': 'libaom.so.2',
    'libasan.so.5': 'libasan.so.6',
    'libclang-cpp.so.10': 'libclang-cpp.so.11',
    'libclang.so.10': 'libclang.so.11',
    'libdav1d.so.2': 'libdav1d.so.4',
    'libgettextlib-0.20.2.so': 'libgettextlib-0.21.so',
    'libgettextsrc-0.20.2.so': 'libgettextsrc-0.21.so',
    'libkadm5clnt_mit.so.11': 'libkadm5clnt_mit.so.12',
    'libkadm5srv_mit.so.11': 'libkadm5srv_mit.so.12',
    'libkdb5.so.9': 'libkdb5.so.10',
    'libLLVM-10.so': 'libLLVM-11.so',
    'libLTO.so.10': 'libLTO.so.11',
    'libprocps.so.7': 'libprocps.so.8',
    'libpython3.8.so': 'libpython3.9.so',
    'libRemarks.so.10': 'libRemarks.so.11',
    'libverto.so.0': 'libverto.so.1',

    # Older in Fedora
    'libffi.so.7': 'libffi.so.6',
    'libvala-0.50.so': 'libvala-0.48.so',
    'libvala-0.50.so.0': 'libvala-0.48.so.0',

    # Replaced by libxcrypt in Fedora
    'libcrypt-2.31.so': 'libcrypt.so.2',

    # Compat symlink in gcr
    'libgcr-3.so.1': 'libgcr-ui-3.so.1',

    # Fedora arch-handling
    'ld-linux.so.2': 'ld-linux-x86-64.so.2',
}
rename.update({ '/usr/lib64/' + k: '/usr/lib64/' + v for k, v in lib_rename.items() })

for old in ['libasm-0.180.so', 'libdw-0.180.so', 'libelf-0.180.so']:
    rename['/usr/lib64/' + old] = '/usr/lib64/' + old.replace('-0.180', '-0.182')

# Fedora has newer glibc
for old in ['ld-2.31.so', 'libBrokenLocale-2.31.so', 'libanl-2.31.so', 'libc-2.31.so',
            'libdl-2.31.so', 'libm-2.31.so',
            'libmvec-2.31.so', 'libnsl-2.31.so', 'libnss_compat-2.31.so',
            'libnss_db-2.31.so', 'libnss_dns-2.31.so', 'libnss_files-2.31.so',
            'libnss_hesiod-2.31.so', 'libpthread-2.31.so', 'libresolv-2.31.so',
            'librt-2.31.so', 'libutil-2.31.so']:
    rename['/usr/lib64/' + old] = '/usr/lib64/' + old.replace('-2.31', '-2.32')

# Fedora has newer icu
for old in ['libicudata.so.64', 'libicui18n.so.64', 'libicuio.so.64', 'libicutest.so.64',
            'libicutu.so.64', 'libicuuc.so.64']:
    rename['/usr/lib64/' + old] = '/usr/lib64/' + old.replace('so.64', 'so.67')

include_rename = {
    'assuan.h': 'libassuan2/assuan.h',
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

# These four plugins in the freedesktop runtime pull in gstreamer-plugins-bad-extras, which
# in turn pulls in a lot more dependencies. If they are useful, they should be moved
# to gstreamer-plugins-extras.
gstreamer_plugins_ignore = {
    'libgstcurl.so', 'libgstdecklink.so', 'libgstopenal.so', 'libgstvdpau.so'
}
ignore.update('/usr/lib64/gstreamer-1.0/' + x for x in gstreamer_plugins_ignore)

pc_ignore = {
    # Not enabled on Fedora
    'harfbuzz-gobject.pc',

    # https://github.com/ostroproject/ostro-os/blob/master/meta/recipes-support/libassuan/libassuan/libassuan-add-pkgconfig-support.patch
    'libassuan.pc',

    # http://cgit.openembedded.org/openembedded-core/tree/meta/recipes-support/libgcrypt/files/0001-Add-and-use-pkg-config-for-libgcrypt-instead-of-conf.patch
    'libgcrypt.pc',
}
ignore.update('/usr/lib64/pkgconfig/' + x for x in pc_ignore)

pc_rename = {
    'libvala-0.50.pc': 'libvala-0.48.pc',
    'python-3.8.pc': 'python-3.9.pc',
    'python-3.8-embed.pc': 'python-3.9-embed.pc',
    'ruby-2.7.pc': 'ruby.pc',
    'vapigen-0.50.pc': 'vapigen-0.48.pc',
}
rename.update({ '/usr/lib64/pkgconfig/' + k: '/usr/lib64/pkgconfig/' + v for k, v in pc_rename.items() })
rename.update({ '/usr/share/pkgconfig/' + k: '/usr/share/pkgconfig/' + v for k, v in pc_rename.items() })

ignore_patterns = [
    # Flatpak runtime has a versioned gawk-5.0.1
    r'/usr/bin/gawk-.*',

    # Architecture specific aliases for gcc, binutils, etc
    r'^/usr/bin/x86_64-unknown-linux-.*',

    # From NSPR, intentionally not installed on Fedora
    r'/usr/include/md/.*',

    # Windows binaries?
    r'/usr/lib64/python3.8/site-packages/setuptools/.*.exe',

    # differences in pip packaging - unbundling
    r'^/usr/lib64/python3.8/site-packages/pip/_internal/.*',
    r'^/usr/lib64/python3.8/site-packages/pip/_vendor/.*',

    # Let the python files pull in the packages, avoid versioned directory names
    r'^/usr/lib64/python3.8/site-packages/[^/]*.dist-info/.*',
    r'^/usr/lib64/python3.8/site-packages/[^/]*.egg-info/.*',

    # fcitx
    r'/usr/lib64/libfcitx.*',

    # .install files litter the include directories of openembedded
    r'.*/\.install$',

    # .la files
    r'.*\.la$',

    # .pyc files shouldn't affect what is needed
    r'.*\.pyc$',

    # Font ID files for fontconfig
    r'/usr/share/fonts(|/.*)/.*\.uuid',

    # We build these into the gtk+ library
    r'^/usr/lib64/gtk-[^/]*/[^/]*/immodules/im-wayland.so',
    r'^/usr/lib64/gtk-[^/]*/[^/]*/immodules/im-waylandgtk.so',
]
ignore_compiled = [re.compile(x) for x in ignore_patterns]

rename_patterns = [
    (r'^/usr/include/c\+\+/10.2.0/(.*)', r'/usr/include/c++/10/\1'),
    (r'^/usr/include/c\+\+/10/x86_64-unknown-linux-gnu/(.*)', r'/usr/include/c++/10/x86_64-redhat-linux/\1'),
    (r'^/usr/include/nss/(.*)', r'/usr/include/nss3/\1'),
    (r'^/usr/include/python3.8/(.*)', r'/usr/include/python3.9/\1'),
    (r'^/usr/include/ruby-2.7.0/ruby/(.*)', r'/usr/include/ruby/\1'),
    (r'^/usr/include/ruby-2.7.0/x86_64-linux/ruby/(.*)', r'/usr/include/ruby/\1'),
    (r'^/usr/include/ruby-2.7.0/(.*)', r'/usr/include/ruby/\1'),
    (r'^/usr/lib64/pkgconfig/(.*proto.pc)', r'/usr/share/pkgconfig/\1'),
    (r'^/usr/lib64/python3.8/(.*)', r'/usr/lib64/python3.9/\1'),
    (r'^/usr/share/fonts/dejavu/(DejaVuSansMono.*)', r'/usr/share/fonts/dejavu-sans-mono-fonts/\1'),
    (r'^/usr/share/fonts/dejavu/(DejaVuSans.*)', r'/usr/share/fonts/dejavu-sans-fonts/\1'),
    (r'^/usr/share/fonts/dejavu/(DejaVuMath.*)', r'/usr/share/fonts/dejavu-serif-fonts/\1'),
    (r'^/usr/share/fonts/dejavu/(DejaVuSerif.*)', r'/usr/share/fonts/dejavu-serif-fonts/\1'),
    (r'^/usr/share/fonts/google-crosextra-caladea/(Caladea.*).ttf', r'/usr/share/fonts/ht-caladea-fonts/\1.otf'),
    (r'^/usr/share/fonts/google-crosextra-carlito/(Carlito.*)', r'/usr/share/fonts/google-carlito-fonts/\1'),
    (r'^/usr/share/fonts/liberation-fonts/(LiberationMono.*)', r'/usr/share/fonts/liberation-mono/\1'),
    (r'^/usr/share/fonts/liberation-fonts/(LiberationSans.*)', r'/usr/share/fonts/liberation-sans/\1'),
    (r'^/usr/share/fonts/liberation-fonts/(LiberationSerif.*)', r'/usr/share/fonts/liberation-serif/\1'),
    (r'^/usr/share/fonts/adobe-source-code-pro-fonts/(.*)', r'/usr/share/fonts/adobe-source-code-pro/\1'),
]
rename_compiled = [(re.compile(a), b) for a, b in rename_patterns]

global_package_ignore_patterns = [
    # The Fedora packages of fcitx pull in qt4. While would be nice to match the upstream
    # runtime in including fcitx for full compatiblity when the host is using fcitx,
    # it doesn't seem worth the increase in runtime size.
    '^fcitx-.*$',

    # Should be installed on the host instead
    '^jack-audio-connection-kit$',
    '^pipewire$',
    '^pulseaudio$',
    '^tracker3$',
    '^v4l-utils$',
    '^v4l-utils-devel-tools$',
    '^xdg-desktop-portal$',
    '^xdg-desktop-portal-devel$',
]
global_package_ignore_compiled = [re.compile(p) for p in global_package_ignore_patterns]

platform_package_ignore_patterns = [
    "^.*-devel$",
    "^libappstream-glib-builder$", # may not need in the sdk either
    "^gcc-gdb-plugin$", # pulls in gcc
    "^gtk-doc$",
    "^icu$", # may not need in the sdk either
    '^llvm$',
    '^llvm-test$', # pulls in gcc and binutils
    '^sqlite$',
]
platform_package_ignore_compiled = [re.compile(p) for p in platform_package_ignore_patterns]


# We need to look up a lot of file dependencies. dnf/libsolv is not fast at doing
# this (at least when we look up files one-by-one) so we create a hash table that
# maps from *all* files in the distribution to the "best" package that provides
# the file. To further speed this up, we pickle the result and store it, and only
# recreate it when the DNF metadata changes. We gzip the pickle to save space
# (70M instead of 700M), this slows things down by about 2 seconds.
#
def make_files_map(repo_info):
    files_map = {}

    def cb(package_info, f):
        old = files_map.get(f)
        if old is None or util.package_cmp(package_info, old) < 0:
            files_map[f] = package_info

    util.foreach_file(repo_info, cb)

    start("Finalizing files map")
    for k in files_map:
        files_map[k] = files_map[k][0]
    done()

    return files_map

def get_files_map():
    return util.get_repo_cacheable('files-map', make_files_map)

start("Reading file list")

to_resolve = []
with open(inpath) as f:
    for l in f:
        r = l.rstrip()
        if r.startswith('/usr/lib/x86_64-linux-gnu/'):
            r = '/usr/lib64/' + r[len('/usr/lib/x86_64-linux-gnu/'):]
        elif r.startswith('/usr/lib/'):
            r = '/usr/lib64/' + r[len('/usr/lib/'):]
        to_resolve.append(r)

to_resolve.sort()

done()

files_map = get_files_map()
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

    if os.path.dirname(r) == '/usr/lib64':
        search = [r, '/lib64/' + os.path.basename(r)]
    elif r.startswith('/usr/lib64') and r.find('/site-packages/') > 0:
        # Python packages can be either in /usr/lib64 or /usr/lib
        search = [r, '/usr/lib/' + r[len('/usr/lib64/'):]]
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
        if any(p.match(providing) is not None for p in global_package_ignore_compiled):
            continue

        if is_platform and any(p.match(providing) is not None for p in platform_package_ignore_compiled):
            continue

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
