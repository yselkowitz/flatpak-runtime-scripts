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

    # libjpeg-turbo utilities not packaged in Fedora
    'tjbench',

    # libselinux utilities not packaged in Fedora
    'compute_av', 'compute_create', 'compute_member', 'compute_relabel', 'getfilecon',
    'getpidcon', 'getseuser', 'policyvers', 'selinux_check_securetty_context',
    'setfilecon', 'togglesebool',

    # Versioned python-3.10 binaries
    'pydoc3.10', 'python3.10', 'python3.10-config', 'python3.10m',  'python3.10m-config', '2to3-3.10',
    'easy_install-3.10', 'pip3.10', 'pyvenv-3.10',

    # nettle utilities not currently packaged in fedora
    # (https://src.fedoraproject.org/rpms/nettle/c/2ec204e2de17006b566c9ff7d90ec65ca1680ed5?branch=master)
    'nettle-hash', 'nettle-lfib-stream', 'nettle-pbkdf2', 'pkcs1-conv', 'sexp-conv',

    # These are installed as <name>-64 in Fedora, we just ignore them because they will be
    # pulled in by the corresponding library
    'gdk-pixbuf-query-loaders', 'gtk-query-immodules-2.0',
    'gio-querymodules', 'gtk-query-immodules-3.0',

    # krb5 sample utilities not packaged in Fedora
    'gss-client', 'gss-server', 'krb5-send-pr', 'sim_client', 'sim_server',
    'uuclient', 'uuserver',

    # OpenEmbedded uses Debian's ca-certificates, Fedora is different
    'update-ca-certificates',

    #########################################################################
    'aomdec', 'aomenc',

    # audit, audisp-plugins
    'aulast', 'aulastlog', 'ausyscall', 'auvirt', 'auditctl', 'auditd',
    'augenrules', 'aureport', 'ausearch', 'autrace', 'audisp-remote',
    'audisp-statsd', 'audisp-syslog',

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

    # Probably not useful in the runtime or the SDK (gstreamer1-*)
    'gst-device-monitor-1.0', 'gst-discoverer-1.0', 'gst-play-1.0',
    'gst-tester-1.0', 'playout',

    # krb5-server
    'kadmin.local', 'kadmind', 'kdb5_util', 'kprop', 'kpropd', 'kproplog', 'krb5kdc',
    'sclient', 'sserver',

    # Just need the ibus libraries and input methods
    'ibus', 'ibus-daemon', 'ibus-setup',

    # A binary from cups, we just need the libraries (cups-libs)
    'ipptool',

    # glibc-utils
    'mtrace', 'nscd', 'pcprofiledump', 'sln', 'trace', 'xtrace',

    # libcap-ng-utils
    'captest', 'filecap', 'netcap', 'pscap',

    # libidn2
    'idn2',

    # libtasn1-tools
    'asn1Coding', 'asn1Decoding', 'asn1Parser',

    # lame
    'lame',

    # nss unsupported or unpackaged tools
    'hw-support', 'nss', 'pwdecrypt', 'shlibsign', 'signtool', 'symkeyutil', 'validation',

    # openjpeg2-tools (renamed opj2_* in Fedora)
    'opj_compress', 'opj_decompress', 'opj_dump',

    # openssl
    'openssl',

    # (pcre-tools)
    'pcregrep', 'pcretest',
    'pcre2grep', 'pcre2test',

    #pulseaudio-utils
    'pacat', 'pacmd', 'pactl', 'padsp', 'pamon',
    'paplay', 'parec', 'parecord', 'pax11publish',

    # pipewire-utils
    'pw-cat', 'pw-cli', 'pw-config', 'pw-dot', 'pw-dsdplay', 'pw-dump', 'pw-encplay', 'pw-link', 'pw-loopback', 'pw-metadata', 'pw-mididump', 'pw-midiplay', 'pw-midirecord', 'pw-mon', 'pw-play', 'pw-profiler', 'pw-record', 'pw-reserve', 'pw-top',
    'spa-acp-tool', 'spa-inspect', 'spa-json-dump', 'spa-monitor', 'spa-resample',

    # pipewire-pulseaudio should only be installed on the host
    'pipewire-pulse',

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

    # golang-github-pierrec-lz4
    'lz4c',

    # specific to community SDKs
    'freedesktop-sdk-stripper',

    'gtksourceview5-widget'
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
    # bzip2
    'bzfless': 'bzless',

    # clang
    'clang-10': 'clang',

    # libselinux-utils
    'getconlist': 'selinuxconlist',
    'getdefaultcon': 'selinuxdefcon',

    # perl
    'perl5.32.0': 'perl',

    # procps-ng
    'pwait': 'pidwait',

    # vala
    'vala-0.52': 'vala-0.56',
    'vala-gen-introspect-0.52': 'vala-gen-introspect-0.56',
    'valac-0.52': 'valac-0.56',
    'vapigen-0.52': 'vapigen-0.56',
}
rename.update({ '/usr/bin/' + k: '/usr/bin/' + v for k, v in bin_rename.items() })

lib_ignore = [
    # Symlink created in freedesktop.org flatpak runtime, not standard
    'libEGL_indirect.so.0',
    'load-p11-kit-trust.so',

    # From AppArmor; Fedora/RHEL use SELinux instead
    'libapparmor.so', 'libapparmor.so.1',

    # binutils internal libraries
    'libbfd-2.38.so', 'libopcodes-2.38.so',

    # Trimmed from gettext(-devel)
    'libgettextlib.so', 'libgettextsrc.so', 'libtextstyle.so', 'libtextstyle.so.0',

    # Part of glibc
    'libc_malloc_debug.so', 'libssp.so.0',

    # glslang is built as static libraries only
    'libHLSL.so', 'libSPIRV.so', 'libSPVRemapper.so', 'libglslang-default-resource-limits.so',
    'libglslang.so.11', 'libglslang.so',

    # Disabled in libunwind
    'libunwind-ptrace.so', 'libunwind-ptrace.so.0',
    'libunwind-setjmp.so', 'libunwind-setjmp.so.0',
]
ignore.update('/usr/lib64/' + x for x in lib_ignore)

lib_rename = {
    # Newer in Fedora
    'libaom.so.2': 'libaom.so.3',
    'libasan.so.6': 'libasan.so.8',
    'libavcodec.so.59': 'libavcodec.so.60',
    'libavdevice.so.59': 'libavdevice.so.60',
    'libavfilter.so.8': 'libavfilter.so.9',
    'libavformat.so.59': 'libavformat.so.60',
    'libavutil.so.57': 'libavutil.so.58',
    'libclang-cpp.so.10': 'libclang-cpp.so.14',
    'libclang.so.10': 'libclang.so.14',
    'libdav1d.so.5': 'libdav1d.so.6',
    'libffi.so.7': 'libffi.so.8',
    'libFLAC++.so.6': 'libFLAC++.so.10',
    'libFLAC.so.8': 'libFLAC.so.12',
    'libgettextlib-0.21.so': 'libgettextlib-0.21.1.so',
    'libgettextsrc-0.21.so': 'libgettextsrc-0.21.1.so',
    'libgnutlsxx.so.28': 'libgnutlsxx.so.30',
    'libjavascriptcoregtk-5.0.so': 'libjavascriptcoregtk-6.0.so',
    'libjavascriptcoregtk-5.0.so.0': 'libjavascriptcoregtk-6.0.so.1',
    'libkadm5clnt_mit.so.11': 'libkadm5clnt_mit.so.12',
    'libkadm5srv_mit.so.11': 'libkadm5srv_mit.so.12',
    'libkdb5.so.9': 'libkdb5.so.10',
    'libLLVM-10.so': 'libLLVM-14.so',
    'libLTO.so.10': 'libLTO.so.14',
    'libonig.so.4': 'libonig.so.5',
    'libopenh264.so.5': 'libopenh264.so.7',
    'libopenh264.so.6': 'libopenh264.so.7',
    'libpcre2-posix.so.2': 'libpcre2-posix.so.3',
    'libprocps.so.7': 'libprocps.so.8',
    'libpython3.10.so': 'libpython3.11.so',
    'libRemarks.so.10': 'libRemarks.so.14',
    'libsepol.so.1': 'libsepol.so.2',
    'libswscale.so.6': 'libswscale.so.7',
    'libtinfow.so': 'libtinfo.so',
    'libtinfow.so.6': 'libtinfo.so.6',
    'libunistring.so.2': 'libunistring.so.5',
    'libvala-0.52.so': 'libvala-0.56.so',
    'libvala-0.52.so.0': 'libvala-0.56.so.0',
    'libverto.so.0': 'libverto.so.1',
    'libvpx.so.7': 'libvpx.so.8',
    'libwebkit2gtk-5.0.so': 'libwebkitgtk-6.0.so',
    'libwebkit2gtk-5.0.so.0': 'libwebkitgtk-6.0.so.4',

    # Replaced by libxcrypt in Fedora
    'libcrypt-2.33.so': 'libcrypt.so.2',

    # Compat symlink in gcr
    'libgcr-3.so.1': 'libgcr-ui-3.so.1',

    # Fedora arch-handling
    'ld-linux.so.2': 'ld-linux-x86-64.so.2',
}
rename.update({ '/usr/lib64/' + k: '/usr/lib64/' + v for k, v in lib_rename.items() })

gcc_libs = [
    'libasan.so', 'libatomic.so', 'libgcc_s.so', 'libgfortran.so', 'libgomp.so',
    'libitm.so', 'liblsan.so', 'libquadmath.so', 'libstdc++.so', 'libtsan.so',
    'libubsan.so'
]
rename.update({ '/usr/lib64/' + x: '/usr/lib/gcc/x86_64-redhat-linux/13/' + x for x in gcc_libs })

for old in ['libasm-0.187.so', 'libdw-0.187.so', 'libelf-0.187.so', 'libdebuginfod-0.187.so']:
    rename['/usr/lib64/' + old] = '/usr/lib64/' + old.replace('-0.187', '-0.189')

# Fedora has newer glibc
for old in ['ld-2.33.so', 'libBrokenLocale-2.33.so', 'libanl-2.33.so', 'libc-2.33.so',
            'libdl-2.33.so', 'libm-2.33.so',
            'libmvec-2.33.so', 'libnsl-2.33.so', 'libnss_compat-2.33.so',
            'libnss_db-2.33.so', 'libnss_dns-2.33.so', 'libnss_files-2.33.so',
            'libnss_hesiod-2.33.so', 'libpthread-2.33.so', 'libresolv-2.33.so',
            'librt-2.33.so', 'libutil-2.33.so']:
    rename['/usr/lib64/' + old] = '/usr/lib64/' + old.replace('-2.33', '')

# Fedora has newer icu
for old in ['libicudata.so.71', 'libicui18n.so.71', 'libicuio.so.71', 'libicutest.so.71',
            'libicutu.so.71', 'libicuuc.so.71']:
    rename['/usr/lib64/' + old] = '/usr/lib64/' + old.replace('so.71', 'so.72')

include_rename = {
    'asoundlib.h': 'alsa/asoundlib.h',
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

# pipewire jack libraries are installed in a non-standard path
jack_libraries = [
    'libjack.so', 'libjacknet.so', 'libjackserver.so'
]
rename.update({ '/usr/lib64/' + x: '/usr/lib64/pipewire-0.3/jack/' + x for x in jack_libraries })

# These plugins in the freedesktop runtime pull in gstreamer-plugins-bad-free-extras, which
# in turn pulls in a lot more dependencies. If they are useful, they should be moved
# to gstreamer-plugins-bad-free.
gstreamer_plugins_ignore = {
    'libgstaom.so', 'libgstcurl.so', 'libgstdecklink.so', 'libgstladspa.so',
    'libgstopenal.so', 'libgstva.so'
}
ignore.update('/usr/lib64/gstreamer-1.0/' + x for x in gstreamer_plugins_ignore)

pc_ignore = {
    # Trimmed from xorg-x11-proto-devel (xorgproto)
    'applewmproto.pc',

    # From AppArmor; Fedora/RHEL use SELinux instead
    'libapparmor.pc',

    # https://github.com/ostroproject/ostro-os/blob/master/meta/recipes-support/libassuan/libassuan/libassuan-add-pkgconfig-support.patch
    'libassuan.pc',

    # http://cgit.openembedded.org/openembedded-core/tree/meta/recipes-support/libgcrypt/files/0001-Add-and-use-pkg-config-for-libgcrypt-instead-of-conf.patch
    'libgcrypt.pc',

    # Disabled in libunwind
    'libunwind-setjmp.pc',

    # ncurses is built with a single tinfo library for both narrow and wide
    'tinfow.pc'
}
ignore.update('/usr/lib64/pkgconfig/' + x for x in pc_ignore)
ignore.update('/usr/share/pkgconfig/' + x for x in pc_ignore)

pc_rename = {
    'libvala-0.52.pc': 'libvala-0.56.pc',
    'python-3.10.pc': 'python-3.11.pc',
    'python-3.10-embed.pc': 'python-3.11-embed.pc',
    'vapigen-0.52.pc': 'vapigen-0.56.pc',
}
rename.update({ '/usr/lib64/pkgconfig/' + k: '/usr/lib64/pkgconfig/' + v for k, v in pc_rename.items() })
rename.update({ '/usr/share/pkgconfig/' + k: '/usr/share/pkgconfig/' + v for k, v in pc_rename.items() })

hunspell_ignore = {
   # regionless symlinks, correctly detected by full xx_XX name
   'gl.aff', 'gl.dic', 'is.aff', 'is.dic', 'te.aff', 'te.dic', 'tr.aff', 'tr.dic',
}
ignore.update('/usr/share/hunspell/' + x for x in hunspell_ignore)

hyph_ignore = {
   # regionless symlinks, correctly detected by full xx_XX name
   'hyph_de.dic', 'hyph_gl.dic', 'hyph_is.dic', 'hyph_te.dic',
}
ignore.update('/usr/share/hyphen/' + x for x in hyph_ignore)

ignore_patterns = [
    # Flatpak runtime has a versioned gawk-5.0.1
    r'/usr/bin/gawk-.*',

    # Architecture specific aliases for gcc, binutils, etc
    r'^/usr/bin/x86_64-unknown-linux-.*',

    # Trimmed from xorg-x11-proto-devel (xorgproto)
    r'/usr/include/X11/extensions/applewm.*',

    # From NSPR, intentionally not installed on Fedora
    r'/usr/include/md/.*',

    # Monolithic driver (individual driver symlinks are detected)
    r'^/usr/lib64/GL/default/lib/dri/libgallium_.*.so',

    # Windows binaries?
    r'/usr/lib64/python3.10/site-packages/setuptools/.*.exe',

    # differences in pip packaging - unbundling
    r'^/usr/lib64/python3.10/site-packages/pip/_internal/.*',
    r'^/usr/lib64/python3.10/site-packages/pip/_vendor/.*',
    r'^/usr/lib64/python3.10/site-packages/pkg_resources/_vendor/.*',
    r'^/usr/lib64/python3.10/site-packages/setuptools/_vendor/.*',

    # Let the python files pull in the packages, avoid versioned directory names
    r'^/usr/lib64/python3.10/site-packages/[^/]*.dist-info/.*',
    r'^/usr/lib64/python3.10/site-packages/[^/]*.egg-info.*',

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
    (r'^/usr/include/c\+\+/12.2.0/x86_64-unknown-linux-gnu/(.*)', r'/usr/include/c++/13/x86_64-redhat-linux/\1'),
    (r'^/usr/include/c\+\+/12.2.0/(.*)', r'/usr/include/c++/13/\1'),
    (r'^/usr/include/(libav.*)', r'/usr/include/ffmpeg/\1'),
    (r'^/usr/include/(libsw.*)', r'/usr/include/ffmpeg/\1'),
    (r'^/usr/include/nss/(.*)', r'/usr/include/nss3/\1'),
    (r'^/usr/include/python3.10/(.*)', r'/usr/include/python3.11/\1'),
    (r'^/usr/include/ruby-[0-9\.]*/ruby/(.*)', r'/usr/include/ruby/\1'),
    (r'^/usr/include/ruby-[0-9\.]*/x86_64-linux/ruby/(.*)', r'/usr/include/ruby/\1'),
    (r'^/usr/include/ruby-[0-9\.]*/(.*)', r'/usr/include/ruby/\1'),
    (r'^/usr/lib64/GL/default/lib/dri/(.*)', r'/usr/lib64/dri/\1'),
    (r'^/usr/lib64/gstreamer-1.0/(gst-.*)', r'/usr/libexec/gstreamer-1.0/\1'),
    (r'^/usr/lib64/pkgconfig/(.*proto.pc)', r'/usr/share/pkgconfig/\1'),
    (r'^/usr/lib64/pkgconfig/ruby-[0-9\.]*.pc', r'/usr/lib64/pkgconfig/ruby.pc'),
    (r'^/usr/lib64/python3.10/(.*).cpython-310-(.*)', r'/usr/lib64/python3.11/\1.cpython-311-\2'),
    (r'^/usr/lib64/python3.10/(.*)', r'/usr/lib64/python3.11/\1'),
    (r'^/usr/lib64/(v4l[12].*.so)', r'/usr/lib64/libv4l/\1'),
    (r'^/usr/share/fonts/adobe-source-code-pro-fonts/(.*)', r'/usr/share/fonts/adobe-source-code-pro/\1'),
    (r'^/usr/share/fonts/cantarell/Cantarell-VF.otf', r'/usr/share/fonts/abattis-cantarell-fonts/Cantarell-Regular.otf'),
    (r'^/usr/share/fonts/dejavu/(DejaVuMath.*)', r'/usr/share/fonts/dejavu-serif-fonts/\1'),
    (r'^/usr/share/fonts/dejavu/(DejaVuSansMono.*)', r'/usr/share/fonts/dejavu-sans-mono-fonts/\1'),
    (r'^/usr/share/fonts/dejavu/(DejaVuSans.*)', r'/usr/share/fonts/dejavu-sans-fonts/\1'),
    (r'^/usr/share/fonts/dejavu/(DejaVuSerif.*)', r'/usr/share/fonts/dejavu-serif-fonts/\1'),
    (r'^/usr/share/fonts/google-crosextra-caladea/(Caladea.*)', r'/usr/share/fonts/google-crosextra-caladea-fonts/\1'),
    (r'^/usr/share/fonts/google-crosextra-carlito/(Carlito.*)', r'/usr/share/fonts/google-carlito-fonts/\1'),
    (r'^/usr/share/fonts/liberation-fonts/(LiberationMono.*)', r'/usr/share/fonts/liberation-mono/\1'),
    (r'^/usr/share/fonts/liberation-fonts/(LiberationSans.*)', r'/usr/share/fonts/liberation-sans/\1'),
    (r'^/usr/share/fonts/liberation-fonts/(LiberationSerif.*)', r'/usr/share/fonts/liberation-serif/\1'),
    (r'^/usr/share/fonts/noto-emoji/(.*)', r'/usr/share/fonts/google-noto-emoji/\1'),
]
rename_compiled = [(re.compile(a), b) for a, b in rename_patterns]

global_package_ignore_patterns = [
    # The Fedora packages of fcitx pull in qt4. While would be nice to match the upstream
    # runtime in including fcitx for full compatibility when the host is using fcitx,
    # it doesn't seem worth the increase in runtime size.
    '^fcitx-.*$',

    # Should be installed on the host instead
    '^dbus-daemon$',
    '^fuse$',
    '^jack-audio-connection-kit$',
    '^nscd$',
    '^pipewire$',
    '^pulseaudio$',
    '^tracker$',
    '^uuidd$',
    '^v4l-utils$',
    '^v4l-utils-devel-tools$',
    '^xdg-desktop-portal$',
    '^xdg-desktop-portal-devel$',
    '^openssl1\.1-devel$', # conflicts with openssl-devel from openssl 3.0
    '^golang-github-xo-terminfo$', # conflicts on /usr/bin/infocmp with ncurses
    '^elfutils-debuginfod$', # we don't need debuginfod server
]

global_package_ignore_compiled = [re.compile(p) for p in global_package_ignore_patterns]

platform_package_ignore_patterns = [
    "^.*-devel$",
    "^libappstream-glib-builder$", # may not need in the sdk either
    "^gcc-gdb-plugin$", # pulls in gcc
    "^gtk-doc$",
    "^gtk4-devel-tools$",
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
