"""Monitor do clipboard: salva novos conteúdos no SQLite com dedupe + prune."""
import time

from PySide6.QtCore import QObject, Signal, QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from . import db
from .constants import DEFAULT_MAX_HISTORY


class ClipboardMonitor(QObject):
    history_changed = Signal()

    def __init__(self, conn, settings):
        super().__init__()
        self.conn = conn
        self.settings = settings
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self._on_clipboard_change)
        self._ignore_until = 0.0
        self._insert_count = 0

    def ignore_for(self, seconds: float) -> None:
        """Suprime a próxima(s) detecção(ões) por N segundos.
        Útil ao colar do histórico para evitar reinserção.
        """
        self._ignore_until = time.time() + seconds

    def _on_clipboard_change(self) -> None:
        if time.time() < self._ignore_until:
            return
        md = self.clipboard.mimeData()
        if md is None:
            return
        # texto primeiro (mais barato e mais comum)
        if md.hasText():
            text = md.text()
            if text and text.strip():
                inserted = db.insert_or_update_text(self.conn, text)
                self._post_insert(inserted)
                return
        # imagem
        if self.settings.get_bool("copy_images_enabled", True) and md.hasImage():
            img = self.clipboard.image()
            if not img.isNull():
                ba = QByteArray()
                buf = QBuffer(ba)
                buf.open(QIODevice.WriteOnly)
                img.save(buf, "PNG")
                data = bytes(ba)
                if data:
                    inserted = db.insert_or_update_image(self.conn, data)
                    self._post_insert(inserted)

    def _post_insert(self, inserted: bool) -> None:
        if inserted:
            self._insert_count += 1
            if self._insert_count % 10 == 0:
                limit = self.settings.get_int("max_history_items", DEFAULT_MAX_HISTORY)
                db.prune_to_limit(self.conn, limit)
        self.history_changed.emit()
