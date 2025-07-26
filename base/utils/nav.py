
from dataclasses import dataclass, field
from collections.abc import Iterable
from django.http import HttpRequest

@dataclass
class RequestedNavItem:
    title: str
    path: str
    active: bool

@dataclass
class NavItem:
    title: str
    paths: Iterable[str]
    
    permissions: Iterable[str] = field(default_factory=list)

    def for_request(self, request: HttpRequest) -> RequestedNavItem | None:
        if not request.user.has_perms(self.permissions):
            return None
        return RequestedNavItem(
            title=self.title,
            path=self.paths[0],
            active=request.resolver_match.view_name in self.paths
        )


