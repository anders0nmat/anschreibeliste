
from typing import Any, Callable
from datetime import timedelta
from django.http import HttpRequest, HttpResponse
from django.utils.timezone import now

from .models import PrivilegedSession
from logging import getLogger

logger = getLogger('autologin')

class AutoLoginMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> Any:
        privileged_session = PrivilegedSession.objects.filter(session_key=request.session.session_key).first()
        if privileged_session:
            if now() - privileged_session.last_changed > timedelta(days=30):
                request.session.cycle_key()
                privileged_session.session_key = request.session.session_key
                privileged_session.save()
                logger.info(f'Recycled session key for privileged connection "{privileged_session.name}"')
            request.session.set_expiry(timedelta(days=90))

        response = self.get_response(request)

        return response
