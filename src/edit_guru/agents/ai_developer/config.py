import os
import subprocess


class ConfigManager:
    _instance = None

    def __init__(self):
        self.use_cwd = False
        self.base_path = None
        self.initialized = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ConfigManager()
        return cls._instance

    def initialize(self, use_cwd: bool = False):
        self.use_cwd = use_cwd
        self.base_path = self._resolve_base_path()
        self.initialized = True

    def _resolve_base_path(self):
        if self.use_cwd:
            return os.getcwd()
        return subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip()
