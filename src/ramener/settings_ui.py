from __future__ import annotations

import sys
from pathlib import Path

try:
    from Cocoa import (
        NSAlert,
        NSApplication,
        NSApplicationActivationPolicyRegular,
        NSBackingStoreBuffered,
        NSButton,
        NSMakeRect,
        NSObject,
        NSSecureTextField,
        NSTextField,
        NSView,
        NSWindow,
        NSWindowStyleMaskClosable,
        NSWindowStyleMaskMiniaturizable,
        NSWindowStyleMaskTitled,
    )
    from AppKit import NSBezelStyleRounded
    import objc
except ImportError:  # pragma: no cover - handled at runtime
    NSApplication = None  # type: ignore

from .config import DEFAULT_BASE_URL, DEFAULT_MODEL
from .settings import SETTINGS_FILE, load_user_settings, save_user_settings


def _normalize(value: str) -> str | None:
    stripped = value.strip()
    return stripped or None


class SettingsController(NSObject):
    def init(self):
        self = objc.super(SettingsController, self).init()
        if self is None:
            return None
        self.window = None
        self._service_field = None
        self._api_key_field = None
        self._model_field = None
        self._base_url_field = None
        return self

    def applicationDidFinishLaunching_(self, notification):  # pragma: no cover - UI hook
        settings = load_user_settings()
        self._build_window(settings)

    def windowWillClose_(self, notification):  # pragma: no cover - UI hook
        NSApplication.sharedApplication().terminate_(self)

    def saveClicked_(self, sender):  # pragma: no cover - UI hook
        current = load_user_settings()
        current.service_name = _normalize(self._service_field.stringValue())
        current.api_key = _normalize(self._api_key_field.stringValue())
        current.model = _normalize(self._model_field.stringValue()) or DEFAULT_MODEL
        current.base_url = _normalize(self._base_url_field.stringValue()) or DEFAULT_BASE_URL
        save_user_settings(current)

        alert = NSAlert.alloc().init()
        alert.setMessageText_("设置已保存")
        alert.setInformativeText_(f"配置已写入\n{Path(SETTINGS_FILE).expanduser()}")
        alert.addButtonWithTitle_("好的")
        alert.runModal()
        NSApplication.sharedApplication().terminate_(self)

    def cancelClicked_(self, sender):  # pragma: no cover - UI hook
        NSApplication.sharedApplication().terminate_(self)

    def _build_window(self, settings):
        width, height = 520, 260
        style = (
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskMiniaturizable
        )
        window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0.0, 0.0, width, height),
            style,
            NSBackingStoreBuffered,
            False,
        )
        window.setTitle_("Ramener 设置")
        window.center()
        window.setDelegate_(self)

        content_view = window.contentView()  # type: ignore[assignment]
        if content_view is None:
            content_view = NSView.alloc().initWithFrame_(NSMakeRect(0.0, 0.0, width, height))
            window.setContentView_(content_view)

        labels = ["服务名称", "API Key", "模型名称", "服务 URL"]
        defaults = [
            settings.service_name or "",
            settings.api_key or "",
            settings.model or DEFAULT_MODEL,
            settings.base_url or DEFAULT_BASE_URL,
        ]

        fields = []
        x_label = 32
        x_field = 140
        y_start = height - 70
        row_gap = 48
        field_width = 320
        field_height = 26

        for index, (label, default) in enumerate(zip(labels, defaults)):
            y = y_start - index * row_gap

            label_field = NSTextField.alloc().initWithFrame_(
                NSMakeRect(x_label, y, 100, field_height)
            )
            label_field.setStringValue_(label)
            label_field.setEditable_(False)
            label_field.setBordered_(False)
            label_field.setBezeled_(False)
            label_field.setDrawsBackground_(False)
            label_field.setSelectable_(False)
            content_view.addSubview_(label_field)

            if label == "API Key":
                value_field = NSSecureTextField.alloc().initWithFrame_(
                    NSMakeRect(x_field, y, field_width, field_height)
                )
            else:
                value_field = NSTextField.alloc().initWithFrame_(
                    NSMakeRect(x_field, y, field_width, field_height)
                )
            value_field.setStringValue_(default)
            content_view.addSubview_(value_field)
            fields.append(value_field)

        self._service_field, self._api_key_field, self._model_field, self._base_url_field = fields

        button_y = 36
        cancel_button = NSButton.alloc().initWithFrame_(NSMakeRect(width - 220, button_y, 80, 32))
        cancel_button.setTitle_("取消")
        cancel_button.setBezelStyle_(NSBezelStyleRounded)
        cancel_button.setTarget_(self)
        cancel_button.setAction_("cancelClicked:")
        content_view.addSubview_(cancel_button)

        save_button = NSButton.alloc().initWithFrame_(NSMakeRect(width - 120, button_y, 80, 32))
        save_button.setTitle_("保存")
        save_button.setBezelStyle_(NSBezelStyleRounded)
        save_button.setTarget_(self)
        save_button.setAction_("saveClicked:")
        content_view.addSubview_(save_button)

        window.makeKeyAndOrderFront_(None)
        self.window = window


def main() -> int:
    if sys.platform != "darwin":
        print("ramener-settings 仅支持在 macOS 上运行", file=sys.stderr)
        return 1

    if NSApplication is None:
        print(
            "未找到 Cocoa 框架，请安装 pyobjc-framework-Cocoa (pip install pyobjc-framework-Cocoa)",
            file=sys.stderr,
        )
        return 1

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)

    controller = SettingsController.alloc().init()
    app.setDelegate_(controller)
    app.activateIgnoringOtherApps_(True)
    app.run()
    return 0


if __name__ == "__main__":  # pragma: no cover - manual invocation
    raise SystemExit(main())
