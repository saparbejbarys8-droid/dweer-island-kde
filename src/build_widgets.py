#!/usr/bin/python3
"""Local frameless variants of the user's existing KDE widgets."""
from pathlib import Path
import shutil,json

def replace_once(text, old, new):
    if old not in text:
        raise RuntimeError("Unsupported Plasma source: missing patch anchor " + repr(old))
    return text.replace(old,new,1)


ROOT=Path(__file__).resolve().parent
import os
BUILD=Path(os.environ.get('ISLAND_BUILD_DIR', ROOT/'build'))
variants=[
    ('org.kde.plasma.mediaframe','local.reference.photo','Фото без рамки'),
    ('org.kde.plasma.mediacontroller','local.reference.media','Музыка без рамки'),
    ('org.kde.plasma.networkmanagement','local.reference.network','Сеть без рамки')]
for source,plugin,name in variants:
    target=BUILD/'widgets'/plugin
    shutil.copytree(Path('/usr/share/plasma/plasmoids')/source,target,dirs_exist_ok=True)
    metadata=json.loads((target/'metadata.json').read_text())
    metadata['KPlugin']['Id']=plugin
    metadata['KPlugin']['Name']=name
    metadata['KPlugin']['Name[ru]']=name
    metadata['KPlugin']['Description']='Local frameless variant of '+source
    (target/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
    qml=target/'contents/ui/main.qml'
    text=qml.read_text()
    if source=='org.kde.plasma.mediaframe':
        text=replace_once(text,'import QtQuick\n','import QtQuick\nimport Qt5Compat.GraphicalEffects as Effects\n')
        text=replace_once(text,'PlasmaCore.Types.DefaultBackground | PlasmaCore.Types.ConfigurableBackground','PlasmaCore.Types.NoBackground')
        text=replace_once(text,'id: imageView\n','''id: imageView
            clip: true
            layer.enabled: true
            layer.effect: Effects.OpacityMask {
                maskSource: Rectangle {
                    width: imageView.width
                    height: imageView.height
                    radius: 16
                    color: "white"
                }
            }
''')
    else:
        text=replace_once(text,'PlasmoidItem {','PlasmoidItem {\n    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground')
    qml.write_text(text)
print('Built local frameless photo, media and network widgets.')
