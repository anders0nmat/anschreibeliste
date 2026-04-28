
try:
    from .local_settings import *
except ImportError:
    from .settings_base import *
