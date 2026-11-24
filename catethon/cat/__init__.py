"""Cat Messenger client helpers on top of upstream Telethon.

catethon is Telethon with the Cat Messenger server wired in. Use `server`
to talk to a Cat Messenger deployment, and `config`/`session`/`proxy` for the
settings that come from environment variables.

Nothing in this package is imported by the rest of catethon: the upstream tree
stays byte-identical apart from the mechanical `telethon` -> `catethon` rename,
so a rebase onto a new upstream release never merges this code.
"""

from .config import CatClientSettings, from_env
from .proxy import parse_proxy
from .server import (
    DEFAULT_DC_ID,
    DEFAULT_HOST,
    DEFAULT_PORT,
    PreparedConnection,
    prepare,
    register_server_key,
)
from .session import session_from_env, string_session_for

__all__ = [
    'CatClientSettings',
    'DEFAULT_DC_ID',
    'DEFAULT_HOST',
    'DEFAULT_PORT',
    'PreparedConnection',
    'from_env',
    'parse_proxy',
    'prepare',
    'register_server_key',
    'session_from_env',
    'string_session_for',
]
