
from typing import Any, Callable
from django.http import HttpRequest, HttpResponse
from django.contrib.auth import login

from django.conf import settings

from .models import AutoLogin
from logging import getLogger

logger = getLogger('autologin')

class AutoLoginMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> Any:
        if not request.user.is_authenticated:
            self.auto_login(request)

        response = self.get_response(request)

        return response
    
    def auto_login(self, request: HttpRequest): 
        try:
            session_key = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
            login_rule = AutoLogin.objects.get(session_key=session_key)
            login(request, login_rule.user)
            login_rule.session_key = request.session.session_key
            login_rule.history.create(
                new_session_id=request.session.session_key,
                ip_address=request.META['REMOTE_ADDR'],
                user_agent=request.META['HTTP_USER_AGENT']
            )
            login_rule.save()
            logger.info(f'Renewed session for {request.META['REMOTE_ADDR']} according to login rule "{login_rule.name}"')
        except (AutoLogin.DoesNotExist, AutoLogin.MultipleObjectsReturned):
            pass
