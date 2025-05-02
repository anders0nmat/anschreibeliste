from typing import Optional
from django.utils.translation import override as override_language
from django.conf import settings

class server_language(override_language):
    """
    A context manager setting the currently active language to the server default.
    
    Usage:
    ```py
    with server_language():
        reason_message = _('User confirmed')
    ```
    """
    def __init__(self, deactivate: bool = False) -> None:
        super().__init__(settings.LANGUAGE_CODE, deactivate)

