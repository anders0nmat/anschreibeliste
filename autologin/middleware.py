
from typing import Any, Callable
from django.http import HttpRequest, HttpResponse
from django.contrib.auth import login

from .models import AutoLogin
from .conf import settings
from logging import getLogger

logger = getLogger('autologin')

class AutoLoginMiddleware:
    COOKIE_KEY = settings.COOKIE_KEY
    COOKIE_MAX_AGE = settings.COOKIE_MAX_AGE

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> Any:
        if not request.user.is_authenticated:
            self.auto_login(request)

        response = self.get_response(request)

        if not self.set_cookie(request, response):
            self.delete_cookie(request, response)

        return response
    
    def auto_login(self, request: HttpRequest):        
        device = request.META.get('REMOTE_ADDR')
        cookie_user = request.COOKIES.get(self.COOKIE_KEY)
        if not device or not cookie_user:
            return
        
        try:
            rule = AutoLogin.objects.get(user=cookie_user, device=device)
            login(request, rule.user)
            logger.info(f'Successful auto-login user={rule.user} for {device=}')
        except AutoLogin.DoesNotExist:
            return

    def set_cookie(self, request: HttpRequest, response: HttpResponse) -> bool:
        if not request.user.is_authenticated:
            return False
        device = request.META.get('REMOTE_ADDR')
        if not device:
            return False
        
        try:
            rule = AutoLogin.objects.get(user=request.user, device=device)
            response.set_cookie(
                key=self.COOKIE_KEY,
                value=rule.user.pk,
                max_age=self.COOKIE_MAX_AGE
            )
            return True
        except AutoLogin.DoesNotExist:
            return False
    
    def delete_cookie(self, request: HttpRequest, response: HttpResponse):
        if self.COOKIE_KEY in request.COOKIES:
            response.delete_cookie(self.COOKIE_KEY)

