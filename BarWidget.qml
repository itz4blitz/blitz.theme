import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

Panel {
  id: root
  moduleName: "blitz.theme"
  ipcTarget: "blitz.theme"

  property bool ready: false
  property string currentTheme: ""
  property var themes: []
  property string preset: "default"
  property var sliders: ({})
  property var builtinPresets: []
  property var userPresets: []
  property string saveName: ""
  property string toast: ""

  readonly property color foreground: bar ? bar.foreground : Color.foreground
  readonly property color dimColor: Qt.rgba(foreground.r, foreground.g, foreground.b, 0.55)
  readonly property color okColor: Qt.rgba(0.45, 0.82, 0.52, 1)
  readonly property string fontFamily: bar ? bar.fontFamily : Style.font.family
  readonly property string collectorPath: {
    var url = String(Qt.resolvedUrl("theme_collect.py"))
    return url.startsWith("file://") ? url.substring(7) : url
  }

  readonly property var presetLabel: {
    var all = builtinPresets.concat(userPresets)
    for (var i = 0; i < all.length; i++)
      if (all[i].id === preset) return all[i].label
    return "Default"
  }

  function apply(payload) {
    try { var d = JSON.parse(String(payload)) } catch (e) { return }
    if (d.ok !== true) return
    ready = true
    currentTheme = String(d.theme || "")
    themes = Array.isArray(d.themes) ? d.themes : []
    preset = String(d.preset || "default")
    sliders = d.sliders && typeof d.sliders === "object" ? d.sliders : ({})
    builtinPresets = Array.isArray(d.builtinPresets) ? d.builtinPresets : []
    userPresets = Array.isArray(d.userPresets) ? d.userPresets : []
  }

  function refresh() {
    if (!collectProc.running) collectProc.running = true
  }

  function run(command, args) {
    actionProc.command = ["python3", root.collectorPath, command].concat(args || [])
    actionProc.running = true
  }

  function showToast(text) {
    toast = text
    toastTimer.restart()
  }

  function triggerPress(button) {
    root.toggle()
  }

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  Process {
    id: collectProc
    command: ["python3", root.collectorPath, "state"]
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.apply(text) }
  }

  Process {
    id: actionProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        try {
          var d = JSON.parse(String(text))
          if (d.ok === true) {
            if (d.saved) root.showToast("Saved \"" + d.saved + "\"")
            else if (d.theme) root.showToast("Theme: " + d.theme)
          }
        } catch (e) { }
        root.refresh()
      }
    }
  }

  Timer {
    id: toastTimer
    interval: 2400
    onTriggered: root.toast = ""
  }

  Timer {
    interval: 15000
    running: root.opened
    repeat: true
    onTriggered: root.refresh()
  }

  Component.onCompleted: collectProc.running = true
  onOpenedChanged: if (root.opened) root.refresh()

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    labelVisible: false
    hasVisualContent: true
    pressable: true
    horizontalMargin: 8
    fixedWidth: chip.implicitWidth + scaledHorizontalMargin * 2
    onPressed: function(b) { root.triggerPress(b) }

    Row {
      id: chip
      anchors.centerIn: parent
      spacing: Style.space(8)

      Text {
        text: "◈"
        color: root.foreground
        font.family: root.fontFamily
        font.pixelSize: Style.font.body
        anchors.verticalCenter: parent.verticalCenter
      }

      Text {
        text: root.presetLabel
        color: root.preset === "default" ? root.dimColor : root.okColor
        font.family: root.fontFamily
        font.pixelSize: Style.font.caption
        font.bold: true
        anchors.verticalCenter: parent.verticalCenter
      }
    }
  }

  component PresetRow : BorderSurface {
    id: presetRow
    required property var modelData
    property bool active: root.preset === modelData.id
    width: parent.width
    height: presetInner.implicitHeight + Style.space(14)
    radius: Style.spacing.labelGap
    color: active ? Style.selectedFillFor(root.foreground, Color.accent) : "transparent"
    borderSpec: active ? Border.controlSpec("normal", root.foreground, Color.accent) : Border.none()
    signal chosen()

    MouseArea {
      anchors.fill: parent
      cursorShape: Qt.PointingHandCursor
      onClicked: presetRow.chosen()
    }

    Column {
      id: presetInner
      anchors.left: parent.left
      anchors.right: parent.right
      anchors.verticalCenter: parent.verticalCenter
      anchors.margins: Style.space(8)
      spacing: Style.space(2)

      Text {
        width: parent.width
        text: presetRow.modelData.label
        color: presetRow.active ? root.foreground : root.dimColor
        font.family: root.fontFamily
        font.pixelSize: Style.font.bodySmall
        font.bold: true
        elide: Text.ElideRight
      }

      Text {
        width: parent.width
        text: presetRow.modelData.description || ""
        color: root.dimColor
        font.family: root.fontFamily
        font.pixelSize: Style.font.caption
        elide: Text.ElideRight
        visible: text !== ""
      }
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    contentWidth: panel.fittedContentWidth(Style.space(520))
    contentHeight: panel.fittedContentHeight(Style.space(640), Style.space(760))

    Item {
      anchors.fill: parent

      Column {
        anchors.fill: parent
        spacing: Style.space(12)

        PanelHero {
          width: parent.width
          title: "Style"
          detail: root.currentTheme || ""
          meta: root.presetLabel + (root.toast !== "" ? " · " + root.toast : "")
          foreground: root.foreground
          fontFamily: root.fontFamily
        }

        Flickable {
          id: body
          width: parent.width
          height: parent.height - y
          clip: true
          contentWidth: width
          contentHeight: bodyCol.implicitHeight
          boundsBehavior: Flickable.StopAtBounds

          Column {
            id: bodyCol
            width: body.width
            spacing: Style.space(10)

            PanelSectionHeader {
              text: "STYLE PRESETS"
              foreground: root.foreground
              fontFamily: root.fontFamily
            }

            PresetRow {
              modelData: ({ id: "default", label: "Theme Default", description: "Drop every override — exactly what the theme ships." })
              active: root.preset === "default"
              onChosen: root.run("apply", ["default"])
            }

            Repeater {
              model: root.builtinPresets.filter(function(p) { return p.id !== "default" })
              delegate: PresetRow {
                onChosen: root.run("apply", [modelData.id])
              }
            }

            Repeater {
              model: root.userPresets
              delegate: PresetRow {
                onChosen: root.run("apply", [modelData.id])
              }
            }

            Row {
              width: parent.width
              spacing: Style.space(8)

              TextField {
                id: saveField
                width: parent.width - saveButton.width - parent.spacing
                placeholderText: "Name the current look…"
                text: root.saveName
                onTextChanged: root.saveName = text
              }

              Button {
                id: saveButton
                text: "Save"
                foreground: root.foreground
                enabled: root.saveName.replace(/\s/g, "") !== ""
                onClicked: {
                  root.run("save", [root.saveName])
                  root.saveName = ""
                }
              }
            }

            PanelSectionHeader {
              text: "LIVE CONTROLS"
              foreground: root.foreground
              fontFamily: root.fontFamily
            }

            Row {
              width: parent.width
              spacing: Style.space(10)

              Text {
                text: "Bar opacity"
                id: barOpLabel
                color: root.dimColor
                font.family: root.fontFamily
                font.pixelSize: Style.font.caption
                width: parent.width * 0.3
                anchors.verticalCenter: parent.verticalCenter
              }

              PanelSlider {
                bar: root.bar
                width: parent.width - barOpLabel.width - parent.spacing
                minimum: 0
                maximum: 1
                step: 0.05
                value: root.sliders["bar-alpha"] !== undefined ? root.sliders["bar-alpha"] : 1
                onReleased: function(v) { root.run("slide", ["bar-alpha", String(v)]) }
              }
            }

            Row {
              width: parent.width
              spacing: Style.space(10)

              Text {
                text: "Panel opacity"
                id: panelOpLabel
                color: root.dimColor
                font.family: root.fontFamily
                font.pixelSize: Style.font.caption
                width: parent.width * 0.3
                anchors.verticalCenter: parent.verticalCenter
              }

              PanelSlider {
                bar: root.bar
                width: parent.width - panelOpLabel.width - parent.spacing
                minimum: 0
                maximum: 1
                step: 0.05
                value: root.sliders["panel-alpha"] !== undefined ? root.sliders["panel-alpha"] : 1
                onReleased: function(v) { root.run("slide", ["panel-alpha", String(v)]) }
              }
            }

            Row {
              width: parent.width
              spacing: Style.space(10)

              Text {
                text: "Bar text dim"
                id: textDimLabel
                color: root.dimColor
                font.family: root.fontFamily
                font.pixelSize: Style.font.caption
                width: parent.width * 0.3
                anchors.verticalCenter: parent.verticalCenter
              }

              PanelSlider {
                bar: root.bar
                width: parent.width - textDimLabel.width - parent.spacing
                minimum: 0
                maximum: 0.6
                step: 0.05
                value: root.sliders["text-dim"] !== undefined ? root.sliders["text-dim"] : 0
                onReleased: function(v) { root.run("slide", ["text-dim", String(v)]) }
              }
            }

            Row {
              width: parent.width
              spacing: Style.space(10)

              Text {
                text: "Font size"
                id: fontSizeLabel
                color: root.dimColor
                font.family: root.fontFamily
                font.pixelSize: Style.font.caption
                width: parent.width * 0.3
                anchors.verticalCenter: parent.verticalCenter
              }

              PanelSlider {
                bar: root.bar
                width: parent.width - fontSizeLabel.width - parent.spacing
                minimum: 8
                maximum: 20
                step: 1
                integer: true
                value: root.sliders["font-size"] !== undefined ? root.sliders["font-size"] : 12
                onReleased: function(v) { root.run("slide", ["font-size", String(Math.round(v))]) }
              }
            }

            PanelSectionHeader {
              text: "OMARCHY THEME"
              foreground: root.foreground
              fontFamily: root.fontFamily
            }

            Dropdown {
              width: parent.width
              label: "Theme"
              value: root.currentTheme
              options: root.themes
              onChanged: root.run("set-theme", [value])
            }

            Text {
              width: parent.width
              text: "Presets restyle the bar and every dropdown at once and survive theme switches. Slider moves stack on top; Save snapshots the combination under a name."
              color: root.dimColor
              font.family: root.fontFamily
              font.pixelSize: Style.font.caption
              wrapMode: Text.WordWrap
            }
          }
        }
      }
    }
  }
}
