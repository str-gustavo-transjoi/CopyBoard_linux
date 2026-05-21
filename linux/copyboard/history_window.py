"""Janela do histórico do clipboard (popup principal)."""
import time

from PySide6.QtCore import Qt, Signal, QTimer, QByteArray
from PySide6.QtGui import QImage, QPixmap, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import db
from .constants import DEBOUNCE_MS, PAGE_SIZE


class ThumbnailCache:
    def __init__(self, max_items: int = 200):
        self._cache: dict[str, QPixmap] = {}
        self._max = max_items

    def get(self, key: str):
        return self._cache.get(key)

    def put(self, key: str, pm: QPixmap):
        if len(self._cache) >= self._max:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = pm

    def clear(self):
        self._cache.clear()


THUMB_CACHE = ThumbnailCache()


class ItemRow(QFrame):
    select_toggled = Signal(int)
    picked = Signal(int)

    def __init__(self, item_id, timestamp, content, image_hash, has_image,
                 selection_mode: bool, is_selected: bool, conn, parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self.has_image = bool(has_image)
        self.image_hash = image_hash or ""
        self.selection_mode = selection_mode
        self.is_selected = is_selected
        self.expanded = False
        self._conn = conn

        self.setFrameShape(QFrame.NoFrame)
        self._apply_bg()
        self.setCursor(Qt.PointingHandCursor)

        v = QVBoxLayout(self)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(2)

        row = QHBoxLayout()
        row.setSpacing(8)

        self.toggle_btn = QPushButton("▼")
        self.toggle_btn.setFlat(True)
        self.toggle_btn.setFixedSize(22, 22)
        self.toggle_btn.clicked.connect(self._toggle_expand)
        row.addWidget(self.toggle_btn, 0, Qt.AlignTop)

        if selection_mode:
            self.check_btn = QPushButton("☑" if is_selected else "☐")
            self.check_btn.setFlat(True)
            self.check_btn.setFixedSize(24, 24)
            self.check_btn.clicked.connect(lambda: self.select_toggled.emit(self.item_id))
            row.addWidget(self.check_btn, 0, Qt.AlignTop)

        content_w = QWidget()
        cw = QVBoxLayout(content_w)
        cw.setContentsMargins(0, 0, 0, 0)
        cw.setSpacing(4)

        if self.has_image:
            self.img_label = QLabel()
            self.img_label.setMinimumSize(140, 90)
            self.img_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            self._load_thumb(expanded=False)
            cw.addWidget(self.img_label)
        else:
            self.text_label = QLabel(content or "")
            self.text_label.setWordWrap(True)
            self.text_label.setMaximumHeight(42)
            self.text_label.setTextInteractionFlags(Qt.NoTextInteraction)
            cw.addWidget(self.text_label)

        ts = QLabel(time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(timestamp)))
        ts.setStyleSheet("color: gray; font-size: 10px;")
        cw.addWidget(ts)

        row.addWidget(content_w, 1)
        v.addLayout(row)

    def _apply_bg(self):
        if self.is_selected:
            self.setStyleSheet("ItemRow { background-color: rgba(46,134,222,40); }")
        else:
            self.setStyleSheet("ItemRow { background-color: transparent; }")

    def _toggle_expand(self):
        self.expanded = not self.expanded
        if self.has_image:
            self._load_thumb(expanded=self.expanded)
        else:
            self.text_label.setMaximumHeight(16777215 if self.expanded else 42)
        self.toggle_btn.setText("▲" if self.expanded else "▼")

    def _load_thumb(self, expanded: bool):
        key = self.image_hash or f"id-{self.item_id}"
        pm = THUMB_CACHE.get(key)
        if pm is None:
            data = db.get_image_data(self._conn, self.item_id)
            if data:
                img = QImage.fromData(QByteArray(data))
                pm = QPixmap.fromImage(img)
                THUMB_CACHE.put(key, pm)
        if pm and not pm.isNull():
            max_w = 320 if expanded else 140
            max_h = 220 if expanded else 90
            self.img_label.setPixmap(
                pm.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            if self.selection_mode:
                self.select_toggled.emit(self.item_id)
            else:
                self.picked.emit(self.item_id)
        super().mousePressEvent(ev)


class HistoryWindow(QDialog):
    item_picked = Signal(int)

    def __init__(self, conn, monitor=None, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.monitor = monitor
        self.setWindowTitle("Histórico do Clipboard")
        self.setMinimumSize(580, 400)
        self.resize(620, 520)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self.selection_mode = False
        self.selected_ids: set[int] = set()
        self.page = 0
        self.search_text = ""
        self.items: list[tuple] = []
        self.has_more = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Toolbar
        tb = QHBoxLayout()
        tb.setContentsMargins(8, 8, 8, 4)
        self.select_all_btn = QPushButton("Selecionar tudo")
        self.select_all_btn.clicked.connect(self._select_all_toggle)
        self.select_all_btn.setVisible(False)
        tb.addWidget(self.select_all_btn)
        tb.addStretch(1)
        self.copy_btn = QPushButton()
        self.copy_btn.clicked.connect(self._copy_selected)
        self.copy_btn.setVisible(False)
        tb.addWidget(self.copy_btn)
        self.delete_btn = QPushButton()
        self.delete_btn.setStyleSheet("color: #c0392b;")
        self.delete_btn.clicked.connect(self._delete_selected)
        self.delete_btn.setVisible(False)
        tb.addWidget(self.delete_btn)
        self.select_btn = QPushButton("Selecionar")
        self.select_btn.clicked.connect(self._toggle_selection_mode)
        tb.addWidget(self.select_btn)
        outer.addLayout(tb)

        # Search
        sb = QHBoxLayout()
        sb.setContentsMargins(8, 4, 8, 4)
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Pesquisar… (use *image para filtrar imagens)")
        self.search_field.textChanged.connect(self._on_search_changed)
        sb.addWidget(self.search_field)
        clr = QPushButton("✕")
        clr.setFlat(True)
        clr.setFixedWidth(28)
        clr.clicked.connect(lambda: self.search_field.setText(""))
        sb.addWidget(clr)
        outer.addLayout(sb)

        # Lista
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(0)
        self.list_layout.addStretch(1)
        self.scroll.setWidget(self.list_container)
        outer.addWidget(self.scroll, 1)

        # Footer
        self.footer = QLabel("")
        self.footer.setStyleSheet("color: gray; font-size: 11px; padding: 6px 12px; "
                                  "background-color: rgba(127,127,127,18);")
        outer.addWidget(self.footer)

        # Debounce + atalhos
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(DEBOUNCE_MS)
        self.debounce.timeout.connect(self._do_fetch)
        QShortcut(QKeySequence("Esc"), self, activated=self.close)

        self.search_field.setFocus()
        self._do_fetch()

    # ----- Fetch / Render
    def _on_search_changed(self, txt: str):
        self.search_text = txt
        self.page = 0
        self.debounce.start()

    def _do_fetch(self):
        limit = PAGE_SIZE * (self.page + 1)
        rows = db.fetch_items(self.conn, self.search_text.strip(), limit=limit + 1, offset=0)
        if len(rows) > limit:
            self.items = rows[:limit]
            self.has_more = True
        else:
            self.items = rows
            self.has_more = False
        # remove ids selecionados que não estão mais visíveis (após delete)
        visible = {r[0] for r in self.items}
        self.selected_ids &= visible
        self._render()

    def _render(self):
        # remove tudo exceto o stretch final
        while self.list_layout.count() > 1:
            it = self.list_layout.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()

        for row in self.items:
            item_id, ts, content, ihash, has_img = row
            r = ItemRow(
                item_id, ts, content, ihash, has_img,
                self.selection_mode, item_id in self.selected_ids, self.conn,
            )
            r.select_toggled.connect(self._toggle_select_id)
            r.picked.connect(self._on_picked)
            self.list_layout.insertWidget(self.list_layout.count() - 1, r)
            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setStyleSheet("color: rgba(127,127,127,60);")
            self.list_layout.insertWidget(self.list_layout.count() - 1, sep)

        if self.has_more:
            more = QPushButton("Carregar mais")
            more.clicked.connect(self._load_more)
            self.list_layout.insertWidget(self.list_layout.count() - 1, more)

        if not self.items:
            empty = QLabel(
                "Nada encontrado" if self.search_text.strip() else "Nenhum item no histórico"
            )
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: gray; padding: 40px;")
            self.list_layout.insertWidget(self.list_layout.count() - 1, empty)

        n = len(self.selected_ids)
        self.copy_btn.setText(f"📋 Copiar ({n})")
        self.delete_btn.setText(f"🗑 Excluir ({n})")
        self.copy_btn.setVisible(self.selection_mode and n > 0)
        self.delete_btn.setVisible(self.selection_mode and n > 0)
        self.select_all_btn.setVisible(self.selection_mode)
        self.select_btn.setText("Cancelar seleção" if self.selection_mode else "Selecionar")
        suffix = "  •  mostrando os mais recentes" if self.has_more else ""
        self.footer.setText(f"{len(self.items)} item(ns){suffix}")

    def _load_more(self):
        self.page += 1
        self._do_fetch()

    # ----- Seleção
    def _toggle_selection_mode(self):
        self.selection_mode = not self.selection_mode
        if not self.selection_mode:
            self.selected_ids.clear()
        self._render()

    def _toggle_select_id(self, item_id: int):
        if item_id in self.selected_ids:
            self.selected_ids.remove(item_id)
        else:
            self.selected_ids.add(item_id)
        self._render()

    def _select_all_toggle(self):
        all_ids = {r[0] for r in self.items}
        if self.selected_ids >= all_ids and all_ids:
            self.selected_ids -= all_ids
        else:
            self.selected_ids |= all_ids
        self._render()

    # ----- Ações
    def _copy_selected(self):
        if self.monitor:
            self.monitor.ignore_for(1.5)
        texts = [r[2] for r in self.items if r[0] in self.selected_ids and r[2]]
        if texts:
            QApplication.clipboard().setText("\n".join(texts))
        self.selection_mode = False
        self.selected_ids.clear()
        self._render()

    def _delete_selected(self):
        ids = list(self.selected_ids)
        db.delete_items(self.conn, ids)
        self.selected_ids.clear()
        self._do_fetch()

    def _on_picked(self, item_id: int):
        self.item_picked.emit(item_id)
        self.close()
