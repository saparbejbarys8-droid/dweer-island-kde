#!/usr/bin/python3
"""Native KDE panel with transparent gaps and a truly centered clock capsule."""
from pathlib import Path
import shutil,json

def replace_once(text, old, new):
    if old not in text:
        raise RuntimeError("Unsupported Plasma source: missing patch anchor " + repr(old))
    return text.replace(old,new,1)


ROOT=Path(__file__).resolve().parent
import os
BUILD=Path(os.environ.get('ISLAND_BUILD_DIR', ROOT/'build'))
target=BUILD/'widgets/local.reference.islandpanel'
shutil.copytree('/usr/share/plasma/plasmoids/org.kde.panel',target,dirs_exist_ok=True)
metadata=json.loads((target/'metadata.json').read_text())
metadata['KPlugin']['Id']='local.reference.islandpanel'
metadata['KPlugin']['Name']='Island Top Panel'
metadata['KPlugin']['Name[ru]']='Верхняя панель с островком'
metadata['KPlugin']['Description']='Transparent panel with separate capsules and a centered clock'
(target/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
qml=target/'contents/ui/main.qml'
text=qml.read_text()
extra='''
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    property real islandLeftGap: 100
    property real islandRightGap: 100
    property int islandClockIndex: 3
    property bool islandOrderReady: false
    readonly property int islandClockWidth: 132
    function balanceIsland() {
        if (!islandOrderReady && appletsModel.count >= 6) {
            const entries=[];
            for (let i=0; i<appletsModel.count; ++i) entries.push(appletsModel.get(i).applet);
            const find = name => entries.find(a => a?.plasmoid?.pluginName === name);
            const gaps=entries.filter(a => a?.plasmoid?.pluginName === "org.kde.plasma.panelspacer");
            const order=[find("org.kde.plasma.kickoff"),find("org.kde.plasma.appmenu"),gaps[0],
                find("org.kde.plasma.digitalclock"),gaps[1],find("org.kde.plasma.systemtray")];
            if (order.every(a => a !== undefined)) {
                for (let i=0; i<order.length; ++i) {
                    for (let j=i; j<appletsModel.count; ++j) {
                        if (appletsModel.get(j).applet === order[i]) {
                            if (j !== i) appletsModel.move(j,i,1);
                            break;
                        }
                    }
                }
                islandOrderReady=true;
                LayoutManager.save();
            }
        }
        const items=currentLayout.children.filter(c => c?.isAppletContainer && c.visible);
        const clock=items.find(c => c?.applet?.plasmoid?.pluginName === "org.kde.plasma.digitalclock");
        if (!clock) return;
        islandClockIndex=clock.index;
        const before=items.filter(c => c.index < clock.index);
        const after=items.filter(c => c.index > clock.index);
        const nonGapWidth = a => a.reduce((n,c) => n+(c?.applet?.plasmoid?.pluginName === "org.kde.plasma.panelspacer" ? 0 : c.width),0);
        const half=(currentLayout.width-clock.width)/2;
        islandLeftGap=Math.max(0,half-nonGapWidth(before)-before.length*currentLayout.columnSpacing);
        islandRightGap=Math.max(0,half-nonGapWidth(after)-after.length*currentLayout.columnSpacing);
    }
    Timer {
        interval: 250
        repeat: true
        running: true
        triggeredOnStart: true
        onTriggered: root.balanceIsland()
    }
'''
text=replace_once(text,'    id: root\n','    id: root\n'+extra)
text=replace_once(text,'Containment.onAppletAdded: (applet, geometry) => {','Containment.onAppletAdded: (applet, geometry) => {\n        root.islandOrderReady=false;')
text=replace_once(text,'                property Item dragging\n','''                property Item dragging
                readonly property bool islandClock: applet?.plasmoid?.pluginName === "org.kde.plasma.digitalclock"
                readonly property bool islandGap: applet?.plasmoid?.pluginName === "org.kde.plasma.panelspacer"
                readonly property real islandGapWidth: index < root.islandClockIndex ? root.islandLeftGap : root.islandRightGap
                Rectangle {
                    anchors.centerIn: parent
                    width: container.islandClock ? root.islandClockWidth : parent.width
                    height: parent.height
                    radius: height/2
                    color: container.islandClock ? "#050505" : "#202020"
                    visible: !container.islandGap && width > 1
                    z: -1
                }
''')
for side,value in [('top',6),('bottom',6),('left',0),('right',0)]:
    text=replace_once(text,f"Layout.{side}Margin: getMargins('{side}')",f"Layout.{side}Margin: {value}")
text=replace_once(text,'                Layout.fillWidth: true\n','                Layout.fillWidth: !islandGap\n')
for metric in ['minimum','preferred','maximum']:
    text=replace_once(text,f'Layout.{metric}Width: root.isHorizontal ?', f'Layout.{metric}Width: islandGap ? islandGapWidth : root.isHorizontal ?')
text=replace_once(text,'columnSpacing: Kirigami.Units.smallSpacing','columnSpacing: 8')
qml.write_text(text)
print('Built transparent native panel with balanced clock and per-widget capsules.')
