"""Hotkey global multiplataforma via pynput (X11). Em Wayland tem limitações."""
from PySide6.QtCore import QObject, Signal

try:
    from pynput import keyboard
    _PYNPUT_OK = True
except Exception:  # pragma: no cover
    _PYNPUT_OK = False


# Modificadores aceitos: ctrl, alt, shift, super
_MOD_TO_PYNPUT = {
    "ctrl": "<ctrl>",
    "alt": "<alt>",
    "shift": "<shift>",
    "super": "<cmd>",  # cmd = tecla super/meta no pynput
}


def build_combo(key: str, modifiers: list[str]) -> str:
    parts = [_MOD_TO_PYNPUT[m] for m in modifiers if m in _MOD_TO_PYNPUT]
    parts.append((key or "").lower())
    return "+".join(parts)


class HotkeyManager(QObject):
    activated = Signal()

    def __init__(self):
        super().__init__()
        self._listener = None
        self._current_combo: str | None = None

    def register(self, key: str, modifiers: list[str]) -> str | None:
        """(Re)registra o hotkey global. Retorna o combo string ou None se falhar."""
        self.unregister()
        if not _PYNPUT_OK:
            print("[hotkey] pynput indisponível — atalho global desabilitado.")
            return None
        combo = build_combo(key, modifiers)
        try:
            self._listener = keyboard.GlobalHotKeys({combo: self._on_hotkey})
            self._listener.daemon = True
            self._listener.start()
            self._current_combo = combo
            return combo
        except Exception as e:
            print(f"[hotkey] erro ao registrar {combo!r}: {e}")
            self._listener = None
            return None

    def unregister(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
            self._current_combo = None

    def _on_hotkey(self):
        # roda em thread do pynput; Signal Qt enfileira pra main thread
        self.activated.emit()
