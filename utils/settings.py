
from typing import Any, Iterable
from django.conf import settings
from django.core.signals import setting_changed
from django.utils.module_loading import import_string

from functools import cached_property

SettingsDict = dict[str, Any]

class AppSettings:
    """
    Easy settings for django apps.

    Example usage:
    ```py
    # myapp/conf.py

    from utils.settings import AppSettings

    HEADER_COLOR = 'red'
    PAGE_TIMEOUT = 500

    settings = AppSettings('MYAPP', globals())

    # myproject/settings.py

    MYAPP = {
        'PAGE_TIMEOUT': 120,
    }

    # myapp/views.py

    from .conf import settings

    def get_config():
        return settings.PAGE_TIMEOUT, settings.HEADER_COLOR
        # Would return (120, 'red')
        
    ```
    """

    namespace: str
    defaults: SettingsDict
    import_keys: set[str]

    def __init__(self, namespace: str, defaults: SettingsDict, import_keys: Iterable[str] = None, connect_signal=True) -> None:
        """
        Params:
        - `namespace` The name to search in django.conf.settings for app-specific settings
        - `defaults` List of valid settings and their default values. Only settings with UPPERCASE keys will be used
        - `import_keys` Setting names that are supposed to import something. Settings might be customized in the
          project/settings.py where no imports are allowed.
        - `connect_signal` Connect to the `setting_changed` signal and reload settings
        """
        self.defaults = {key: value for key, value in defaults.items() if key.isupper()}
        self.namespace = namespace
        self.import_keys = set(import_keys or [])

        if connect_signal:
            def signal_callback(*args, setting, **kwargs):
                if setting == self.namespace:
                    self.reload()
            setting_changed.connect(signal_callback)

    @cached_property
    def settings(self) -> SettingsDict:
        return getattr(settings, self.namespace, {})
    
    def _import_value(self, value, attr):
        try:
            return import_string(value)
        except ImportError as e:
            raise ImportError(f"Failed to import '{value}' for setting '{attr}'. {e}")

    def __getattr__(self, attr: str):
        if attr not in self.defaults:
            raise AttributeError(f"Invalid setting: '{attr}'")
        
        value = self.settings.get(attr, self.defaults[attr])

        if attr in self.import_keys:
            if isinstance(value, str):
                value = self._import_value(value)
            elif isinstance(value, (list, tuple)):
                value = [self._import_value(v) for v in value]
        
        return value
    
    def reload(self):
        del self.settings
