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

        if not use_cwd and not self._is_git_repo():
            raise RuntimeError(
                "Not inside a git repository. "
                "Please run the script from within a git repository or use the --use-cwd option."
            )

        self.base_path = self._resolve_base_path()
        self.initialized = True

    def _resolve_base_path(self):
        if self.use_cwd:
            return os.getcwd()
        return subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip()

    def _is_git_repo(self) -> bool:
        try:
            subprocess.check_output(["git", "rev-parse", "--is-inside-work-tree"], stderr=subprocess.STDOUT)
            return True
        except subprocess.CalledProcessError:
            return False
