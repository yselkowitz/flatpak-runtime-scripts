#!/usr/bin/python3

import gi
gi.require_version('AppStreamGlib', '1.0')
from gi.repository import AppStreamGlib as AS
from gi.repository import Gio
import json
import locale
import os
import re
import subprocess
import sys

import util

id_mappings = {
    'amarok.desktop': 'org.kde.amarok.desktop',
    'android-studio.desktop': 'com.google.AndroidStudio.desktop',
    'apper.desktop': 'org.kde.apper.desktop',
    'arduino-arduinoide.desktop': 'arduino.desktop',
    'astromenace.desktop': 'com.viewizard.AstroMenace.desktop',
    'atom.desktop': 'io.atom.Atom.desktop',
    'BlockOutII.desktop': 'net.blockout.BlockOutII.desktop',
    'btanks.desktop': 'net.sourceforge.btanks.desktop',
    'deja-dup.desktop': 'org.gnome.DejaDup.desktop',
    'digikam.desktop': 'org.kde.digikam.desktop',
    'discord.desktop': 'com.discordapp.Discord.desktop',
    'evolution.desktop': 'org.gnome.Evolution.desktop',
    'feedreader.desktop': 'org.gnome.FeedReader.desktop',
    'flowblade.desktop': 'io.github.jliljebl.Flowblade.desktop',
    'geary.desktop': 'org.gnome.Geary.desktop',
    'geogebra.desktop': 'org.geogebra.GeoGebra.desktop',
    'gnome-calculator.desktop': 'org.gnome.Calculator.desktop',
    'gnome-music.desktop': 'org.gnome.Music.desktop',
    'gthumb.desktop': 'org.gnome.gThumb.desktop',
    'lollypop.desktop': 'org.gnome.Lollypop.desktop',
    'k3b.desktop': 'org.kde.k3b.desktop',
    'kmines.desktop': 'org.kde.kmines.desktop',
    'krita.desktop': 'org.kde.krita.desktop',
    'lshw.desktop': 'lshw-gui.desktop',
    'lshw-gtk.desktop': 'lshw-gui.desktop',
    'megaglest.desktop': 'org.megaglest.MegaGlest.desktop',
    'minetest.desktop': 'net.minetest.Minetest.desktop',
    'minitube.desktop': 'org.tordini.flavio.Minitube.desktop',
    'okular.desktop': 'org.kde.okular.desktop',
    'openmw.desktop': 'org.openmw.OpenMW.desktop',
    'parole.desktop': 'org.xfce.Parole.desktop',
    'pingus.desktop': 'org.seul.pingus.desktop',
    'qtcreator.desktop': 'org.qt-project.qtcreator.desktop',
    'qupzilla.desktop': 'org.qupzilla.QupZilla.desktop',
    'nextcloud.desktop': 'org.nextcloud.Nextcloud.desktop',
    'quasselclient.desktop': 'org.quassel_irc.QuasselClient.desktop',
    'qBittorrent.desktop': 'qbittorrent.desktop',
    'siril.desktop': 'org.free-astro.siril.desktop',
    'slack.desktop': 'com.slack.Slack.desktop',
    'skype.desktop': 'com.skype.Client.desktop',
    'sound-juicer.desktop': 'org.gnome.SoundJuicer.desktop',
    'spotify.desktop': 'com.spotify.Client.desktop',
    'steam.desktop': 'com.valvesoftware.Steam.desktop',
    'smb4k.desktop': 'org.kde.smb4k.desktop',
    'supertux2.desktop': 'org.supertuxproject.SuperTux.desktop',
    'telegramdesktop.desktop': 'org.telegram.desktop.desktop',
    'telegram-desktop.desktop': 'org.telegram.desktop.desktop',
    'thunderbird.desktop': 'mozilla-thunderbird.desktop',
    'tremulous.desktop': 'com.grangerhub.Tremulous.desktop',
    'viber.desktop': 'com.viber.Viber.desktop',
    'visual-studio-code.desktop': 'com.visualstudio.code.desktop',
    'vlc.desktop': 'org.videolan.VLC.desktop',
    'wxmaxima.desktop': 'wxMaxima.desktop',
    'Zoom.desktop': 'us.zoom.Zoom.desktop',
}

for k, v in { k: v for k, v in id_mappings.items() }.items():
    id_mappings[v] = k


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
    a.fedora_id = app.get_id()
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
    flathub_id = app.get_id()
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
    homepage_app = homepage_to_application.get(homepage, None)

    if name_app is not None and homepage_app is not None:
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
        package = desktop_map.get(k)
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

info_json = subprocess.check_output(['fedmod', '--dataset=rawhide', 'flatpak-report'] + [a.package for a in packaged_apps])
info = json.loads(info_json)
for a in packaged_apps:
    a.extra_packages = info['flatpaks'][a.package]['extra']

runtime_packages = {}
extra_packages = {}
for p, i in info['packages'].items():
    if i['runtime']:
        runtime_packages[p] = { 'all': i['used_by']}
    else:
        extra_packages[p] = { 'all': i['used_by']}

top_info_json = subprocess.check_output(['fedmod', '--dataset=rawhide', 'flatpak-report'] + [a.package for a in top_packaged_apps])
top_info = json.loads(top_info_json)

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

def sanitize_piece(m):
    if m.group(1) is not None:
        return m.group(1)
    elif m.group(2) is not None:
        return '&lt;'
    elif m.group(3) is not None:
        return '&gt;'

def sanitize_description(description):
    # This is specifically for a buggy appstream for GNOME Screenshot
    description = re.sub(r'<p xml:lang="[^"]*">.*</p>', '', description)
    # Main part of the sanitization - quote all <>&
    description = re.sub(r'(<p>|</p>|<ul>|</ul>|<li>|</li>|[^<>]+)|(<)|(>)', sanitize_piece, description)
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
        output_item['star_avg'] = sum((i * a.stars[i]) for i in range(0, 6))/sum((a.stars[i]) for i in range(0, 6))
        output_item['star_total'] = a.star_total
        output_item['stars'] = a.stars

    output.append(output_item)
#    print(a.display_name, a.package, a.flathub_id, a.fedora_id, a.odrs_id, a.homepage, a.star_total)

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
