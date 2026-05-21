"""Ícone na bandeja do sistema."""
from pathlib import Path

from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu

ICON_PATH = Path(__file__).resolve().parent.parent / "resources" / "icon.png"


def _load_icon() -> QIcon:
    if ICON_PATH.exists():
        return QIcon(str(ICON_PATH))
    # fallback: ícone do tema do sistema
    icon = QIcon.fromTheme("edit-paste")
    if icon.isNull():
        icon = QIcon.fromTheme("accessories-text-editor")
    return icon


class TrayIcon(QSystemTrayIcon):
    def __init__(self, on_hotkey_config, on_settings, on_open_history, on_quit, parent=None):
        super().__init__(_load_icon(), parent)
        self.setToolTip("CopyBoard")

        menu = QMenu()
        a_open = QAction("Abrir Histórico", menu)
        a_open.triggered.connect(on_open_history)
        menu.addAction(a_open)

        menu.addSeparator()

        a_hot = QAction("Alterar Atalho", menu)
        a_hot.triggered.connect(on_hotkey_config)
        menu.addAction(a_hot)

        a_set = QAction("Configurações", menu)
        a_set.triggered.connect(on_settings)
        menu.addAction(a_set)

        menu.addSeparator()

        a_quit = QAction("Sair", menu)
        a_quit.triggered.connect(on_quit)
        menu.addAction(a_quit)

        self.setContextMenu(menu)
        self.activated.connect(lambda reason: on_open_history()
                               if reason == QSystemTrayIcon.Trigger else None)
        self.show()
