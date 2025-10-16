#!/bin/bash

set -euo pipefail

DEST_DIR="${HOME}/Applications"
DEST_APP="${DEST_DIR}/Ramener Toolbar.app"

# Prefer an existing CLI, otherwise fall back to the bundled app path.
if command -v ramener >/dev/null 2>&1; then
    RUNNER_CMD="ramener"
elif [ -x "/Applications/Ramener.app/Contents/MacOS/ramener" ]; then
    RUNNER_CMD="/Applications/Ramener.app/Contents/MacOS/ramener"
else
    echo "⚠️  未找到已安装的 ramener CLI，也没有检测到 /Applications/Ramener.app。脚本仍会创建工具栏应用，但点击时需要先安装 CLI 或复制 Ramener.app 到 /Applications。" >&2
    RUNNER_CMD="ramener"
fi

echo "➡️  Creating Finder toolbar helper at ${DEST_APP}" >&2
mkdir -p "${DEST_DIR}"

tmp_dir=$(mktemp -d)
trap 'rm -rf "${tmp_dir}"' EXIT

applescript_path="${tmp_dir}/ramener_toolbar.applescript"
cat >"${applescript_path}" <<APPLESCRIPT
on run {input, parameters}
    tell application "Finder"
        set selectedItems to selection
        if selectedItems is {} then
            display alert "Ramener" message "请在 Finder 中选中要重命名的 PDF，再点击工具栏按钮。"
            return
        end if
    end tell

    set renamedItems to {}
    repeat with anItem in selectedItems
        set itemAlias to anItem as alias
        set posixPath to POSIX path of itemAlias

        set runCommand to "${RUNNER_CMD} --log-file \"$HOME/Library/Logs/Ramener/ramener.log\" " & quoted form of posixPath
        set shellCommand to "/usr/bin/env zsh -lc " & quoted form of runCommand

        try
            set newPath to do shell script shellCommand
            if newPath is not "" then copy newPath to end of renamedItems
        on error errMsg number errNo
            display alert "Ramener" message ("处理失败：" & errMsg)
            return
        end try
    end repeat

    if (count of renamedItems) > 0 then
        set lastItem to last item of renamedItems
        do shell script "/usr/bin/open -R " & quoted form of lastItem
    end if
end run
APPLESCRIPT

if ! command -v osacompile >/dev/null 2>&1; then
    echo "❌  未找到 osacompile，请在安装 Xcode Command Line Tools 后重试 (xcode-select --install)。" >&2
    exit 1
fi

osacompile -o "${DEST_APP}" "${applescript_path}"

chmod +x "${DEST_APP}/Contents/MacOS/applet"

osascript <<'APPLESCRIPT' "${DEST_APP}"
on run argv
    set destPath to item 1 of argv
    set destAlias to POSIX file destPath
    tell application "Finder"
        activate
        open (path to applications folder from user domain)
        reveal destAlias
        display dialog "已创建 \"Ramener Toolbar.app\"。点击 Finder 菜单栏的“显示 → 自定工具栏…”，然后把这个应用拖到工具栏即可。" buttons {"好的"} default button 1
    end tell
end run
APPLESCRIPT

echo "✅  Finder 工具栏助手已创建。按照弹框提示，将它拖到 Finder 工具栏即可。" >&2
