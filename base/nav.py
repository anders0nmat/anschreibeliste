
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from typing import Iterable, Mapping
from .utils.nav import NavItem

from logging import getLogger

logger = getLogger('base.nav')

def get_nav_from_conf() -> Iterable[NavItem]:
    conf = settings.NAVBAR
    if not conf:
        logger.info('No NAVBAR entries specified in settings, using []')
        return []
    if not isinstance(conf, Iterable):
        logger.warn('settings.NAVBAR is not iterable, ignoring...')
        return []
    
    nav_list = []
    for idx, item in enumerate(conf):
        if not isinstance(item, Mapping):
            logger.warn(f'settings.NAVBAR[{idx}] is not a mapping')
            continue
        try:
            nav_list.append(NavItem(
                title=item['title'],
                paths=item['paths'],
                path_prefixes=item.get('path_prefixes', []),
                permissions=item.get('permissions', []),
            ))
        except KeyError as err:
            logger.warn(f'settings.NAVBAR[{idx}] is missing "{err.args[0]}" attribute')

    return nav_list

navbar = get_nav_from_conf()

