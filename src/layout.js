// SPDX-License-Identifier: GPL-3.0-or-later
// OPTIONS is supplied as JSON by theme.py. Wallpaper settings are never touched.
(function () {
    const required = ["org.kde.plasma.kickoff", "org.kde.plasma.appmenu",
        "org.kde.plasma.systemtray", "org.kde.plasma.digitalclock",
        "org.kde.plasma.panelspacer", "org.kde.plasma.icontasks",
        "org.kde.plasma.trash", "org.kde.plasma.marginsseparator",
        "local.reference.downloadfan", "local.reference.photo",
        "local.reference.media", "local.reference.network"];
    for (const type of required) {
        if (knownWidgetTypes.indexOf(type) < 0) throw new Error("Missing widget: " + type);
    }
    if (knownPanelTypes.indexOf("local.reference.islandpanel") < 0)
        throw new Error("Island panel package has not loaded");
    const ds = desktops();
    const screens = [];
    for (const d of ds) if (d.screen >= 0 && screens.indexOf(d.screen) < 0) screens.push(d.screen);
    if (!screens.length) throw new Error("No connected KDE desktops");
    const previous = panels();
    const created = [];
    const addedWidgets = [];
    const menus = [];
    function config(widget, group, values) {
        widget.currentConfigGroup = group;
        for (const key in values) widget.writeConfig(key, values[key]);
    }
    function spacer(panel, expanding, length) {
        const w = panel.addWidget("org.kde.plasma.panelspacer");
        config(w, ["General"], {expanding: expanding, length: length});
        return w;
    }
    try {
        for (const screen of screens) {
            const top = new Panel("local.reference.islandpanel");
            created.push(top);
            top.screen = screen;
            top.location = "top";
            top.height = 42;
            top.lengthMode = "fill";
            top.floating = false;
            top.hiding = "none";
            top.alignment = "center";
            config(top, [], {DweerIslandRole: "top"});
            const menu = top.addWidget("org.kde.plasma.kickoff");
            config(menu, ["General"], {icon: OPTIONS.menuIcon});
            menus.push(menu);
            top.addWidget("org.kde.plasma.appmenu");
            spacer(top, true, -1);
            const clock = top.addWidget("org.kde.plasma.digitalclock");
            config(clock, ["Appearance"], {showDate: false, showSeconds: 1, use24hFormat: 2,
                showLocalTimezone: false, autoFontAndSize: false,
                fontFamily: "Noto Sans", fontSize: 11, fontWeight: 500});
            spacer(top, true, -1);
            top.addWidget("org.kde.plasma.systemtray");

            const dock = new Panel;
            created.push(dock);
            dock.screen = screen;
            dock.location = "bottom";
            dock.height = 62;
            dock.alignment = "center";
            dock.lengthMode = "fit";
            dock.floating = true;
            dock.hiding = "dodgewindows";
            config(dock, [], {DweerIslandRole: "dock"});
            spacer(dock, false, 8);
            const tasks = dock.addWidget("org.kde.plasma.icontasks");
            const apps = ["org.kde.dolphin.desktop", "google-chrome.desktop", "kitty.desktop",
                "spotify.desktop", "firefox-esr.desktop", "systemsettings.desktop",
                "org.kde.discover.desktop", "org.telegram.desktop.desktop", "org.telegram.desktop"];
            const launchers = [];
            for (const app of apps) if (applicationExists(app)) launchers.push("applications:" + app);
            config(tasks, ["General"], {launchers: launchers, fill: false, iconSpacing: 2,
                groupingStrategy: 1, onlyGroupWhenFull: false, showOnlyCurrentDesktop: false});
            dock.addWidget("org.kde.plasma.marginsseparator");
            const fan = dock.addWidget("local.reference.downloadfan");
            config(fan, ["General"], {folderUrl: OPTIONS.downloadUrl});
            dock.addWidget("org.kde.plasma.trash");
            spacer(dock, false, 8);
            if (top.widgetIds.length !== 6 || dock.widgetIds.length !== 6)
                throw new Error("Incomplete panels");
        }

        for (const desktop of ds) {
            if (desktop.screen < 0) continue;
            const screen = screenGeometry(desktop.screen);
            const photoWidth = Math.min(400, Math.round(screen.width * 0.24));
            const photoHeight = Math.round(photoWidth * 0.6);
            const right = screen.width - photoWidth - 24;
            const top = 56;
            const oldManaged = desktop.widgets().filter(w => {
                w.currentConfigGroup = [];
                return w.readConfig("DweerIslandWidget", false) === true ||
                    w.readConfig("DweerIslandWidget", "false") === "true";
            });
            function add(type, x, y, width, height) {
                const w = desktop.addWidget(type, x, y, width, height);
                addedWidgets.push(w);
                w.userBackgroundHints = "NoBackground";
                config(w, [], {DweerIslandWidget: true});
                return w;
            }
            add("org.kde.plasma.digitalclock", Math.round(screen.width / 2 - 88), top, 176, 80);
            const photo = add("local.reference.photo", right, top, photoWidth, photoHeight);
            config(photo, ["General"], {interval: 5, fillMode: 2, showCountdown: false, pauseOnMouseOver: true});
            if (OPTIONS.photoUrl) config(photo, ["Paths"], {
                pathList: [JSON.stringify({path: OPTIONS.photoUrl, type: "folder"})]
            });
            add("local.reference.media", 24, Math.max(top, screen.height - 220), photoWidth - 96, 96);
            add("local.reference.network", right + photoWidth - 80, top + photoHeight + 16, 80, 96);
            for (const w of oldManaged) w.remove();
        }
    } catch (error) {
        for (const w of addedWidgets) w.remove();
        for (const p of created) p.remove();
        throw error;
    }
    // Desktop files, unrelated widgets, and every wallpaper setting stay as they were.
    for (const panel of previous) panel.remove();
    if (menus.length) menus[0].globalShortcut = "Alt+F1";
    print("DWEER_ISLAND_OK:" + created.length);
})();
