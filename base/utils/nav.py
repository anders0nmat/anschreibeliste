
from dataclasses import dataclass, field
from collections.abc import Iterable
from django.http import HttpRequest

@dataclass
class RequestedNavItem:
    title: str
    path: str
    active: bool

class NavItem:
    title: str
    main_path: str
    paths: set[str]
    path_prefixes: set[str]
    
    permissions: set[str]

    def __init__(self, title: str, paths: str | Iterable[str] = [], path_prefixes: str | Iterable[str] = [], permissions: Iterable[str] = []) -> None:
        self.title = title

        if isinstance(paths, str):
            paths = [paths]
        if isinstance(path_prefixes, str):
            path_prefixes = [path_prefixes]
        if isinstance(permissions, str):
            permissions = [permissions]

        if not paths:
            raise ValueError("No path defined but required for default target")
        self.main_path = paths[0]

        self.paths = set(paths)
        self.path_prefixes = set(path_prefixes)

        self.permissions = set(permissions)

    def for_request(self, request: HttpRequest) -> RequestedNavItem | None:
        if not request.user.has_perms(self.permissions):
            return None
        
        view_name = request.resolver_match.view_name
        is_active = \
            view_name in self.paths or\
            any(view_name.startswith(prefix) for prefix in self.path_prefixes)        

        return RequestedNavItem(
            title=self.title,
            path=self.main_path,
            active=is_active
        )


