"""Diálogo que captura um atalho de teclado (modificadores + tecla)."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout


_QT_MOD_KEYS = {Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift, Qt.Key_Meta}


def _mods_from_event(ev: QKeyEvent) -> list[str]:
    m = ev.modifiers()
    mods = []
    if m & Qt.ControlModifier:
        mods.append("ctrl")
    if m & Qt.AltModifier:
        mods.append("alt")
    if m & Qt.ShiftModifier:
        mods.append("shift")
    if m & Qt.MetaModifier:
        mods.append("super")
    return mods


def format_hotkey(key: str, mods: list[str]) -> str:
    sym = {"ctrl": "⌃", "alt": "⌥", "shift": "⇧", "super": "⌘"}
    s = "".join(sym[m] for m in ("ctrl", "alt", "shift", "super") if m in mods)
    s += (key or "").upper()
    return s or "—"


class HotkeyCaptureDialog(QDialog):
    captured = Signal(str, list)  # (key, modifiers)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Atalho")
        self.setModal(True)
        self.setFixedSize(360, 180)
        self.setFocusPolicy(Qt.StrongFocus)

        v = QVBoxLayout(self)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(10)

        self.info = QLabel("Pressione o novo atalho…")
        self.info.setAlignment(Qt.AlignCenter)
        self.info.setStyleSheet("font-size: 14px;")
        v.addWidget(self.info)

        self.live = QLabel(" ")
        self.live.setAlignment(Qt.AlignCenter)
        self.live.setStyleSheet("font-size: 26px; color: #2e86de;")
        v.addWidget(self.live)

        hint = QLabel("Use Ctrl/Alt/Shift/Super + tecla. Esc cancela.")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: gray; font-size: 11px;")
        v.addWidget(hint)

    def keyPressEvent(self, ev: QKeyEvent):
        if ev.key() == Qt.Key_Escape:
            self.reject()
            return
        mods = _mods_from_event(ev)
        # Modificador puro: mostra ao vivo e espera a tecla
        if ev.key() in _QT_MOD_KEYS:
            self.live.setText(format_hotkey("", mods) or " ")
            return
        if not mods:
            # exige ao menos 1 modificador (evita atalhos triviais)
            return
        text = ev.text()
        if not text or not text.isprintable():
            return
        key = text.lower()
        self.live.setText(format_hotkey(key, mods))
        self.captured.emit(key, mods)
        self.accept()

    def keyReleaseEvent(self, ev: QKeyEvent):
        mods = _mods_from_event(ev)
        self.live.setText(format_hotkey("", mods) or " ")
