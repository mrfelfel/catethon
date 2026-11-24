"""Turn the project's proxy URL strings into what TelegramClient accepts.

cat-server already speaks one proxy dialect on the Go side: `cmd/giftfetch`
parses ``SOCKS5_PROXY`` and `cmd/bots/grammystore` documents
``socks5h://`` (remote DNS). Telethon's `proxy=` takes a tuple or dict, not a
URL, and the shape depends on the scheme. This module translates once so each
Python tool does not grow its own subtly different parser.

It returns the *tuple form* Telethon documents
``(proxy_type, addr, port, username, password, rdns)``
(`catethon/network/connection/connection.py`, `_parse_proxy`), so Telethon
still owns how the socket is opened. Only the schemes the project uses are
accepted; an unknown scheme raises instead of being guessed into an HTTP
proxy, because a silently wrong proxy is a hung or leaking connection.
"""

from urllib.parse import urlsplit


def parse_proxy(url):
    """Parse a proxy URL into Telethon's proxy tuple, or None for no proxy.

    ``socks5h://`` is ``socks5://`` with remote DNS: same tuple, rdns True.
    A missing port is an error -- defaulting it would hide a typo.
    """
    if not url:
        return None
    parts = urlsplit(url.strip())
    scheme = (parts.scheme or '').lower()
    if scheme in ('socks5', 'socks5h'):
        proxy_type = 'socks5'
    elif scheme == 'socks4':
        proxy_type = 'socks4'
    elif scheme == 'http':
        proxy_type = 'http'
    else:
        raise ValueError(
            'unsupported proxy scheme %r (use socks5://, socks5h://, '
            'socks4:// or http://)' % scheme)
    if not parts.hostname:
        raise ValueError('proxy URL %r has no host' % url)
    if parts.port is None:
        raise ValueError('proxy URL %r has no port' % url)
    return (
        proxy_type,
        parts.hostname,
        parts.port,
        parts.username,
        parts.password,
        scheme == 'socks5h',
    )
