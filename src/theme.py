#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Portable Debian KDE installer. No user assets or wallpaper assignments."""
from pathlib import Path
from datetime import datetime
import argparse
import fcntl
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
HOME = Path.home()
DATA = Path(os.environ.get('XDG_DATA_HOME', HOME / '.local/share'))
CONFIG = Path(os.environ.get('XDG_CONFIG_HOME', HOME / '.config'))
STATE = Path(os.environ.get('XDG_STATE_HOME', HOME / '.local/state')) / 'dweer-island-kde'
AUTOSTART = CONFIG / 'autostart/dweer-island-kde.desktop'
FILES = ['kdeglobals', 'kwinrc', 'plasmarc', 'plasmashellrc',
         'plasma-org.kde.plasma.desktop-appletsrc', 'auroraerc',
         'Kvantum/kvantum.kvconfig', 'kglobalshortcutsrc', 'kwinoutputconfig.json']
PLUGINS = ['local.reference.islandpanel', 'local.reference.downloadfan',
           'local.reference.photo', 'local.reference.media', 'local.reference.network']
WALLPAPER_SCRIPT = '''print(JSON.stringify(desktops().map(d => {
    d.currentConfigGroup=["Wallpaper",d.wallpaperPlugin,"General"];
    return {id:d.id,plugin:d.wallpaperPlugin,values:d.configKeys.map(k=>[k,d.readConfig(k)])};
})));'''


def run(args, required=True, timeout=60, env=None):
    result = subprocess.run([str(a) for a in args], capture_output=True,
                            text=True, timeout=timeout, env=env)
    if required and result.returncode:
        raise RuntimeError(f'{args[0]}: {(result.stderr or result.stdout).strip()}')
    return result


def evaluate(script):
    return run(['qdbus6', 'org.kde.plasmashell', '/PlasmaShell',
                'org.kde.PlasmaShell.evaluateScript', script], timeout=45).stdout.strip()


def version_check():
    # Query Debian's package database without starting a GUI from a text console.
    version = run(['dpkg-query', '-W', '-f=${Version}', 'plasma-workspace']).stdout
    if not re.search(r'\b6\.3\.\d+', version):
        raise RuntimeError('This version supports Plasma 6.3.x (Debian 13). Found: ' + version.strip())


def check():
    for command in ['qdbus6', 'kwriteconfig6', 'plasma-apply-colorscheme',
                    'plasma-apply-desktoptheme', 'kscreen-doctor', 'plasmashell', 'kquitapp6']:
        if not shutil.which(command):
            raise RuntimeError('Missing dependency: ' + command + '. Run ./install.sh.')
    version_check()
    for plugin in PLUGINS:
        path = DATA / 'plasma/plasmoids' / plugin / 'metadata.json'
        if not path.is_file() or json.loads(path.read_text())['KPlugin']['Id'] != plugin:
            raise RuntimeError('Missing package: ' + plugin + '. Run ./install.sh.')
    for path in [DATA / 'color-schemes/ReferenceGraphite.colors',
                 DATA / 'plasma/desktoptheme/reference-graphite/metadata.json',
                 DATA / 'aurorae/themes/ReferenceGraphite/decoration.svgz',
                 Path('/usr/share/Kvantum/KvMojave/KvMojave.kvconfig')]:
        if not path.is_file():
            raise RuntimeError('Missing asset: ' + str(path))
    print('Dependencies, Plasma version and all five custom packages: OK', flush=True)


def desktop_quote(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$') + '"'


def launchers():
    binary = HOME / '.local/bin/dweer-island-kde'
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text('#!/bin/sh\nexec /usr/bin/python3 ' + shlex.quote(str(ROOT / 'theme.py')) + ' "$@"\n')
    binary.chmod(0o755)
    applications = DATA / 'applications'
    applications.mkdir(parents=True, exist_ok=True)
    for action, name, icon in [('apply', 'Применить Dweer Island KDE', 'preferences-desktop-theme'),
                               ('restore', 'Вернуть прежний KDE', 'edit-undo')]:
        path = applications / f'dweer-island-kde-{action}.desktop'
        path.write_text(f'[Desktop Entry]\nType=Application\nName={name}\n'
                        f'Exec={desktop_quote(binary)} {action} --interactive\n'
                        f'Icon={icon}\nTerminal=true\nCategories=Settings;DesktopSettings;\n')


def prepare():
    version_check()
    with tempfile.TemporaryDirectory(prefix='dweer-island-build-') as temp:
        stage = Path(temp)
        env = {**os.environ, 'ISLAND_BUILD_DIR': str(stage)}
        for name in ['build_assets.py', 'build_widgets.py', 'build_island_panel.py']:
            result = run([sys.executable, ROOT / name], env=env)
            print(result.stdout.strip(), flush=True)
        # All source patches finish successfully before any installed asset is replaced.
        for source in (stage / 'share').iterdir():
            shutil.copytree(source, DATA / source.name, dirs_exist_ok=True)
        for plugin in (stage / 'widgets').iterdir():
            destination = DATA / 'plasma/plasmoids' / plugin.name
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(plugin, destination)
        destination = DATA / 'plasma/plasmoids/local.reference.downloadfan'
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(ROOT / 'fan', destination)
    launchers()
    if shutil.which('kbuildsycoca6'):
        run(['kbuildsycoca6', '--noincremental'], required=False)
    check()


def wait_session(wait=0):
    if 'KDE' not in os.environ.get('XDG_CURRENT_DESKTOP', ''):
        raise RuntimeError('Run from your normal KDE Plasma session, not as root.')
    deadline = time.monotonic() + wait
    while True:
        try:
            if 'ISLAND_READY' in evaluate('print(desktops().length ? "ISLAND_READY" : "WAIT")'):
                return
        except (RuntimeError, subprocess.TimeoutExpired):
            pass
        if time.monotonic() >= deadline:
            raise RuntimeError('Plasma is not ready. Log into Plasma and retry.')
        time.sleep(1)


def display_config():
    result = run(['kscreen-doctor', '-j'], required=False)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}


def snapshot():
    target = STATE / 'backups' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    target.mkdir(parents=True)
    missing = []
    for name in FILES:
        source = CONFIG / name
        if source.is_file():
            dest = target / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
        else:
            missing.append(name)
    (target / 'manifest.json').write_text(json.dumps({'files': FILES, 'missing': missing}, indent=2))
    (target / 'displays.json').write_text(json.dumps(display_config(), indent=2))
    if not (STATE / 'original').exists():
        (STATE / 'original').write_text(str(target))
    (STATE / 'latest').write_text(str(target))
    return target


def shell_pid():
    # Match the PID on this D-Bus session: isolated tests must never restart the real desktop.
    return int(run(['qdbus6', 'org.freedesktop.DBus', '/org/freedesktop/DBus',
                    'org.freedesktop.DBus.GetConnectionUnixProcessID', 'org.kde.plasmashell']).stdout.strip())


def stop_shell():
    pid = shell_pid()
    service = run(['systemctl', '--user', 'show', 'plasma-plasmashell.service',
                   '--property=MainPID', '--value'], required=False)
    managed = service.returncode == 0 and service.stdout.strip() == str(pid)
    if managed:
        run(['systemctl', '--user', 'stop', 'plasma-plasmashell.service'])
    else:
        run(['kquitapp6', 'plasmashell'])
    deadline = time.monotonic() + 15
    while Path(f'/proc/{pid}').exists():
        try:
            if Path(f'/proc/{pid}/stat').read_text().split(') ')[1].startswith('Z'):
                break
        except FileNotFoundError:
            break
        if time.monotonic() > deadline:
            raise RuntimeError('Plasma did not stop; backup retained.')
        time.sleep(.1)
    return managed


def start_shell(managed):
    if managed:
        run(['systemctl', '--user', 'start', 'plasma-plasmashell.service'])
    else:
        STATE.mkdir(parents=True, exist_ok=True)
        with (STATE / 'plasmashell.log').open('a') as log:
            subprocess.Popen(['plasmashell'], stdout=log, stderr=log, start_new_session=True)
    wait_session(45)


def restart_shell():
    start_shell(stop_shell())


def write(filename, group, key, value):
    run(['kwriteconfig6', '--file', filename, '--group', group, '--key', key, str(value)])


def scale_displays(scale):
    if scale == 'keep':
        return
    if os.environ.get('XDG_SESSION_TYPE') != 'wayland':
        print('Fractional scale requires Wayland; current display scale retained.', flush=True)
        return
    options = [f'output.{o["name"]}.scale.{scale}' for o in display_config().get('outputs', [])
               if o.get('connected') and o.get('enabled')]
    if options:
        run(['kscreen-doctor', *options])


def apply_settings():
    run(['plasma-apply-colorscheme', 'ReferenceGraphite'])
    run(['plasma-apply-desktoptheme', 'reference-graphite'])
    for group, values in {
        'KDE': {'widgetStyle': 'kvantum', 'AnimationDurationFactor': '0.8'},
        'Icons': {'Theme': 'breeze-dark'},
        'General': {k: 'Noto Sans,10,-1,5,400,0,0,0,0,0' for k in ['font', 'menuFont', 'toolBarFont']},
        'WM': {'activeFont': 'Noto Sans,10,-1,5,500,0,0,0,0,0'},
    }.items():
        for key, value in values.items():
            write('kdeglobals', group, key, value)
    write('Kvantum/kvantum.kvconfig', 'General', 'theme', 'KvMojave')
    for key, value in {'library': 'org.kde.kwin.aurorae', 'theme': '__aurorae__svg__ReferenceGraphite',
                       'ButtonsOnLeft': 'XIA', 'ButtonsOnRight': '',
                       'BorderSize': 'Tiny', 'BorderSizeAuto': 'false'}.items():
        write('kwinrc', 'org.kde.kdecoration2', key, value)
    for key, value in {'blurEnabled': 'true', 'magiclampEnabled': 'true', 'squashEnabled': 'false'}.items():
        write('kwinrc', 'Plugins', key, value)
    run(['qdbus6', 'org.kde.KWin', '/KWin', 'org.kde.KWin.reconfigure'], required=False)


def layout_options(photo_dir):
    downloads = run(['xdg-user-dir', 'DOWNLOAD']).stdout.strip()
    if not downloads:
        downloads = str(HOME / 'Downloads')
    download_path = Path(downloads)
    download_path.mkdir(parents=True, exist_ok=True)
    icon = Path('/usr/share/icons/desktop-base/scalable/emblems/emblem-debian-white.svg')
    return {'downloadUrl': download_path.as_uri(),
            'photoUrl': Path(photo_dir).resolve().as_uri() if photo_dir else '',
            'menuIcon': str(icon) if icon.is_file() else 'start-here-kde'}


def apply(args):
    check()
    wait_session(120 if args.scheduled else 0)
    if args.scheduled:
        values = json.loads((STATE / 'pending.json').read_text())
        args.scale, args.photo_dir = values['scale'], values['photo_dir']
    # Refresh plugin discovery first, before modifying settings or removing any panel.
    restart_shell()
    wallpaper_before = evaluate(WALLPAPER_SCRIPT)
    backup = snapshot()
    print('Backup:', backup, flush=True)
    try:
        apply_settings()
        scale_displays(args.scale)
        options = layout_options(args.photo_dir)
        script = '(function(){const OPTIONS = ' + json.dumps(options, ensure_ascii=False) + ';\n' + (ROOT / 'layout.js').read_text() + '\n})();'
        result = evaluate(script)
        if 'DWEER_ISLAND_OK:' not in result:
            raise RuntimeError('Layout did not finish: ' + result)
        restart_shell()
        wallpaper_after = evaluate(WALLPAPER_SCRIPT)
        if json.loads(wallpaper_before) != json.loads(wallpaper_after):
            raise RuntimeError('Wallpaper verification failed; reverting settings.')
        report = {'version': '1.0.0', 'applied_at': datetime.now().isoformat(),
                  'backup': str(backup), 'scale': args.scale, 'wallpaper_preserved': True}
        (STATE / 'applied.json').write_text(json.dumps(report, indent=2))
        AUTOSTART.unlink(missing_ok=True)
        (STATE / 'pending.json').unlink(missing_ok=True)
        print('Done. Panels, colored icons and frameless widgets applied. Wallpaper preserved.', flush=True)
    except Exception:
        print('Apply failed. Restoring the settings saved before this attempt.', file=sys.stderr, flush=True)
        restore_backup(backup)
        raise


def restore_backup(backup):
    manifest = json.loads((backup / 'manifest.json').read_text())
    # Restore live scale through KScreen, so KWin cannot overwrite the restored file on exit.
    displays = json.loads((backup / 'displays.json').read_text()).get('outputs', [])
    connected = {o['name'] for o in display_config().get('outputs', []) if o.get('connected')}
    options = [f'output.{o["name"]}.scale.{o["scale"]}' for o in displays
               if o.get('enabled') and o.get('name') in connected and 'scale' in o]
    if options and os.environ.get('XDG_SESSION_TYPE') == 'wayland':
        run(['kscreen-doctor', *options])
    managed = stop_shell()
    try:
        for name in manifest['files']:
            destination = CONFIG / name
            if name in manifest['missing']:
                destination.unlink(missing_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup / name, destination)
    finally:
        start_shell(managed)
    run(['qdbus6', 'org.kde.KWin', '/KWin', 'org.kde.KWin.reconfigure'], required=False)


def restore(args):
    wait_session()
    pointer = STATE / ('latest' if args.latest else 'original')
    if not pointer.is_file():
        raise RuntimeError('No backup found.')
    backup = Path(pointer.read_text().strip())
    restore_backup(backup)
    AUTOSTART.unlink(missing_ok=True)
    (STATE / 'pending.json').unlink(missing_ok=True)
    print('Previous KDE restored from', backup)


def schedule(args):
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / 'pending.json').write_text(json.dumps({'scale': args.scale, 'photo_dir': args.photo_dir}))
    AUTOSTART.parent.mkdir(parents=True, exist_ok=True)
    AUTOSTART.write_text('[Desktop Entry]\nType=Application\nName=Dweer Island KDE setup\n'
                         f'Exec=/usr/bin/python3 {desktop_quote(ROOT / "theme.py")} apply --scheduled\n'
                         'OnlyShowIn=KDE;\nX-KDE-autostart-phase=2\nTerminal=false\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'check', 'apply', 'restore', 'schedule'])
    parser.add_argument('--scale', default='0.9')
    parser.add_argument('--photo-dir', default='')
    parser.add_argument('--scheduled', action='store_true')
    parser.add_argument('--latest', action='store_true', help='restore last backup instead of first')
    parser.add_argument('--interactive', action='store_true')
    args = parser.parse_args()
    code = 0
    try:
        if os.getuid() == 0:
            raise RuntimeError('Run as your normal desktop user, without sudo.')
        if args.scale != 'keep' and not (re.fullmatch(r'\d+(\.\d+)?', args.scale) and .75 <= float(args.scale) <= 3):
            raise RuntimeError('Scale must be keep or a number from 0.75 to 3.')
        if args.photo_dir and not Path(args.photo_dir).is_dir():
            raise RuntimeError('Photo directory does not exist.')
        STATE.mkdir(parents=True, exist_ok=True)
        with (STATE / 'installer.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            {'prepare': prepare, 'check': check, 'apply': lambda: apply(args),
             'restore': lambda: restore(args), 'schedule': lambda: schedule(args)}[args.action]()
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        print('Setup failed:', error, file=sys.stderr, flush=True)
        code = 1
        if args.scheduled and shutil.which('notify-send'):
            run(['notify-send', 'Dweer Island KDE', 'Setup failed. See ~/.local/state/dweer-island-kde/'], required=False)
    if args.interactive and sys.stdin.isatty():
        input('\nPress Enter to close…')
    return code


if __name__ == '__main__':
    sys.exit(main())
