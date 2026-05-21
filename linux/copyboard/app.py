"""Entry point do CopyBoard (Linux)."""
import sys
import os

from pathlib import Path

from PySide6.QtCore import QTimer, QByteArray
from PySide6.QtGui import QIcon, QImage
from PySide6.QtWidgets import QApplication, QMessageBox

ICON_PATH = Path(__file__).resolve().parent.parent / "resources" / "icon.png"

from . import db
from .constants import DEFAULT_HOTKEY_KEY, DEFAULT_HOTKEY_MODIFIERS
from .hotkey import HotkeyManager
from .hotkey_capture import HotkeyCaptureDialog
from .history_window import HistoryWindow
from .monitor import ClipboardMonitor
from .settings import Settings
from .settings_window import SettingsWindow
from .tray import TrayIcon

try:
    from pynput.keyboard import Controller, Key
    _PYNPUT_OK = True
except Exception:
    _PYNPUT_OK = False


class CopyBoardApp:
    def __init__(self, argv):
        self.qapp = QApplication(argv)
        self.qapp.setQuitOnLastWindowClosed(False)
        self.qapp.setApplicationName("CopyBoard")
        self.qapp.setOrganizationName("CopyBoard")
        if ICON_PATH.exists():
            self.qapp.setWindowIcon(QIcon(str(ICON_PATH)))

        self.conn = db.init_db()
        self.settings = Settings()

        self.monitor = ClipboardMonitor(self.conn, self.settings)

        self.hotkey = HotkeyManager()
        self.hotkey.activated.connect(self._on_hotkey)
        self._register_hotkey()

        self.kbd = Controller() if _PYNPUT_OK else None
        self.history: HistoryWindow | None = None
        self.settings_win: SettingsWindow | None = None

        self.exec_cmd = self._build_exec_cmd()
        self.tray = TrayIcon(
            on_hotkey_config=self._open_hotkey_config,
            on_settings=self._open_settings,
            on_open_history=self._open_history,
            on_quit=self._quit,
        )

    def _build_exec_cmd(self) -> str:
        return f"{sys.executable} -m copyboard.app"

    def _register_hotkey(self):
        key = self.settings.get_str("hotkey_key", DEFAULT_HOTKEY_KEY)
        mods = self.settings.get_list("hotkey_modifiers", DEFAULT_HOTKEY_MODIFIERS)
        if not key:
            key = DEFAULT_HOTKEY_KEY
        if not mods:
            mods = DEFAULT_HOTKEY_MODIFIERS
        self.hotkey.register(key, mods)

    def _on_hotkey(self):
        self._open_history()

    def _open_history(self):
        if self.history is not None and self.history.isVisible():
            self.history.raise_()
            self.history.activateWindow()
            return
        self.history = HistoryWindow(self.conn, monitor=self.monitor)
        self.history.item_picked.connect(self._paste_item)
        # atualiza ao chegar item novo
        self.monitor.history_changed.connect(self._refresh_history_if_open)
        self.history.destroyed.connect(self._on_history_destroyed)
        self.history.show()
        self.history.activateWindow()

    def _on_history_destroyed(self, *_):
        self.history = None

    def _refresh_history_if_open(self):
        if self.history is not None and self.history.isVisible():
            try:
                self.history._do_fetch()
            except Exception:
                pass

    def _paste_item(self, item_id: int):
        row = db.get_item(self.conn, item_id)
        if not row:
            return
        content, image_data, has_image = row
        self.monitor.ignore_for(2.0)
        cb = self.qapp.clipboard()
        if has_image and image_data:
            img = QImage.fromData(QByteArray(image_data))
            if not img.isNull():
                cb.setImage(img)
            elif content:
                cb.setText(content)
        elif content:
            cb.setText(content)
        # pequena pausa para a janela popup fechar e o foco voltar ao app de destino
        QTimer.singleShot(120, self._send_paste)

    def _send_paste(self):
        if not self.kbd:
            return
        try:
            self.kbd.press(Key.ctrl)
            self.kbd.press('v')
            self.kbd.release('v')
            self.kbd.release(Key.ctrl)
        except Exception as e:
            print(f"[paste] erro ao simular Ctrl+V: {e}")

    def _open_hotkey_config(self):
        d = HotkeyCaptureDialog()
        d.captured.connect(self._on_hotkey_captured)
        d.exec()

    def _on_hotkey_captured(self, key: str, mods: list):
        self.settings.set("hotkey_key", key)
        self.settings.set("hotkey_modifiers", ",".join(mods))
        combo = self.hotkey.register(key, mods)
        if combo is None:
            QMessageBox.warning(
                None,
                "Atalho",
                "Não foi possível registrar o atalho global.\n"
                "Em Wayland esse recurso normalmente não funciona — "
                "use uma sessão X11.",
            )

    def _open_settings(self):
        if self.settings_win is not None and self.settings_win.isVisible():
            self.settings_win.raise_()
            self.settings_win.activateWindow()
            return
        self.settings_win = SettingsWindow(
            self.conn, self.settings, self.hotkey, self.exec_cmd
        )
        self.settings_win.open_history_requested.connect(self._open_history)
        self.settings_win.finished.connect(lambda _: setattr(self, "settings_win", None))
        self.settings_win.show()

    def _quit(self):
        try:
            self.hotkey.unregister()
        except Exception:
            pass
        self.qapp.quit()

    def run(self) -> int:
        return self.qapp.exec()


def main():
    app = CopyBoardApp(sys.argv)
    sys.exit(app.run())


if __name__ == "__main__":
    main()
