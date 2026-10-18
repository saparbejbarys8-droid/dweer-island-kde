#!/usr/bin/python3
"""Build local, vector-based KDE assets inspired by the user's video."""
from pathlib import Path
import configparser
import gzip
import json
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
import os
SHARE = Path(os.environ.get('ISLAND_BUILD_DIR', ROOT/'build')) / 'share'
NAME = 'ReferenceGraphite'

def put(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')

def svg(content, w=64, h=64):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{content}</svg>\n'

def panel_frame(prefix, x, y, radius, opacity, color='#292929'):
    p = prefix + '-' if prefix else ''
    r = max(radius, 1)
    fill = f'fill="{color}" fill-opacity="{opacity}"'
    # Nine independently scalable pieces; rounded corners belong only to the dock.
    parts = [f'<rect id="{p}center" x="{x+r}" y="{y+r}" width="40" height="24" {fill}/>']
    pieces = {'top': (x+r,y,40,r), 'bottom': (x+r,y+r+24,40,r),
              'left': (x,y+r,r,24), 'right': (x+r+40,y+r,r,24)}
    for key,(a,b,w,h) in pieces.items():
        parts.append(f'<rect id="{p}{key}" x="{a}" y="{b}" width="{w}" height="{h}" {fill}/>')
    curves = {
        'topleft': f'M {r},0 V {r} H 0 A {r},{r} 0 0 1 {r},0 Z',
        'topright': f'M 0,0 A {r},{r} 0 0 1 {r},{r} H 0 Z',
        'bottomleft': f'M 0,0 H {r} V {r} A {r},{r} 0 0 1 0,0 Z',
        'bottomright': f'M 0,0 H {r} A {r},{r} 0 0 1 0,{r} Z'}
    positions = {'topleft':(x,y), 'topright':(x+r+40,y),
                 'bottomleft':(x,y+r+24), 'bottomright':(x+r+40,y+r+24)}
    for key,(a,b) in positions.items():
        if radius:
            parts.append(f'<path id="{p}{key}" transform="translate({a} {b})" d="{curves[key]}" {fill}/>')
        else:
            parts.append(f'<rect id="{p}{key}" x="{a}" y="{b}" width="{r}" height="{r}" {fill}/>')
    for key in ['top','bottom','left','right']:
        margin = 6 if prefix == 'floating' else 3
        parts.append(f'<rect id="{p}hint-{key}-margin" x="{x+90}" y="{y}" width="{margin}" height="{margin}" fill="#f0f"/>')
    return ''.join(parts)


def make_colors_and_plasma():
    color = configparser.ConfigParser(interpolation=None)
    color.optionxform = str
    color.read('/usr/share/color-schemes/KvMojave.colors')
    color['General']['Name'] = 'Reference Graphite'
    color['General']['ColorScheme'] = NAME
    for section in color.sections():
        if section.startswith('Colors:'):
            color[section]['ForegroundActive'] = '220,220,220'
            color[section]['ForegroundNegative'] = '255,103,103'
            color[section]['ForegroundNeutral'] = '235,194,105'
            color[section]['ForegroundPositive'] = '113,202,136'
    for section in ['Colors:Header','Colors:Complementary']:
        color[section] = dict(color['Colors:Window'])
    target = SHARE / 'color-schemes' / f'{NAME}.colors'
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('w') as f:
        color.write(f,space_around_delimiters=False)
    theme = SHARE / 'plasma/desktoptheme/reference-graphite'
    if not theme.exists():
        shutil.copytree('/usr/share/plasma/desktoptheme/default', theme)
    put(theme/'metadata.json',json.dumps({'KPlugin':{'Id':'reference-graphite',
        'Name':'Reference Graphite','Description':'Graphite desktop with a rounded floating dock',
        'Version':'1.0','License':'GPL-2.0-or-later','Authors':[{'Name':'dweer'}]},
        'X-Plasma-API':'5.0'},indent=2))
    shutil.copy2(target,theme/'colors')
    for solid in [False,True]:
        content = panel_frame('',0,0,0,1 if solid else .9)
        content += panel_frame('floating',0,60,13,1 if solid else .82)
        target_panel = theme / ('solid/widgets/panel-background.svg' if solid else 'widgets/panel-background.svg')
        put(target_panel,svg(content,130,130))
        compressed = target_panel.with_suffix('.svgz')
        if compressed.exists():
            compressed.unlink()
    put(theme/'plasmarc','[Settings]\nFallbackTheme=default\n\n[BlurBehindEffect]\nenabled=true\n\n[ContrastEffect]\nenabled=false\n')

def make_decoration():
    target = SHARE/'aurorae/themes'/NAME
    put(target/'metadata.json',json.dumps({'KPlugin':{'Id':NAME,'Name':'Reference Graphite',
        'Version':'1.0','License':'GPL-3.0-or-later','Authors':[{'Name':'dweer'}]},
        'KPackageStructure':'KWin/Aurorae'},indent=2))
    put(target/'metadata.desktop', '[Desktop Entry]\nName=Reference Graphite\nComment=Dark titlebars with traffic-light buttons\nX-KDE-PluginInfo-Author=dweer\nX-KDE-PluginInfo-Name=ReferenceGraphite\nX-KDE-PluginInfo-Version=1.0\nX-KDE-PluginInfo-License=GPL-3.0\n')
    put(target/f'{NAME}rc', '''[General]
ActiveTextColor=238,238,238
InactiveTextColor=151,151,151
TitleAlignment=Center
TitleVerticalAlignment=Center
Animation=120
Shadow=false
UseTextShadow=false

[Layout]
BorderLeft=1
BorderRight=1
BorderBottom=1
BorderTop=0
TitleHeight=24
TitleEdgeTop=3
TitleEdgeBottom=3
TitleEdgeLeft=12
TitleEdgeRight=12
TitleEdgeTopMaximized=3
TitleEdgeBottomMaximized=3
TitleEdgeLeftMaximized=12
TitleEdgeRightMaximized=12
TitleBorderLeft=12
TitleBorderRight=12
ButtonWidth=16
ButtonHeight=16
ButtonSpacing=6
ButtonMarginTop=4
ButtonMarginTopMaximized=4
PaddingLeft=0
PaddingRight=0
PaddingTop=0
PaddingBottom=0
''')
    pieces=[]
    for i,(prefix,bg) in enumerate([('decoration','#302f2e'),('decoration-inactive','#2c2b2a'),('mask','#000000')]):
        y=i*110
        # Upper corners are rounded; the client area stays completely transparent.
        pieces.append(f'<path id="{prefix}-topleft" d="M 0,{y+30} V {y+10} Q 0,{y} 10,{y} V {y+30} Z" fill="{bg}"/>')
        pieces.append(f'<rect id="{prefix}-top" x="10" y="{y}" width="120" height="30" fill="{bg}"/>')
        pieces.append(f'<path id="{prefix}-topright" d="M 130,{y} Q 140,{y} 140,{y+10} V {y+30} H 130 Z" fill="{bg}"/>')
        for part,x,dy,w,h in [('left',0,30,1,60),('right',139,30,1,60),('bottomleft',0,90,1,1),('bottom',1,90,138,1),('bottomright',139,90,1,1)]:
            pieces.append(f'<rect id="{prefix}-{part}" x="{x}" y="{y+dy}" width="{w}" height="{h}" fill="{bg}"/>')
        pieces.append(f'<rect id="{prefix}-center" x="1" y="{y+30}" width="138" height="60" fill="{bg}" fill-opacity="{1 if prefix == "mask" else 0}"/>')
    decoration_svg=svg(''.join(pieces),140,330)
    put(target/'decoration.svg',decoration_svg)
    (target/'decoration.svgz').write_bytes(gzip.compress(decoration_svg.encode('utf-8')))
    glyphs={'close':'M 6,6 L 10,10 M 10,6 L 6,10',
            'minimize':'M 5.5,8 H 10.5',
            'maximize':'M 5.5,9.5 V 5.5 H 9.5 M 10.5,6.5 V 10.5 H 6.5',
            'restore':'M 6,6 H 10 V 10 H 6 Z'}
    for name,color in [('close','#ff6159'),('minimize','#ffbd2e'),('maximize','#28ca42'),('restore','#28ca42')]:
        states=[]
        for i,state in enumerate(['active','hover','pressed','inactive','hover-inactive','pressed-inactive','deactivated','deactivated-inactive']):
            fill='#666666' if state in ['inactive','deactivated','deactivated-inactive'] else color
            states.append(f'<g id="{state}-center" transform="translate({i*20} 0)"><rect width="16" height="16" fill="none"/><circle cx="8" cy="8" r="6" fill="{fill}" stroke="#000000" stroke-opacity=".22" stroke-width=".7"/>')
            if state in ['hover','pressed','hover-inactive','pressed-inactive']:
                states.append(f'<path d="{glyphs[name]}" fill="none" stroke="#292929" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>')
            states.append('</g>')
        put(target/f'{name}.svg',svg(''.join(states),160,16))



if __name__ == '__main__':
    make_colors_and_plasma()
    make_decoration()
    for path in (SHARE/'aurorae/themes'/NAME).glob('*.svg'):
        ET.parse(path)
    print('Built Plasma theme, color scheme and Aurorae decoration. Wallpaper unchanged.')
