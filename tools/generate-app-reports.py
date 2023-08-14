#!/usr/bin/python3

import gi
gi.require_version('AppStreamGlib', '1.0')
from gi.repository import AppStreamGlib as AS
from gi.repository import Gio
import json
import locale
import os
import re
import requests
import subprocess
import sys

import util
from util import TAG_ARG

id_mappings = {
    '0ad': 'com.play0ad.zeroad',
    'amarok': 'org.kde.amarok',
    'android-studio': 'com.google.AndroidStudio',
    'apper': 'org.kde.apper',
    'arduino-arduinoide': 'arduino',
    'astromenace': 'com.viewizard.AstroMenace',
    'atom': 'io.atom.Atom',
    'BlockOutII': 'net.blockout.BlockOutII',
    'btanks': 'net.sourceforge.btanks',
    'deja-dup': 'org.gnome.DejaDup',
    'digikam': 'org.kde.digikam',
    'discord': 'com.discordapp.Discord',
    'evolution': 'org.gnome.Evolution',
    'feedreader': 'org.gnome.FeedReader',
    'flowblade': 'io.github.jliljebl.Flowblade',
    'geary': 'org.gnome.Geary',
    'geogebra': 'org.geogebra.GeoGebra',
    'gimp': 'org.gimp.GIMP',
    'gnome-calculator': 'org.gnome.Calculator',
    'gnome-music': 'org.gnome.Music',
    'gthumb': 'org.gnome.gThumb',
    'lollypop': 'org.gnome.Lollypop',
    'k3b': 'org.kde.k3b',
    'kmines': 'org.kde.kmines',
    'krita': 'org.kde.krita',
    'lshw': 'lshw-gui',
    'lshw-gtk': 'lshw-gui',
    'megaglest': 'org.megaglest.MegaGlest',
    'minetest': 'net.minetest.Minetest',
    'minitube': 'org.tordini.flavio.Minitube',
    'okular': 'org.kde.okular',
    'openmw': 'org.openmw.OpenMW',
    'parole': 'org.xfce.Parole',
    'pingus': 'org.seul.pingus',
    'qtcreator': 'org.qt-project.qtcreator',
    'qupzilla': 'org.qupzilla.QupZilla',
    'nextcloud': 'org.nextcloud.Nextcloud',
    'quasselclient': 'org.quassel_irc.QuasselClient',
    'qBittorrent': 'qbittorrent',
    'siril': 'org.free-astro.siril',
    'slack': 'com.slack.Slack',
    'skype': 'com.skype.Client',
    'sound-juicer': 'org.gnome.SoundJuicer',
    'spotify': 'com.spotify.Client',
    'steam': 'com.valvesoftware.Steam',
    'stellarium': 'org.stellarium.Stellarium',
    'smb4k': 'org.kde.smb4k',
    'supertux2': 'org.supertuxproject.SuperTux',
    'telegramdesktop': 'org.telegram',
    'telegram-desktop': 'org.telegram',
    'texstudio': 'org.texstudio.TeXstudio',
    'thunderbird': 'mozilla-thunderbird',
    'tremulous': 'com.grangerhub.Tremulous',
    'viber': 'com.viber.Viber',
    'visual-studio-code': 'com.visualstudio.code',
    'vlc': 'org.videolan.VLC',
    'warzone2100': 'net.wz2100.wz2100',
    'warzone2100': 'net.wz2100.wz2100',
    'wxmaxima': 'wxMaxima',
    'Zoom': 'us.zoom.Zoom',
}

for k, v in {k: v for k, v in id_mappings.items()}.items():
    id_mappings[v] = k


def no_desktop(id):
    if id.endswith('.desktop'):
        id = id[0:-8]
    return id


def make_desktop_map(repo_info):
    desktop_map = {}

    def cb(package_info, f):
        if f.startswith("/usr/share/applications/"):
            desktop_id = os.path.basename(f)
            old = desktop_map.get(desktop_id)
            if old is None or util.package_cmp(package_info, old) < 0:
                desktop_map[desktop_id] = package_info

    util.foreach_file(repo_info, cb)

    for k in desktop_map:
        desktop_map[k] = desktop_map[k][0]

    return desktop_map

def get_desktop_map():
    return util.get_repo_cacheable('desktop-map', make_desktop_map)

util.set_log_name(os.path.basename(sys.argv[0]))

desktop_map = get_desktop_map()

class Application:
    def __init__(self):
        self.name = None
        self.description = None
        self.homepage = None
        self.package = None
        self.extra_packages = None
        self.flathub = None
        self.fedora_id = None
        self.flathub_id = None
        self.odrs_id = None
        self.star_total = None
        self.stars = [None, None, None, None, None, None]

    @property
    def canon_id(self):
        if self.flathub_id is not None:
            return self.flathub_id
        elif self.fedora_id is not None:
            return self.fedora_id
        else:
            return self.odrs_id

    @property
    def display_name(self):
        if self.name is not None:
            return self.name
        else:
            assert self.odrs_id
            if self.odrs_id.endswith('.desktop'):
                return self.odrs_id[0:-8]
            else:
                return self.odrs_id

def iterate_apps(store):
    for app in store.get_apps():
        try:
            is_desktop = app.get_id_kind() == AS.IdKind.DESKTOP
        except ValueError:
            is_desktop = False
        if is_desktop:
            yield app

id_to_application = {}
name_to_application = {}
homepage_to_application = {}

fedora_store = AS.Store()
fedora_store.from_file(Gio.File.new_for_path('out/fedora-appstream.xml.gz'), "", None)
for app in iterate_apps(fedora_store):
    a = Application()
    a.fedora_id = no_desktop(app.get_id())
    a.name = app.get_name()
    a.description = app.get_description()
    a.homepage = app.get_url_item(AS.UrlKind.HOMEPAGE)
    a.package = app.get_pkgnames()[0]

    id_to_application[a.fedora_id] = a
    name_to_application[a.name] = a
    homepage_to_application[a.homepage] = a


flathub_store = AS.Store()
flathub_store.from_file(Gio.File.new_for_path('out/flathub-appstream.xml.gz'), "", None)
for app in iterate_apps(flathub_store):
    bundle_id = app.get_bundle_default().get_id()
    prefix, flathub_id, arch, branch = bundle_id.split('/')
    name = app.get_name()
    description = app.get_description()
    homepage = app.get_url_item(AS.UrlKind.HOMEPAGE)

    id_app = id_to_application.get(flathub_id, None)
    if id_app is not None:
        id_app.flathub_id = flathub_id
        continue

    other_id = id_mappings.get(flathub_id, None)
    if other_id is not None:
        other_id_app = id_to_application.get(other_id, None)
        if other_id_app is not None:
            other_id_app.flathub_id = flathub_id
            id_to_application[flathub_id] = other_id_app
            continue

    name_app = name_to_application.get(name, None)
    # Exceptions for homepages that have more than one Flatpak application associated.
    if homepage != 'http://elementary.io/' and homepage != "http://www.w1hkj.com" and \
       homepage != 'https://www.chocolate-doom.org/' and homepage != "https://git-cola.github.io/":
        homepage_app = homepage_to_application.get(homepage, None)
    else:
        homepage_app = None

    if name_app is not None and homepage_app is not None:
        if name_app is not homepage_app:
            print("Please check whether there are more Flatpaks associated with the \"", homepage,
                  "\" homepage (by inspecting out/fedora-appstream.xml.gz). If yes, "
                  "please add an exception into tools/generate-app-reports.py.", file=sys.stderr)
        assert name_app is homepage_app
    if name_app is not None:
        a = name_app
    elif homepage_app is not None:
        a = homepage_app
    else:
        a = Application()
        a.name = name
        a.description = description
        a.homepage = homepage

    a.flathub_id = flathub_id
    id_to_application[a.flathub_id] = a

with open('out/ratings.json') as f:
    ratings = json.load(f)

for k, v in ratings.items():
    k = no_desktop(k)
    a = id_to_application.get(k, None)
    if not a:
        other_id = id_mappings.get(k, None)
        if other_id is not None:
            a = id_to_application.get(other_id, None)
        if a:
            id_to_application[k] = a
        else:
            a = Application()
    if a.package is None:
        package = desktop_map.get(k + '.desktop')
        if package:
            a.package = package
    a.odrs_id = k
    id_to_application[a.odrs_id] = a
    for x in range(0, 6):
        old = a.stars[x]
        if old is None:
            old = 0
        a.stars[x] = old + v['star' + str(x)]
    old = a.star_total
    if old is None:
        old = 0
    a.star_total = old + v['total']

def load_fedora_flatpaks():
    print("Checking for Flatpaks in src.fedoraproject.org ... ", file=sys.stderr, end="")
    flatpaks = set()

    page = 1
    retrieved = 0
    while True:
        response = requests.get(
            'https://src.fedoraproject.org/'
            f'api/0/projects?namespace=flatpaks&fork=false&page={page}&per_page=100'
        )
        response.raise_for_status()

        data = response.json()
        for project in data['projects']:
            flatpaks.add(project['name'])
            retrieved += 1

        if retrieved >= data['total_projects']:
            break

        page += 1

    print("done", file=sys.stderr)

    return flatpaks

fedora_flatpaks = load_fedora_flatpaks()

locale.setlocale(locale.LC_ALL, '')

fedora_appstream = 0
no_appstream = 0
flathub = 0
review_only = 0

output = []

apps = set(id_to_application.values())

packaged_apps = {a for a in apps if a.package is not None}

top_packaged_apps = sorted(packaged_apps, key=lambda a: a.package)
top_packaged_apps.sort(key=lambda a: -(a.star_total or 0))
top_packaged_apps = top_packaged_apps[0:100]


def get_flatpak_report(apps):
    info_json = subprocess.check_output([
        'flatpak-module-depchase',
        TAG_ARG,
        'flatpak-report',
        '--runtime-profile=out/runtime.profile'
    ] + [a.package for a in apps])

    return json.loads(info_json)


info = get_flatpak_report(packaged_apps)
for a in packaged_apps:
    app_info = info['flatpaks'].get(a.package)
    if app_info:  # package info from appstream might be stale
        a.extra_packages = info['flatpaks'][a.package]['extra']

runtime_packages = {}
extra_packages = {}
for p, i in info['packages'].items():
    if i['runtime']:
        runtime_packages[p] = {'all': i['used_by']}
    else:
        extra_packages[p] = {'all': i['used_by']}

top_info = get_flatpak_report(top_packaged_apps)

for p, i in top_info['packages'].items():
    if i['runtime']:
        runtime_packages[p]['top'] = i['used_by']
    else:
        extra_packages[p]['top'] = i['used_by']

def dict_to_list(packages):
    result = []
    for p in sorted(packages.keys()):
        i = packages[p]
        x = {
            'package': p,
            'all': sorted(i['all']),
            'all_count': len(i['all']),
        }
        if 'top' in i:
            x['top'] = sorted(i['top'])
            x['top_count'] = len(i['top'])
        result.append(x)
    result.sort(key=lambda i: -i['all_count'])

    return result

with open('reports/application-packages.json', 'w') as f:
    json.dump({
        'runtime': dict_to_list(runtime_packages),
        'extra': dict_to_list(extra_packages),
    }, f, indent=4, sort_keys=True)

def sanitize_piece(m: re.Match[str]):
    if m.group(1) is not None:
        return m.group(1)
    elif m.group(2) is not None:
        return '&lt;'
    elif m.group(3) is not None:
        return '&gt;'
    else:
        assert False

def sanitize_description(description):
    # This is specifically for a buggy appstream for GNOME Screenshot
    description = re.sub(r'<p xml:lang="[^"]*">.*</p>', '', description)
    # Main part of the sanitization - quote all <>&
    description = re.sub(
        r'(<p>|</p>|<ul>|</ul>|<li>|</li>|[^<>]+)|(<)|(>)', sanitize_piece, description
    )
    return description

for a in sorted(apps, key=lambda a: (locale.strxfrm(a.display_name), a.canon_id)):
    if a.fedora_id is not None:
        fedora_appstream += 1
    elif a.package is not None:
        no_appstream += 1
    elif a.flathub_id is not None:
        flathub += 1
    else:
        review_only += 1

    output_item = {
        'name': a.display_name,
    }

    if a.package is not None:
        output_item['package'] = a.package

    if a.description is not None:
        output_item['description'] = sanitize_description(a.description)

    if a.flathub_id is not None:
        output_item['flathub'] = a.flathub_id

    if a.fedora_id is not None:
        output_item['fedora'] = a.fedora_id

    if a.odrs_id is not None:
        output_item['odrs'] = a.odrs_id

    if a.extra_packages is not None:
        output_item['extra_packages'] = a.extra_packages

    if a.star_total is not None:
        output_item['star_avg'] = (
            sum((i * a.stars[i]) for i in range(0, 6))
            / sum((a.stars[i]) for i in range(0, 6))
        )
        output_item['star_total'] = a.star_total
        output_item['stars'] = a.stars

    output_item['fedora_flatpak'] = a.package is not None and a.package in fedora_flatpaks

    output.append(output_item)
#    print(
#       a.display_name, a.package, a.flathub_id, a.fedora_id, a.odrs_id, a.homepage, a.star_total
#    )

with open('reports/applications.json', 'w') as f:
    json.dump({
        'applications': output,
        'summary': [
            ['In Fedora appstream', fedora_appstream],
            ['In Fedora, not in appstream', no_appstream],
            ['In Flathub, not in Fedora', flathub],
            ['ODRS review, not in Flathub or Flathub', review_only],
            ['Total', fedora_appstream + no_appstream + flathub + review_only],
        ]
    }, f, indent=4, sort_keys=True)
