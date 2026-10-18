#!/usr/bin/env python3
"""Integration check in a separate virtual Wayland session and empty HOME."""
from pathlib import Path
import importlib.util
import json
import os
import subprocess
import sys
import time

root = Path(os.environ['XDG_DATA_HOME']) / 'dweer-island-kde/src'
spec = importlib.util.spec_from_file_location('theme', root / 'theme.py')
theme = importlib.util.module_from_spec(spec)
spec.loader.exec_module(theme)


def command(*args):
    subprocess.run([sys.executable, str(root / 'theme.py'), *args], check=True)


def state():
    return json.loads(theme.evaluate('''print(JSON.stringify({
        panels:panels().map(p=>({id:p.id,type:p.type,location:p.location,
            widgets:p.widgets().map(w=>w.type)})),
        desktops:desktops().map(d=>({id:d.id,widgets:d.widgets().map(w=>({id:w.id,type:w.type}))}))
    }));'''))


before = state()
wallpaper_before = json.loads(theme.evaluate(theme.WALLPAPER_SCRIPT))
scale_before = theme.display_config()
assert before['panels'], 'Vanilla Plasma did not create a default panel'
# A second unrelated desktop widget must survive installation.
theme.evaluate('desktops()[0].addWidget("org.kde.plasma.analogclock",24,100,100,100);')
unrelated = state()['desktops'][0]['widgets'][-1]['id']

for attempt in range(2):
    command('apply', '--scale', '0.9')
    time.sleep(2)
    current = state()
    assert len(current['panels']) == 2, current
    top = next(p for p in current['panels'] if p['location'] == 'top')
    dock = next(p for p in current['panels'] if p['location'] == 'bottom')
    assert top['type'] == 'local.reference.islandpanel', top
    assert len(top['widgets']) == 6, top
    assert 'local.reference.downloadfan' in dock['widgets'], dock
    widgets = current['desktops'][0]['widgets']
    assert len(widgets) == 5, widgets
    assert unrelated in [w['id'] for w in widgets], widgets
    for plugin in ['local.reference.photo', 'local.reference.media', 'local.reference.network']:
        assert sum(w['type'] == plugin for w in widgets) == 1, widgets
    assert json.loads(theme.evaluate(theme.WALLPAPER_SCRIPT)) == wallpaper_before
    outputs = theme.display_config().get('outputs', [])
    assert outputs and all(abs(o['scale'] - .9) < .01 for o in outputs if o['enabled'])
    print(f'Apply {attempt + 1}: layout, widget preservation, wallpaper and scale verified', flush=True)

command('restore')
restored = state()
assert restored['panels'] == before['panels'], restored
assert json.loads(theme.evaluate(theme.WALLPAPER_SCRIPT)) == wallpaper_before
for old in scale_before.get('outputs', []):
    current = next(o for o in theme.display_config()['outputs'] if o['name'] == old['name'])
    assert abs(current['scale'] - old['scale']) < .01
print('Restore: original panels, wallpaper and display scale verified', flush=True)

# Confirm one-shot installation from a console uses the same options and removes its job on success.
command('schedule', '--scale', 'keep')
assert theme.AUTOSTART.is_file()
command('apply', '--scheduled')
assert not theme.AUTOSTART.exists()
assert not (theme.STATE / 'pending.json').exists()
print('First-login setup: applied once and removed its autostart job', flush=True)
