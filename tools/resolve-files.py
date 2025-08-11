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

# Use this for individual utilities absent or unsupported in Fedora;
# to exclude entire packages, use *_package_ignore_patterns below
bin_ignore = [
    # /usr/share/doc/aspell/aspell-import in Fedora
    'aspell-import',

    # compatibility perl script in zenity for something quite old, not packaged in fedora
    'gdialog',

    # glibc-utils not packaged in Fedora
    'nscd', 'sln', 'trace',

    # gnupg utilities not packaged in Fedora
    'gpg-authcode-sign.sh', 'gpg-mail-tube', 'gpgscm', 'gpgtar',

    # gnutls utlilties not packaged in Fedora
    'srptool',

    # groff contrib utilities not packaged in Fedora
    'groffer', 'roff2dvi', 'roff2html', 'roff2pdf', 'roff2ps', 'roff2text', 'roff2x',

    # gstreamer1 utilities not packaged in Fedora
    'gst-tester-1.0', 'playout',

    # kf5-*/phonon-qt5 in <=39, kf6-*/phonon-qt6 in >=40
    'kde-geo-uri-handler', 'kwalletd5', 'kwalletd6', 'kwallet-query', 'phononsettings',

    # libjpeg-turbo utilities not packaged in Fedora
    'tjbench',

    # libselinux utilities not packaged in Fedora
    'compute_av', 'compute_create', 'compute_member', 'compute_relabel', 'getfilecon',
    'getpidcon', 'getseuser', 'policyvers', 'selinux_check_securetty_context',
    'setfilecon', 'togglesebool',

    # removed from npth-devel
    'npth-config',

    # nss tools unsupported or unpackaged in Fedora
    'hw-support', 'nss', 'pwdecrypt', 'shlibsign', 'signtool', 'symkeyutil', 'validation',

    # Versioned python3 binaries
    'pydoc3.13', 'python3.13', 'python3.13-config', 'python3.13m',  'python3.13m-config', '2to3-3.13',
    'easy_install-3.13', 'pip3.13', 'pyvenv-3.13',

    # nettle utilities not currently packaged in fedora
    # (https://src.fedoraproject.org/rpms/nettle/c/2ec204e2de17006b566c9ff7d90ec65ca1680ed5?branch=master)
    'nettle-hash', 'nettle-lfib-stream', 'nettle-pbkdf2', 'pkcs1-conv', 'sexp-conv',

    # krb5 sample utilities not packaged in Fedora
    'gss-client', 'gss-server', 'krb5-send-pr', 'sim_client', 'sim_server',
    'uuclient', 'uuserver',

    # pciutils tools not packaged in Fedora
    'pcilmr',

    # v4l-utils tools not packaged in Fedora
    'decode_tm6000',

    # Debian login/passwd/util-linux
    'expiry', 'faillog', 'logoutd', 'mkfs.bfs',

    # OpenEmbedded uses Debian's ca-certificates, Fedora is different
    'update-ca-certificates',

    # specific to community SDKs
    'freedesktop-sdk-stripper',
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
    # automake
#    'aclocal-1.18': 'aclocal-1.18',
#    'automake-1.18': 'automake-1.18',

    # bzip2
    'bzfless': 'bzless',

    # cups-client
    'lpr': 'lpr.cups',

    # GIO/GTK module file generators
    'gdk-pixbuf-query-loaders': 'gdk-pixbuf-query-loaders-64',
    'gio-querymodules': 'gio-querymodules-64',
    'gtk-query-immodules-2.0': 'gtk-query-immodules-2.0-64',
    'gtk-query-immodules-3.0': 'gtk-query-immodules-3.0-64',

    # glslang
    'glslang': 'glslangValidator',

    # libselinux-utils
    'getconlist': 'selinuxconlist',
    'getdefaultcon': 'selinuxdefcon',

    # perl
    'perl5.42.0': 'perl',

    # vala
    'vala-0.58': 'vala-0.56',
    'vala-gen-introspect-0.58': 'vala-gen-introspect-0.56',
    'valac-0.58': 'valac-0.56',
    'vapigen-0.58': 'vapigen-0.56',
}
rename.update({'/usr/bin/' + k: '/usr/bin/' + v for k, v in bin_rename.items()})

lib_ignore = [
    # Symlink created in freedesktop.org flatpak runtime, not standard
    'libEGL_indirect.so.0',
    'load-p11-kit-trust.so',

    # From AppArmor; Fedora/RHEL use SELinux instead
    'libapparmor.so', 'libapparmor.so.1',

    # binutils internal libraries
    'libbfd-2.45.so', 'libopcodes-2.45.so', 'libgprofng.so', 'libgprofng.so.0',

    # Trimmed from gettext(-devel)
    'libgettextlib.so', 'libgettextsrc.so', 'libtextstyle.so', 'libtextstyle.so.0',

    # binutils-gprofng private libraries
    'libgprofng.so', 'libgprofng.so.0',

    # Part of glibc
    'libc_malloc_debug.so', 'libssp.so.0',

    # glslang is built as static libraries only
    'libHLSL.so.15', 'libHLSL.so', 'libSPIRV.so.15', 'libSPIRV.so',
    'libSPVRemapper.so.15', 'libSPVRemapper.so', 'libglslang.so.15', 'libglslang.so',
    'libglslang-default-resource-limits.so.15', 'libglslang-default-resource-limits.so',

    # Disabled in libunwind
    'libunwind-ptrace.so', 'libunwind-ptrace.so.0',
    'libunwind-setjmp.so', 'libunwind-setjmp.so.0',
]
ignore.update('/usr/lib64/' + x for x in lib_ignore)

lib_rename = {
    # Newer or older in Fedora
    'libassuan.so.9': 'libassuan.so.0',
    'libgettextlib-0.26.so': 'libgettextlib-0.25.1.so',
    'libgettextsrc-0.26.so': 'libgettextsrc-0.25.1.so',
    'libgpgme.so.45': 'libgpgme.so.11',
    'libgpgmepp.so.7': 'libgpgmepp.so.6',
    'libmanette-1.so.0': 'libmanette-0.2.so.0',
    'libnsl.so.1': 'libnsl.so.3',
    'libpkgconf.so.7': 'libpkgconf.so.5',
    'libproc2.so.1': 'libproc2.so.0',
    'libpython3.13.so.1.0': 'libpython3.14.so.1.0',
    'libpython3.13.so': 'libpython3.14.so',
    'libSvtAv1Enc.so.3': 'libSvtAv1Enc.so.2',
    'libtag.so.2': 'libtag.so.1',
    'libtag_c.so.2': 'libtag_c.so.0',
    'libtheora.so.1': 'libtheora.so.0',
    'libtheoradec.so.2': 'libtheoradec.so.1',
    'libtheoraenc.so.2': 'libtheoraenc.so.1',
    'libvala-0.58.so.0': 'libvala-0.56.so.0',
    'libverto.so.0': 'libverto.so.1',
    'libvpx.so.11': 'libvpx.so.9',
    'libwebrtc-audio-processing-2.so': 'libwebrtc-audio-processing-1.so',
    'libwebrtc-audio-processing-2.so.1': 'libwebrtc-audio-processing-1.so.3',
    'libxml2.so.16': 'libxml2.so.2',

    # ffmpeg-free version may be different
    'libavcodec.so.60': 'libavcodec.so.61',
    'libavdevice.so.60': 'libavdevice.so.61',
    'libavfilter.so.9': 'libavfilter.so.10',
    'libavformat.so.60': 'libavformat.so.61',
    'libavutil.so.58': 'libavutil.so.59',
    'libswresample.so.4': 'libswresample.so.5',
    'libswscale.so.7': 'libswscale.so.8',

    # ncurses is built with a single tinfo library for both narrow and wide
    'libtinfow.so': 'libtinfo.so',
    'libtinfow.so.6': 'libtinfo.so.6',

    # named differently when built with autotools vs cmake
    'libSDL2_mixer-2.0.so': 'libSDL2_mixer.so',
    'libSDL2_net-2.0.so': 'libSDL2_net.so',
}
rename.update({'/usr/lib64/' + k: '/usr/lib64/' + v for k, v in lib_rename.items()})

gcc_libs = [
    'libasan.so', 'libatomic.so', 'libgcc_s.so', 'libgfortran.so', 'libgomp.so',
    'libhwasan.so', 'libitm.so', 'liblsan.so', 'libobjc.so', 'libquadmath.so',
    'libstdc++.so', 'libtsan.so', 'libubsan.so'
]
rename.update({'/usr/lib64/' + x: '/usr/lib/gcc/x86_64-redhat-linux/15/' + x for x in gcc_libs})

for old in ['libasm-0.193.so', 'libdw-0.193.so', 'libelf-0.193.so', 'libdebuginfod-0.193.so']:
    rename['/usr/lib64/' + old] = '/usr/lib64/' + old.replace('-0.193', '-0.193')

# Fedora may have newer icu
for old in ['libicudata.so.77', 'libicui18n.so.77', 'libicuio.so.77', 'libicutest.so.77',
            'libicutu.so.77', 'libicuuc.so.77']:
    rename['/usr/lib64/' + old] = '/usr/lib64/' + old.replace('so.77', 'so.77')

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
rename.update({'/usr/include/' + x: '/usr/include/nspr4/' + x for x in nspr_include})

# pipewire jack libraries are installed in a non-standard path
jack_libraries = [
    'libjack.so', 'libjacknet.so', 'libjackserver.so'
]
rename.update({'/usr/lib64/' + x: '/usr/lib64/pipewire-0.3/jack/' + x for x in jack_libraries})

# These plugins in the freedesktop runtime pull in gstreamer-plugins-bad-free-extras, which
# in turn pulls in a lot more dependencies. If they are useful, they should be moved
# to gstreamer-plugins-bad-free.
gstreamer_plugins_ignore = {
    'libgstdecklink.so', 'libgstladspa.so', 'libgstwildmidi.so'
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
    'libvala-0.58.pc': 'libvala-0.56.pc',
    'manette-1.pc': 'manette-0.2.pc',
#    'mozjs-140.pc': 'mozjs-140.pc',
    'python-3.13.pc': 'python-3.14.pc',
    'python-3.13-embed.pc': 'python-3.14-embed.pc',
    'vapigen-0.58.pc': 'vapigen-0.56.pc',
    'webrtc-audio-processing-2.pc': 'webrtc-audio-processing-1.pc',
}
rename.update({'/usr/lib64/pkgconfig/' + k: '/usr/lib64/pkgconfig/' + v for k, v in pc_rename.items()})
rename.update({'/usr/share/pkgconfig/' + k: '/usr/share/pkgconfig/' + v for k, v in pc_rename.items()})

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

    # From tdbc, not available in Fedora
    r'/usr/include/fake(mysql|pq|sql).h',
    r'/usr/include/(mysql|odbc|pq|sql)Stubs.h',
    r'/usr/include/tdbc.*.h',

    # From NSPR, intentionally not installed on Fedora
    r'/usr/include/md/.*',

    # From AppArmor; Fedora/RHEL use SELinux instead
    r'/usr/include/sys/apparmor.*',

    # Trimmed from gettext-devel
    r'/usr/include/textstyle.*',

    # Trimmed from ncurses-devel
    r'/usr/include/nc_tparm.h',
    r'/usr/include/tic.h',

    # Arch-specific paths
    r'/usr/include/.*-linux-gnu',
    r'/usr/lib64/ld-linux.*',

    # Trimmed from Fedora perl packages, or pull -devel into platform
    r'/usr/lib64/perl5.*/.packlist',
    r'/usr/lib64/perl5/[\d.]+/ExtUtils/MakeMaker/Locale\.pm',
    r'/usr/lib64/perl5/[\d.]+/ExtUtils/MakeMaker/version\.pm',
    r'/usr/lib64/perl5/[\d.]+/ExtUtils/PL2Bat\.pm',
    r'/usr/lib64/perl5/[\d.]+/ExtUtils/typemap',
    r'/usr/lib64/perl5/[\d.]+/.*/File/Spec/VMS\.pm',
    r'/usr/lib64/perl5/[\d.]+/pod/.*',

    # Pulls in a conflicting compatibility version of python3-cython
    r'/usr/lib64/python[\d.]+/site-packages/Cython/Includes/Deprecated/.*',
    r'/usr/lib64/python[\d.]+/site-packages/Cython/(Plex/Timing|Plex/Traditional)\.py',
    r'/usr/lib64/python[\d.]+/site-packages/Cython/Utility/Capsule\.c',

    # Removed or renamed in Python 3.14
    r'/usr/lib64/python[\d.]+/_compression.py',
    r'/usr/lib64/python[\d.]+/_pyrepl/.*curses.py',
    r'/usr/lib64/python[\d.]+/encodings/.*',
    r'/usr/lib64/python[\d.]+/lib-dynload/_.*',
    r'/usr/lib64/python[\d.]+/pathlib/_.*',
    r'/usr/lib64/python[\d.]+/site-packages/pkg_resources/tests/.*',
    r'/usr/lib64/python[\d.]+/site-packages/setuptools/_distutils/compilers/C/tests/.*',
    r'/usr/lib64/python[\d.]+/site-packages/setuptools/_distutils/tests/.*',
    r'/usr/lib64/python[\d.]+/site-packages/setuptools/tests/.*',
    r'/usr/lib64/python[\d.]+/site-packages/sitecustomize.py',

    # System fonts are used in gi-docgen
    r'/usr/lib64/python[\d.]+/site-packages/gidocgen/templates/basic/.*.woff2?',

    # Qt private API headers, micro version will not always align
    r'/usr/include/Qt.*/[\d.]+/Qt.*',

    # Monolithic driver (individual driver symlinks are detected)
    r'^/usr/lib64/GL/default/lib/dri/libgallium_.*.so',
    r'^/usr/lib64/GL/default/lib/vdpau/libvdpau_gallium.so.*',
    # Trace library
    r'^/usr/lib64/GL/default/lib/vdpau/libvdpau_trace.so.*',
    # Unversioned symlinks are not packaged
    r'^/usr/lib64/GL/default/lib/vdpau/libvdpau_.*.so$',

    # symlinks to pkcs11(prov).so
    r'^/usr/lib64/ossl-modules/libpkcs11.so',

    # Windows binaries?
    r'/usr/lib64/python[\d.]+/site-packages/setuptools/.*.exe',

    # differences in pip packaging - unbundling
    r'^/usr/lib64/python[\d.]+/site-packages/pip/_internal/.*',
    r'^/usr/lib64/python[\d.]+/site-packages/pip/_vendor/.*',
    r'^/usr/lib64/python[\d.]+/site-packages/pkg_resources/_vendor/.*',
    r'^/usr/lib64/python[\d.]+/site-packages/setuptools/_vendor/.*',

    # Let the python files pull in the packages, avoid versioned directory names
    r'^/usr/lib64/python[\d.]+/site-packages/[^/]*.dist-info/.*',
    r'^/usr/lib64/python[\d.]+/site-packages/[^/]*.egg-info.*',

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

    # provided by both dvtm and ncurses-term; only the latter is wanted
    r'^/usr/share/terminfo/d/dvtm.*',
]
ignore_compiled = [re.compile(x) for x in ignore_patterns]

rename_patterns = [
    (r'^/usr/include/c\+\+/[\d\.]*/x86_64-unknown-linux-gnu/(.*)', r'/usr/include/c++/15/x86_64-redhat-linux/\1'),
    (r'^/usr/include/c\+\+/[\d\.]*/(.*)', r'/usr/include/c++/15/\1'),
    (r'^/usr/include/(libav.*)', r'/usr/include/ffmpeg/\1'),
    (r'^/usr/include/(libsw.*)', r'/usr/include/ffmpeg/\1'),
#    (r'^/usr/include/mozjs-140/(.*)', r'/usr/include/mozjs-140/\1'),
    (r'^/usr/include/nss/(.*)', r'/usr/include/nss3/\1'),
    (r'^/usr/include/(proxy.h)', r'/usr/include/libproxy/\1'),
    (r'^/usr/include/python3.13/(.*)', r'/usr/include/python3.14/\1'),
    (r'^/usr/include/ruby-[\d\.]*/ruby/(.*)', r'/usr/include/ruby/\1'),
    (r'^/usr/include/ruby-[\d\.]*/x86_64-linux/ruby/(.*)', r'/usr/include/ruby/\1'),
    (r'^/usr/include/ruby-[\d\.]*/(.*)', r'/usr/include/ruby/\1'),
    (r'^/usr/include/sysprof-[\d]+/(.*)', r'/usr/include/sysprof-6/\1'),
    (r'^/usr/lib64/GL/default/lib/(OpenCL/vendors/.*)', r'/etc/\1'),
    (r'^/usr/lib64/GL/default/lib/(vulkan/icd.d/.*)', r'/usr/share/\1'),
    (r'^/usr/lib64/GL/default/lib/(.*)', r'/usr/lib64/\1'),
    (r'^/usr/lib64/GL/default/share/clc/(.*)', r'/usr/lib64/clc/\1'),
    (r'^/usr/lib64/GL/default/share/(.*)', r'/usr/share/\1'),
    (r'^(/usr/lib64/gdk-pixbuf-2.0/.*)/libpixbufloader-svg.so', r'\1/libpixbufloader_svg.so'),
    (r'^/usr/lib64/gstreamer-1.0/(gst-.*)', r'/usr/libexec/gstreamer-1.0/\1'),
    (r'^(/usr/lib64/ossl-modules)/pkcs11prov.so', r'\1/pkcs11.so'),
    (r'^/usr/lib64/perl5/site_perl/[\d.]+/x86_64-linux-gnu/(.*)', r'/usr/lib64/perl5/\1'),
    (r'^/usr/lib64/perl5/site_perl/[\d.]+/(.*)', r'/usr/lib64/perl5/\1'),
    (r'^/usr/lib64/perl5/vendor_perl/[\d.]+/x86_64-linux-gnu/(.*)', r'/usr/lib64/perl5/\1'),
    (r'^/usr/lib64/perl5/vendor_perl/[\d.]+/(.*)', r'/usr/lib64/perl5/\1'),
    (r'^/usr/lib64/perl5/[\d.]+/x86_64-linux-gnu/(.*)', r'/usr/lib64/perl5/\1'),
    (r'^/usr/lib64/perl5/[\d.]+/(.*)', r'/usr/lib64/perl5/\1'),
    (r'^/usr/lib64/pkgconfig/(.*proto.pc)', r'/usr/share/pkgconfig/\1'),
    (r'^/usr/lib64/pkgconfig/ruby-[\d\.]*.pc', r'/usr/lib64/pkgconfig/ruby.pc'),
    (r'^/usr/lib64/python3.13/(pathlib|sysconfig).py', r'/usr/lib64/python3.14/\1/__init__.py'),
    (r'^/usr/lib64/python3.13/(site-packages/_dbus.*).cpython-313-.*', r'/usr/lib64/python3.14/\1.so'),
    (r'^/usr/lib64/python3.13/config-3.13-(.*)', r'/usr/lib64/python3.14/config-3.14-\1'),
    (r'^/usr/lib64/python3.13/(.*).cpython-313-(.*)', r'/usr/lib64/python3.14/\1.cpython-314-\2'),
    (r'^/usr/lib64/python3.13/(.*)', r'/usr/lib64/python3.14/\1'),
    (r'^/usr/lib64/(v4l[12].*.so)', r'/usr/lib64/libv4l/\1'),
    (r'^/usr/share/fonts/Adwaita/(AdwaitaMono.*)', r'/usr/share/fonts/adwaita-mono-fonts/\1'),
    (r'^/usr/share/fonts/Adwaita/(AdwaitaSans.*)', r'/usr/share/fonts/adwaita-sans-fonts/\1'),
    (r'^/usr/share/fonts/cantarell/(Cantarell-VF.otf)', r'/usr/share/fonts/abattis-cantarell-vf-fonts/\1'),
    (r'^/usr/share/fonts/dejavu/(DejaVuMath.*)', r'/usr/share/fonts/dejavu-serif-fonts/\1'),
    (r'^/usr/share/fonts/dejavu/(DejaVuSansMono.*)', r'/usr/share/fonts/dejavu-sans-mono-fonts/\1'),
    (r'^/usr/share/fonts/dejavu/(DejaVuSans.*)', r'/usr/share/fonts/dejavu-sans-fonts/\1'),
    (r'^/usr/share/fonts/dejavu/(DejaVuSerif.*)', r'/usr/share/fonts/dejavu-serif-fonts/\1'),
    (r'^/usr/share/fonts/google-crosextra-caladea/(Caladea.*)', r'/usr/share/fonts/google-crosextra-caladea-fonts/\1'),
    (r'^/usr/share/fonts/google-crosextra-carlito/(Carlito.*)', r'/usr/share/fonts/google-carlito-fonts/\1'),
    (r'^/usr/share/fonts/liberation-fonts/(LiberationMono.*)', r'/usr/share/fonts/liberation-mono-fonts/\1'),
    (r'^/usr/share/fonts/liberation-fonts/(LiberationSans.*)', r'/usr/share/fonts/liberation-sans-fonts/\1'),
    (r'^/usr/share/fonts/liberation-fonts/(LiberationSerif.*)', r'/usr/share/fonts/liberation-serif-fonts/\1'),
    (r'^/usr/share/fonts/noto-emoji/NotoColorEmoji.*', r'/usr/share/fonts/google-noto-color-emoji-fonts/Noto-COLRv1.ttf'),
]
rename_compiled = [(re.compile(a), b) for a, b in rename_patterns]

global_package_ignore_patterns = [
    # The Fedora packages of fcitx pull in qt4. While would be nice to match the upstream
    # runtime in including fcitx for full compatibility when the host is using fcitx,
    # it doesn't seem worth the increase in runtime size.
    '^fcitx-.*$',

    # Should be installed on the host instead
    '^arptables-legacy$',
    '^audispd-plugins$',
    '^audit$',
    "^authselect$",
    '^avahi$',
    '^avahi-autoipd$',
    '^avahi-dnsconfd$',
    '^avahi-gobject.*',
    '^avahi-ui.*',
    '^cryptsetup.*$',
    "^cups-ipptool$",
    "^cups-printerapp$",
    '^dbus$',
    '^dbus-broker$',
    '^dbus-daemon$',
    '^dbus-x11$',
    '^device-mapper.*$',
    '^dvb-tools$',
    '^ebtables-legacy$',
    '^fuse$',
    '^ibus$',
    '^ibus-setup$',
    '^integritysetup$',
    '^iptables.*$',
    '^jack-audio-connection-kit$',
    '^kbd$',
    '^kbd-legacy$',
    '^kbd-misc$',
    '^kmod$',
    '^kmod-devel$',
    '^krb5-server$',
    '^libaio.*',
    '^libdaemon.*',
    '^libmnl.*',
    '^libnftnl.*',
    '^lvm2.*$',
    '^nscd$',
    '^openresolv$',
    '^pam$',
    '^passwd$',
    '^pipewire$',
    '^pipewire-pulse$',
    '^pipewire-v4l2$',
    '^pulseaudio$',
    '^rc-tools$',
    '^shadow-utils-subid$',
    '^switcheroo-control$',
    '^systemd$',
    '^systemd-container$',
    '^systemd-networkd$',
    '^systemd-resolved$',
    '^systemd-standalone-repart$',
    '^systemd-udev$',
    '^tinysparql$',
    '^tracker$',
    '^uuidd$',
    '^v4l-utils$',
    '^v4l-utils-devel-tools$',
    '^veritysetup$',
    '^xdg-dbus-proxy$',
    '^xdg-desktop-portal$',
    '^xdg-desktop-portal-devel$',

    # unnecessary utilities, or unwanted due to dependencies;
    # if any of these need to be made available in SDK for compatibility,
    # move them to platform_package_ignore_patterns[] below
    "^aom$",
    "^aspell.*",
    '^avahi-tools$',
    '^avahi-ui-tools$',
    '^cowsay$',
    "^cyrus-sasl$",
    "^dav1d$",
    '^enchant2-nuspell$',
    '^fido2-tools$',
    '^gamemode.*',
    '^gcab$',
    '^gcr$',
    '^gcr3.*',
    '^gdbm$',
    '^giflib-utils$',
    '^gitk$',
    '^glibc-utils$',
    '^gstreamer1-plugins-base-tools$',
    '^gstreamer1-plugins-ugly-free$',
    '^gtksourceview5-tests$',
    '^idn2$',
    '^itcl$',
    '^itcl-devel$',
    '^itk$',
    '^itk-devel$',
    r'^kf[\d]+-sonnet-aspell$',
    '^lcms2-utils$',
    '^libXt$',  # needs to be rebuilt to search /app
    '^libXt-devel$',
    '^libbpf.*',
    '^libcap-ng-utils$',
    '^libeconf-utils$',
    '^libei-utils$',
    '^libevdev-utils$',
    '^libselinux-utils$',
    '^libsepol-utils$',
    '^libsndfile-utils$',
    '^libtasn1-tools$',
    '^libtiff-tools$',
    '^libxkbcommon-utils$',
    '^libvpx-utils$',
    '^mesa-libd3d-devel$',
    '^nuspell*',
    '^openssh$',
    '^openssl-pkcs11$',  # replaced by pkcs11-provider
    '^pciutils$',
    '^pcre-tools$',
    '^pcre2-tools$',
    '^pipewire-utils$',
    '^plocate$',
    '^psl$',
    '^psl-make-dafsa$',
    '^pulseaudio-utils$',
    '^qrencode$',
    '^qv4l2$',  # requires qt5
    '^rr$',
    '^speex-tools$',
    '^sqlite$',
    '^sqlite-analyzer$',
    '^svt-av1$',
    '^tcl-thread$',
    '^tcl-thread-devel$',
    '^texinfo-tex$',  # requires texlive
    '^wildmidi.*',  # requires fluid-soundfont
    '^xxhash$',

    # file conflicts
    '^coreutils$',  # conflicts with coreutils-single
    r'^openssl1\.1-devel$',  # conflicts with openssl-devel from openssl 3.0
    '^golang-github-cespare-xxhash$', # conflicts with xxhash
    '^golang-github-google-martian$', # conflicts with libproxy-bin
    '^golang-github-xo-terminfo$',  # conflicts on /usr/bin/infocmp with ncurses
    '^elfutils-debuginfod$',  # we don't need debuginfod server
    '^ocl-icd.*',  # conflicts with OpenCL-ICD-Loader
    '^wget1-wget$',  # conflicts with wget2-wget
]

global_package_ignore_compiled = [re.compile(p) for p in global_package_ignore_patterns]

platform_package_ignore_patterns = [
    "^.*-devel$",
    "^.*-static$",
    "^appstream-compose",
    "^blueprint-compiler",
    "^libappstream-glib-builder$", # may not need in the sdk either
    "^gcc-gdb-plugin$",  # pulls in gcc
    '^gperf$',
    "^gtk-doc$",
    "^gtk4-devel-tools$",
    "^icu$",  # may not need in the sdk either
    '^itstool$',
    '^krb5-pkinit$',
    '^krb5-workstation$',
    '^librsvg2-tools$',
    '^llvm$',
    '^llvm-test$',  # pulls in gcc and binutils
    '^openssl$',
    '^perl',  # all perl components should be only in sdk
    '^python3-attrs$',
    '^python3-jinja2$',
    '^python3-test$',
    '^sqlite$',
    '^xcb-proto$',
    '^xmltoman$',
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

def get_files_map(platform_only=False):
    return util.get_repo_map('files-map', make_files_map, platform_only=platform_only)

start("Reading file list")

to_resolve = []
with open(inpath) as f:
    for line in f:
        r = line.rstrip()
        if r.startswith('/usr/lib/x86_64-linux-gnu/'):
            r = '/usr/lib64/' + r[len('/usr/lib/x86_64-linux-gnu/'):]
        elif r.startswith('/usr/lib/'):
            r = '/usr/lib64/' + r[len('/usr/lib/'):]
        to_resolve.append(r)

to_resolve.sort()

done()

files_map = get_files_map(platform_only=is_platform)
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
    elif r.startswith('/usr/lib64/perl5') > 0:
        # Perl packages can be either in privlib or archlib, and may be
        # packaged in vendorlib or vendorarch instead
        search = [r,
            '/usr/lib64/perl5/vendor_perl/' + r[len('/usr/lib64/perl5/'):],
            '/usr/share/perl5/vendor_perl/' + r[len('/usr/lib64/perl5/'):],
            '/usr/share/perl5/' + r[len('/usr/lib64/perl5/'):],
        ]
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
    else:
        providing = None

    if providing is None:
        print(r, file=unmatched_file)
        unmatched_count += 1
    else:
        # On Fedora glibc-headers-s390 and glibc-headers-x86_64 are no-arch
        # dependencies of glibc-devel required on the specific platform;
        # we just normalize to glibc-devel and let dependencies pull in the
        # appropriate glibc-headers package.
        if providing.startswith("glibc-headers-"):
            providing = "glibc-devel"

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
