"""Client settings sourced from the environment cat-server already uses.

The values and variable names here are not invented. Two Go programs in
cat-server are the contract:

- `cmd/giftfetch` reads ``SESSION`` and ``SOCKS5_PROXY`` and defaults to the
  published Telegram Desktop api_id/api_hash pair for a read-only fetcher.
- `cmd/bots/grammystore` reads ``TELEGRAM_PROXY_URL`` (socks5h:// preferred).

A Python tool that uses catethon should describe the *same* client as the Go
one, so this module reads those names first and only falls back to
``CATETHON_*`` overrides. It never hardcodes a bot token: user-session
credentials are api_id/api_hash, which are public application identifiers, not
account secrets.

The api_id/api_hash default is the published Telegram Desktop pair (17349 /
344583e45741c457fe1862106095a5eb), the same constants `cmd/giftfetch` and
`scripts/giftfetch_telethon.py` already ship. It identifies the application,
not a user; keep it in one place per client rather than inventing a new pair.
"""

import os
from dataclasses import dataclass
from typing import Optional

# Published Telegram Desktop application identifiers. Not a secret; see the
# module docstring for why this is not read from a cat-server secret.
DEFAULT_API_ID = 17349
DEFAULT_API_HASH = '344583e45741c457fe1862106095a5eb'

# Telethon's own defaults are generic; these make a catethon session
# distinguishable in the account's "Active sessions" list, which is how an
# operator tells the gift fetcher apart from a real phone.
DEFAULT_DEVICE_MODEL = 'catethon'
DEFAULT_SYSTEM_VERSION = '1.0'
DEFAULT_APP_VERSION = '1.0'

_PROXY_VARS = ('CATETHON_PROXY', 'SOCKS5_PROXY', 'TELEGRAM_PROXY_URL')


def _first(env, names, default=None):
    for name in names:
        value = (env.get(name) or '').strip()
        if value:
            return value
    return default


def _int_or_none(value):
    if value is None or value == '':
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError('api id %r is not an integer' % (value,))


@dataclass(frozen=True)
class CatClientSettings:
    """Everything TelegramClient needs, plus where it came from.

    `proxy` is a string, not a parsed object: converting it (socks5 vs MTProxy
    vs HTTP) is Telethon's job in `proxy=` handling, and duplicating that here
    would drift from upstream.
    """
    api_id: int
    api_hash: str
    proxy: Optional[str] = None
    device_model: str = DEFAULT_DEVICE_MODEL
    system_version: str = DEFAULT_SYSTEM_VERSION
    app_version: str = DEFAULT_APP_VERSION
    lang_code: str = 'en'
    system_lang_code: str = 'en'

    def client_kwargs(self):
        """Keyword arguments for `catethon.TelegramClient(...)`, proxy aside.

        Proxy is deliberately excluded: Telethon wants either a parsed proxy
        object or a connection factory, and passing the raw URL would break on
        a socks5h:// value. Use `.proxy_url` with `catethon.cat.proxy.connect`
        when a proxy is configured.
        """
        kwargs = dict(
            device_model=self.device_model,
            system_version=self.system_version,
            app_version=self.app_version,
            lang_code=self.lang_code,
            system_lang_code=self.system_lang_code,
        )
        return kwargs

    @property
    def proxy_url(self):
        return self.proxy


def from_env(environ=None):
    """Read CatClientSettings from the environment.

    Precedence for every value: a ``CATETHON_*``-specific variable, then the
    cat-server name the Go tools use, then the module default.
    """
    env = os.environ if environ is None else environ
    api_id = _int_or_none(_first(
        env, ('CATETHON_API_ID',), DEFAULT_API_ID))
    api_hash = _first(env, ('CATETHON_API_HASH',), DEFAULT_API_HASH)
    proxy = _first(env, _PROXY_VARS)
    return CatClientSettings(
        api_id=api_id,
        api_hash=api_hash,
        proxy=proxy,
        device_model=_first(env, ('CATETHON_DEVICE_MODEL',), DEFAULT_DEVICE_MODEL),
    )
