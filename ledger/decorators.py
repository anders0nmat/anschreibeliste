from functools import wraps
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from http import HTTPStatus
from django.core.cache import caches
from hashlib import blake2b
import json
from typing import Any, Callable, TypeVar, Optional
from dataclasses import dataclass
from django.core.exceptions import ImproperlyConfigured

class HttpResponseLocked(HttpResponse):
    status_code = HTTPStatus.LOCKED

def idempotent(function=None, header_name: str = "Idempotency-Key", required: bool = False, cache: str = 'default', timeout=600):
    def _idempotent(view_func):
        @wraps(view_func)
        def _check_idempotent(request: HttpRequest, *args, **kwargs):
            _cache = caches[cache]
            key = request.headers.get(header_name)
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
                return HttpResponseBadRequest()
            else:
                return view_func(request, *args, **kwargs)

        return _check_idempotent

    if function:
        return _idempotent(function)
    return _idempotent

@dataclass
class Pattern:
    name: str
    path: str
    validator: Callable[[Any], Any]
    
    def __init__(self, pattern: str | tuple[str] | tuple[str, str | Callable[[Any], Any]] | tuple[str, str, Callable[[Any], Any]]):
        self.validator = lambda x: x
        match pattern:
            case (a, b, c):
                self.path = a
                self.name = b
                self.validator = c
            case (a, b):
                if isinstance(b, str):
                    self.path = a
                    self.name = b
                else:
                    self.path = a
                    self.name = a
                    self.validator = b
            case (a,):
                self.path = a
                self.name = a
            case a if isinstance(a, str):
                self.path = a
                self.name = a
            case a if isinstance(a, Pattern):
                self = pattern
            case _:
                raise ImproperlyConfigured(f"Invalid pattern: {pattern}")
        self.name = self.name.replace('.', '_').replace('?', '')
    
    def split_path(self) -> list[tuple[str, bool]]:
        result = ((part, part[-1] == '?') for part in self.path.split('.'))
        return [(part[:-1] if optional else part, optional) for part, optional in result]
    
    def find_value(self, json_structure, default=None):
        current = json_structure
        path = []
        for step, optional in self.split_path():
            if not isinstance(current, (dict, list)):
                raise ValueError(f'Cannot walk path along object of type {current.__class__.__name__}. Expected dict or list')
            try:
                if isinstance(current, dict):
                    current = current[step]
                elif isinstance(current, list):
                    current = current[int(step)]
                path.append(step)
            except (KeyError, IndexError):
                if optional:
                    return default
                raise KeyError('.'.join(path))
        return current
    
    def get_value(self, structure) -> Optional[tuple[str, Any]]:
        sentinel = object()
        value = self.find_value(structure, default=sentinel)
        if value is not sentinel:
            try:
                value = self.validator(value)
            except ValueError:
                raise ValueError('.'.join(p for p, _ in self.split_path()))
            return self.name, value
        return None
        

    

def one_of(*values: Any) -> Callable[[Any], Any]:
    def _one_of(value):
        if value not in values:
            raise ValueError()
        return value
    return _one_of

T = TypeVar("T")
def satisfies(condition: Callable[[Any], bool]) -> Callable[[T], T]:
    def _satisfies(value):
        if not condition(value):
            raise ValueError()
        return value
    return _satisfies

def chain(*validators: Callable[[Any], Any]) -> Callable[[Any], Any]:
    def _chain(value):
        for validator in validators:
            value = validator(value)
        return value
    return _chain

def json_body(function=None, patterns: list[Pattern] = None):
    """
    Assert a request body of type json which is added to the request object under `request.json`.

    If parameter `patterns` is given, the json body is also evaluated and passed as parameter to the view function.
    A pattern is a tuple with the following entries:
    - a json path
    - a parameter name to populate (optional, inferred from the json path)
    - a validator/converter function (optional)
    if only a json path is given, the pattern may also be a string.
    If any component of the json path ends with a '?', the component may not exist.
    In this case, the argument is not bound, allowing for a default value to be specified.

    Example:
    ```python
    recipe_patterns = [
        "recipe.id",
        ("step_count", int),

        ("steps.-1", "last_step"),
        ("steps.-1.time", "last_step_time", datetime.time.fromisoformat)
    ]

    request.json = {
        "recipe": {"id": 51, "name": "Eggs & Bacon"},
        "step_count": 3,
        "steps": [
            {"type": "prepare", "time": "0:30"},
            {"type": "cook", "time": "6:00"},
            {"type": "garnish", "time": "15:00"}
        ]
    }

    @json_body(patterns=recipe_patterns)
    def view_func(request: HttpRequest, recipe_id: Any, step_count: int, last_step: Any, last_step_time: datetime.time):
        print(f"{recipe_id=} {step_count=} {last_step=} {last_step_time=}")
        # prints: recipe_id=51 step_count=3 last_step={"type": "garnish", "time": "15:00"} last_step_time=datetime.time(15, 0)
    ```
    """
    def _json_body(view_func):
        @wraps(view_func)
        def _convert_json_body(request: HttpRequest, *args, **kwargs):
            try:
                body_json = json.loads(request.body)

                if not hasattr(request, 'json'):
                    setattr(request, 'json', body_json)

                arguments = {}
                if patterns:
                    for field in patterns:
                        key_value = Pattern(field).get_value(body_json)
                        if key_value is not None:
                            arguments[key_value[0]] = key_value[1]
            except json.JSONDecodeError:
                return HttpResponseBadRequest("Expected JSON")
            except KeyError as e:
                return HttpResponseBadRequest(f"Missing Field '{e}'")
            except ValueError as e:
                return HttpResponseBadRequest(f"Invalid value at '{e}'")
            return view_func(request, *args, **arguments, **kwargs)
        return _convert_json_body
    
    if function:
        return _json_body(function)
    return _json_body



def require_POST_fields(fields: list[Pattern]):
    def _require_POST_fields(view_func):
        @wraps(view_func)
        def _read_POST_fields(request: HttpRequest, *args, **kwargs):
            arguments = {}
            try:
                for field in fields:
                    key_value = Pattern(field).get_value(request.POST)
                    if key_value is not None:
                        arguments[key_value[0]] = key_value[1]
            except KeyError:
                return HttpResponseBadRequest("Missing required POST parameter")
            except ValueError:
                return HttpResponseBadRequest("POST parameter has wrong type")
            return view_func(request, *args, **arguments, **kwargs)

        return _read_POST_fields
    
    return _require_POST_fields
    
