"""Janela de configurações."""
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from . import db
from .constants import DEFAULT_HOTKEY_KEY, DEFAULT_HOTKEY_MODIFIERS
from .hotkey_capture import HotkeyCaptureDialog, format_hotkey

AUTOSTART_DIR = Path.home() / ".config" / "autostart"
AUTOSTART_FILE = AUTOSTART_DIR / "copyboard.desktop"


def is_autostart_enabled() -> bool:
    return AUTOSTART_FILE.exists()


def set_autostart_enabled(enabled: bool, exec_cmd: str) -> None:
    if enabled:
        AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
        AUTOSTART_FILE.write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=CopyBoard\n"
            f"Exec={exec_cmd}\n"
            "X-GNOME-Autostart-enabled=true\n"
            "NoDisplay=false\n"
            "Terminal=false\n"
        )
    else:
        if AUTOSTART_FILE.exists():
            AUTOSTART_FILE.unlink()


def _fmt_bytes(n: int) -> str:
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    if n < 1024 * 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    return f"{n / (1024 * 1024 * 1024):.2f} GB"


class SettingsWindow(QDialog):
    open_history_requested = Signal()

    def __init__(self, conn, settings, hotkey_manager, exec_cmd: str, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.settings = settings
        self.hotkey_manager = hotkey_manager
        self.exec_cmd = exec_cmd

        self.setWindowTitle("Configurações")
        self.setMinimumSize(440, 560)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(14)

        # Aparência
        v.addWidget(self._title("Aparência"))
        self.theme_box = QComboBox()
        self.theme_box.addItem("Sistema", "system")
        self.theme_box.addItem("Claro", "light")
        self.theme_box.addItem("Escuro", "dark")
        current = self.settings.get_str("appearance_mode", "system")
        idx = self.theme_box.findData(current)
        if idx >= 0:
            self.theme_box.setCurrentIndex(idx)
        self.theme_box.currentIndexChanged.connect(
            lambda _: self.settings.set("appearance_mode", self.theme_box.currentData())
        )
        v.addWidget(self.theme_box)
        v.addWidget(self._divider())

        # Atalho
        v.addWidget(self._title("Atalho global"))
        h = QHBoxLayout()
        self.hotkey_label = QLabel(self._current_hotkey_text())
        self.hotkey_label.setStyleSheet("font-size: 16px; padding: 4px;")
        h.addWidget(self.hotkey_label, 1)
        change_btn = QPushButton("Alterar Atalho")
        change_btn.clicked.connect(self._change_hotkey)
        h.addWidget(change_btn)
        v.addLayout(h)
        v.addWidget(self._divider())

        # Histórico
        v.addWidget(self._title("Histórico"))
        open_btn = QPushButton("Abrir Histórico")
        open_btn.clicked.connect(self._open_history)
        v.addWidget(open_btn)

        v.addWidget(QLabel("Limpar histórico"))
        self.cleanup_mode = QComboBox()
        self.cleanup_mode.addItem("Apagar últimos X dias", "deleteRecent")
        self.cleanup_mode.addItem("Manter apenas últimos X dias", "keepRecent")
        cur_mode = self.settings.get_str("cleanup_mode", "deleteRecent")
        ix = self.cleanup_mode.findData(cur_mode)
        if ix >= 0:
            self.cleanup_mode.setCurrentIndex(ix)
        v.addWidget(self.cleanup_mode)

        h2 = QHBoxLayout()
        h2.addWidget(QLabel("Dias:"))
        self.days_spin = QSpinBox()
        self.days_spin.setRange(1, 3650)
        self.days_spin.setValue(self.settings.get_int("cleanup_days", 30))
        h2.addWidget(self.days_spin)
        h2.addStretch(1)
        v.addLayout(h2)

        cleanup_btn = QPushButton("Apagar")
        cleanup_btn.setStyleSheet(
            "color: white; background-color: #c0392b; padding: 8px; border-radius: 4px;"
        )
        cleanup_btn.clicked.connect(self._do_cleanup)
        v.addWidget(cleanup_btn)
        self.cleanup_msg = QLabel("")
        self.cleanup_msg.setStyleSheet("color: gray; font-size: 11px;")
        v.addWidget(self.cleanup_msg)
        v.addWidget(self._divider())

        # Imagens
        v.addWidget(self._title("Imagens"))
        self.images_check = QCheckBox("Salvar imagens copiadas no histórico")
        self.images_check.setChecked(self.settings.get_bool("copy_images_enabled", True))
        self.images_check.stateChanged.connect(
            lambda s: self.settings.set("copy_images_enabled", bool(s))
        )
        v.addWidget(self.images_check)
        v.addWidget(self._divider())

        # Autostart
        v.addWidget(self._title("Inicialização"))
        self.autostart_check = QCheckBox("Abrir o CopyBoard ao iniciar o sistema")
        self.autostart_check.setChecked(is_autostart_enabled())
        self.autostart_check.stateChanged.connect(self._on_autostart)
        v.addWidget(self.autostart_check)
        v.addWidget(self._divider())

        # Storage
        v.addWidget(self._title("Uso de armazenamento"))
        total = db.total_storage_size(self.conn)
        self.storage_label = QLabel("Total armazenado: " + _fmt_bytes(total))
        v.addWidget(self.storage_label)

        v.addStretch(1)
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ----- helpers
    def _title(self, t: str) -> QLabel:
        l = QLabel(t)
        l.setStyleSheet("font-weight: bold; font-size: 13px;")
        return l

    def _divider(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.HLine)
        f.setFrameShadow(QFrame.Sunken)
        return f

    def _current_hotkey_text(self) -> str:
        key = self.settings.get_str("hotkey_key", DEFAULT_HOTKEY_KEY)
        mods = self.settings.get_list("hotkey_modifiers", DEFAULT_HOTKEY_MODIFIERS)
        return format_hotkey(key, mods)

    # ----- ações
    def _change_hotkey(self):
        d = HotkeyCaptureDialog(self)
        d.captured.connect(self._on_hotkey_captured)
        d.exec()

    def _on_hotkey_captured(self, key: str, mods: list):
        self.settings.set("hotkey_key", key)
        self.settings.set("hotkey_modifiers", ",".join(mods))
        combo = self.hotkey_manager.register(key, mods)
        self.hotkey_label.setText(format_hotkey(key, mods))
        if combo is None:
            QMessageBox.warning(
                self,
                "Atalho",
                "Não foi possível registrar o atalho global. "
                "Em Wayland, atalhos globais geralmente não funcionam — "
                "tente uma sessão X11.",
            )

    def _open_history(self):
        self.open_history_requested.emit()
        self.close()

    def _do_cleanup(self):
        mode = self.cleanup_mode.currentData()
        days = self.days_spin.value()
        msg = (
            f"Apagar todos os itens dos últimos {days} dia(s)?"
            if mode == "deleteRecent"
            else f"Manter apenas os itens dos últimos {days} dia(s)?\n"
                 "Todos os demais serão removidos."
        )
        r = QMessageBox.question(
            self, "Confirmar limpeza", msg,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if r != QMessageBox.Yes:
            return
        self.settings.set("cleanup_mode", mode)
        self.settings.set("cleanup_days", days)
        n = db.cleanup_by_days(self.conn, mode, days)
        self.cleanup_msg.setText(f"{n} item(ns) removido(s).")
        total = db.total_storage_size(self.conn)
        self.storage_label.setText("Total armazenado: " + _fmt_bytes(total))
        # invalida cache de thumbs
        try:
            from .history_window import THUMB_CACHE
            THUMB_CACHE.clear()
        except Exception:
            pass

    def _on_autostart(self, state):
        try:
            set_autostart_enabled(bool(state), self.exec_cmd)
        except Exception as e:
            QMessageBox.warning(self, "Inicialização automática", f"Falha: {e}")
