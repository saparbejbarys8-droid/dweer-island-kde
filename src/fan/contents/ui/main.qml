// SPDX-License-Identifier: GPL-3.0-or-later
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.kirigami as Kirigami
import QtCore

PlasmoidItem {
    id: root
    property Item popupAnchor: null
    Plasmoid.title: "Загрузки"
    Plasmoid.icon: "folder-downloads"
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    Plasmoid.status: popup.visible ? PlasmaCore.Types.RequiresAttentionStatus : PlasmaCore.Types.ActiveStatus
    toolTipMainText: "Загрузки"
    toolTipSubText: "Последние файлы веером · нажми, чтобы раскрыть"
    preferredRepresentation: fullRepresentation
    Plasmoid.onActivated: popup.visible = !popup.visible

    fullRepresentation: MouseArea {
        id: compactIcon
        Component.onCompleted: root.popupAnchor = compactIcon
        Component.onDestruction: { if (root.popupAnchor === compactIcon) root.popupAnchor = null; }
        implicitWidth: 48
        implicitHeight: 48
        Layout.minimumWidth: 40
        Layout.minimumHeight: 40
        hoverEnabled: true
        activeFocusOnTab: true
        cursorShape: Qt.PointingHandCursor
        onClicked: popup.visible = !popup.visible
        Keys.onSpacePressed: popup.visible = !popup.visible
        Keys.onReturnPressed: popup.visible = !popup.visible
        Accessible.role: Accessible.Button
        Accessible.name: "Загрузки веером"
        Kirigami.Icon {
            anchors.fill: parent
            anchors.margins: 4
            source: "folder-downloads"
            active: parent.containsMouse || popup.visible
        }
    }

    PlasmaCore.Dialog {
        id: popup
        visualParent: root.popupAnchor
        location: PlasmaCore.Types.BottomEdge
        type: PlasmaCore.Dialog.PopupMenu
        flags: Qt.WindowStaysOnTopHint
        hideOnWindowDeactivate: true
        backgroundHints: PlasmaCore.Dialog.NoBackground
        onVisibleChanged: { if (visible) requestActivate(); }
        mainItem: FanView {
            folderUrl: Plasmoid.configuration.folderUrl || StandardPaths.writableLocation(StandardPaths.DownloadLocation)
            open: popup.visible
            onDismissed: popup.visible = false
        }
    }
}
