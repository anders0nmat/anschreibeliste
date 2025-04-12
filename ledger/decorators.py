from functools import wraps
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from http import HTTPStatus
from django.core.cache import caches
from hashlib import blake2b

class HttpResponseLocked(HttpResponse):
    status_code = HTTPStatus.LOCKED

def idempotent(function=None, header_name: str = "Idempotency-Key", required: bool = True, post_field=None, cache: str = 'default', timeout=600):
    """
    Ensure idempotency on this view. Responses will be buffered for subsequent requests with the same key.
    
    This ensures that views where calling them multiple times has a different effect than calling them once (non-idempotent)
    will only execute once, but will behave to the client as if every request was processed (just with the identical response).

    Can be used on POST-requests where it is important that the exact same request will not trigger an action multiple times.
    E.g. processing a transaction request.
    
    Will look for the value of header `header_name` (default 'Idempotency-Key'),
    if not present, assume the body is a POST body and look for the `post_field`.
    This allows for plain HTML-forms to still use this decorator by including an `<input type="hidden">` with name `post_field` and an server-provided value/key.
    
    Responses are cached in `cache` for `timeout` milliseconds. During that time, a request from the same session with the same key
    will instead receive the cached response _without_ calling the view. The request is not checked for equality, only the idempotency-key.
    
    if `required` is false, requests without the `header_name`-header or `post_field` in the body will be passed without modification
    to the view function, behaving as if the modifier is not present.
    Requests with one of the key fields will still get idempotent behavior.
    """
    def _idempotent(view_func):
        @wraps(view_func)
        def _check_idempotent(request: HttpRequest, *args, **kwargs):
            _cache = caches[cache]
            key = request.headers.get(header_name) or (post_field and request.POST.get(post_field))
            if key:				
                cache_key = blake2b(f"{request.session.session_key}-{key}".encode()).hexdigest()
                obtained_key = _cache.add(cache_key, HttpResponseLocked(), timeout=timeout)
                
                if not obtained_key:
                    return _cache.get(cache_key)

                if not hasattr(request, 'idempotency_key'):
                    setattr(request, 'idempotency_key', key)

                response = view_func(request, *args, **kwargs)
                _cache.set(cache_key, response, timeout=timeout)

                return response
            elif required:
                return HttpResponseBadRequest('Missing required idempotency key')
            else:
                return view_func(request, *args, **kwargs)

        return _check_idempotent

    if function:
        return _idempotent(function)
    return _idempotent

