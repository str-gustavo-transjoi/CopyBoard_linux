"""Wrapper simples sobre QSettings para preferências do usuário."""
from PySide6.QtCore import QSettings

from .constants import APP_ORG, APP_NAME


class Settings:
    def __init__(self):
        self.q = QSettings(APP_ORG, APP_NAME)

    def get(self, key, default=None):
        v = self.q.value(key)
        return default if v is None else v

    def get_bool(self, key, default=False):
        v = self.q.value(key)
        if v is None:
            return default
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return bool(v)

    def get_int(self, key, default=0):
        v = self.q.value(key)
        if v is None:
            return default
        try:
            return int(v)
        except (TypeError, ValueError):
            return default

    def get_str(self, key, default=""):
        v = self.q.value(key)
        return default if v is None else str(v)

    def get_list(self, key, default=None):
        v = self.q.value(key)
        if v is None:
            return list(default or [])
        if isinstance(v, list):
            return [str(x) for x in v if x]
        if isinstance(v, str):
            return [x for x in v.split(",") if x]
        return list(default or [])

    def set(self, key, value):
        self.q.setValue(key, value)
        self.q.sync()
