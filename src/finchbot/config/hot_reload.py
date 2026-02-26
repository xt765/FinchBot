import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from loguru import logger
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


class ConfigHotReloader:
    """
    Hot reload configuration files.

    Features:
    - Watch configuration file changes
    - Automatic reload on modification
    - Callback support for custom handlers
    """

    def __init__(
        self,
        config_path: Path,
        on_reload: Callable[[dict[str, Any]], None] | None = None
    ):
        self.config_path = config_path
        self.on_reload = on_reload
        self._observer: Observer | None = None
        self._last_reload: float = 0
        self._debounce_seconds: float = 1.0
        self._running = False

    def start(self) -> None:
        """Start watching configuration file."""
        if self._running:
            return

        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}")
            return

        self._observer = Observer()
        handler = _ConfigEventHandler(self._on_file_change)

        self._observer.schedule(
            handler,
            str(self.config_path.parent),
            recursive=False
        )

        self._observer.start()
        self._running = True
        logger.info(f"Config hot reload started for {self.config_path}")

    def stop(self) -> None:
        """Stop watching configuration file."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None

        self._running = False
        logger.info("Config hot reload stopped")

    def _on_file_change(self, event: FileSystemEvent) -> None:
        """Handle file change event."""
        if not event.src_path.endswith(str(self.config_path)):
            return

        if event.event_type not in ('modified', 'created'):
            return

        now = time.time()
        if now - self._last_reload < self._debounce_seconds:
            return

        self._last_reload = now

        try:
            config = self._load_config()

            if config and self.on_reload:
                self.on_reload(config)
                logger.info("Configuration reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload config: {e}")

    def _load_config(self) -> dict[str, Any] | None:
        """Load configuration from file."""
        import yaml

        with open(self.config_path, encoding='utf-8') as f:
            return yaml.safe_load(f)


class _ConfigEventHandler(FileSystemEventHandler):
    """Event handler for configuration file changes."""

    def __init__(self, callback: Callable[[FileSystemEvent], None]):
        self.callback = callback

    def on_modified(self, event: FileSystemEvent) -> None:
        self.callback(event)

    def on_created(self, event: FileSystemEvent) -> None:
        self.callback(event)


class ConfigManager:
    """
    Configuration manager with hot reload support.

    Features:
    - Load configuration from file
    - Hot reload on file changes
    - Get/set configuration values
    - Environment variable overrides
    """

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._config: dict[str, Any] = {}
        self._reloader: ConfigHotReloader | None = None
        self._subscribers: list[Callable[[dict[str, Any]], None]] = []

    def load(self) -> dict[str, Any]:
        """Load configuration from file."""
        import yaml

        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}")
            return {}

        with open(self.config_path, encoding='utf-8') as f:
            self._config = yaml.safe_load(f) or {}

        self._apply_env_overrides()

        return self._config

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides."""
        import os

        env_mappings = {
            'FINCHBOT_DEFAULT_MODEL': 'default_model',
            'FINCHBOT_LOG_LEVEL': 'logging.level',
            'FINCHBOT_DEBUG': 'debug',
        }

        for env_key, config_path in env_mappings.items():
            value = os.environ.get(env_key)
            if value:
                self._set_nested(config_path, value)

    def _set_nested(self, path: str, value: Any) -> None:
        """Set a nested configuration value."""
        keys = path.split('.')
        current = self._config

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        keys = key.split('.')
        current = self._config

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default

        return current

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        self._set_nested(key, value)

    def subscribe(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Subscribe to configuration changes."""
        self._subscribers.append(callback)

    def _notify_subscribers(self) -> None:
        """Notify all subscribers of configuration changes."""
        for callback in self._subscribers:
            try:
                callback(self._config)
            except Exception as e:
                logger.error(f"Config subscriber error: {e}")

    def start_hot_reload(self) -> None:
        """Start hot reload."""
        def on_reload(config: dict[str, Any]) -> None:
            self._config = config
            self._apply_env_overrides()
            self._notify_subscribers()

        self._reloader = ConfigHotReloader(
            self.config_path,
            on_reload=on_reload
        )
        self._reloader.start()

    def stop_hot_reload(self) -> None:
        """Stop hot reload."""
        if self._reloader:
            self._reloader.stop()
            self._reloader = None

    @property
    def config(self) -> dict[str, Any]:
        """Get the current configuration."""
        return self._config
