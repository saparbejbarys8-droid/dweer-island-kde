// SPDX-License-Identifier: GPL-3.0-or-later
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls as Controls
import Qt.labs.folderlistmodel
import org.kde.kirigami as Kirigami

Item {
    id: root
    property url folderUrl: ""
    property bool open: true
    // Repeater follows row insertions reliably with Debian's Qt 6.8 model.
    readonly property int entryCount: entries.count
    readonly property string firstEntryName: entryCount ? folderModel.get(0,"fileName") : ""
    readonly property int folderStatus: folderModel.status
    readonly property url resolvedFolder: folderModel.folder
    readonly property int visibleEntries: Math.min(entryCount, 8)
    implicitWidth: 350
    implicitHeight: Math.max(140, visibleEntries * 44 + 80)
    signal dismissed()

    FolderListModel {
        id: folderModel
        folder: root.folderUrl
        showDotAndDotDot: false
        showHidden: false
        sortField: FolderListModel.Time
        sortReversed: false
    }

    function iconFor(name, isDir) {
        if (isDir) return "folder";
        const ext = name.split('.').pop().toLowerCase();
        if (["png","jpg","jpeg","webp","svg","gif"].indexOf(ext) >= 0) return "image-x-generic";
        if (["mp4","mkv","mov","webm"].indexOf(ext) >= 0) return "video-x-generic";
        if (["mp3","flac","ogg","wav"].indexOf(ext) >= 0) return "audio-x-generic";
        if (ext === "pdf") return "application-pdf";
        if (["zip","tar","gz","7z","rar","deb"].indexOf(ext) >= 0) return "package-x-generic";
        return "text-x-generic";
    }

    Repeater {
        id: entries
        model: folderModel
        delegate: Item {
            id: entry
            required property int index
            required property string fileName
            required property url fileUrl
            required property bool fileIsDir
            visible: index < 8
            width: 300
            height: 38
            x: 16 + Math.pow(Math.min(index,7) / 7, 2) * 22
            y: root.open ? root.height - 87 - index * 44 : root.height - 52
            rotation: root.open ? -Math.min(index,7) * 1.05 : 0
            opacity: root.open ? 1 : 0
            transformOrigin: Item.BottomRight
            Behavior on y { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
            Behavior on rotation { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
            Behavior on opacity { NumberAnimation { duration: 160 } }

            Rectangle {
                anchors.right: fileIcon.left
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                width: 245
                height: 28
                radius: 14
                color: mouse.containsMouse ? "#ffffff" : "#e7e7e4"
                border.color: "#a5a5a1"
                Text {
                    anchors.fill: parent
                    anchors.leftMargin: 13
                    anchors.rightMargin: 13
                    text: entry.fileName
                    color: "#292929"
                    font.family: "Noto Sans"
                    font.pixelSize: 12
                    elide: Text.ElideMiddle
                    verticalAlignment: Text.AlignVCenter
                    horizontalAlignment: Text.AlignRight
                    textFormat: Text.PlainText
                }
            }
            Kirigami.Icon {
                id: fileIcon
                width: 34
                height: 34
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                source: root.iconFor(entry.fileName, entry.fileIsDir)
            }
            MouseArea {
                id: mouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    Qt.openUrlExternally(entry.fileUrl);
                    root.dismissed();
                }
                Accessible.role: Accessible.Button
                Accessible.name: entry.fileName
                Controls.ToolTip.visible: containsMouse
                Controls.ToolTip.text: entry.fileName
                Controls.ToolTip.delay: 700
            }
        }
    }

    Text {
        visible: root.entryCount === 0
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 25
        text: "В «Загрузках» пока пусто"
        color: "#eeeeee"
        font.pixelSize: 13
    }

    Rectangle {
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 8
        anchors.right: parent.right
        anchors.rightMargin: 18
        width: 300
        height: 38
        radius: 16
        color: openFolder.containsMouse ? "#505050" : "#363636"
        border.color: "#757575"
        Text {
            anchors.centerIn: parent
            text: "Открыть «Загрузки»  ↗"
            color: "#eeeeee"
            font.family: "Noto Sans"
            font.pixelSize: 13
        }
        MouseArea {
            id: openFolder
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                Qt.openUrlExternally(root.folderUrl);
                root.dismissed();
            }
            Accessible.role: Accessible.Button
            Accessible.name: "Открыть папку Загрузки"
        }
    }
}
