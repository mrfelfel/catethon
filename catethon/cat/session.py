"""Session strings that the Go side of cat-server can decode.

`td/session.TelethonSession` (in cat-server's td submodule) reads a Telethon
StringSession: a literal ``'1'`` version byte followed by URL-safe base64 of
``>B{4,16}sH256s`` -- dc_id, packed IP, port, 256-byte auth key. That format
is owned by upstream `catethon.sessions.string`, and this module does not
reimplement it. It only picks the right session source out of the environment
and refuses, up front, a string the Go parser would reject.

Why the check exists: a StringSession that Python accepts but Go rejects fails
at the *other* end of a pipeline, usually hours later, as a decrypt/garbage
error against a different service. Failing at construction is cheaper.
"""

import base64
import binascii
import os

from ..sessions import StringSession

SESSION_ENV = 'CATETHON_SESSION'
# Upstream script compatibility: scripts/giftfetch_telethon.py already reads
# TELETHON_SESSION. Reading it here means an operator's existing environment
# keeps working after the import rename.
LEGACY_SESSION_ENV = 'TELETHON_SESSION'

_VERSION = '1'
# 1 (version byte) + base64 of (1 + 4|16 + 2 + 256). See the struct format in
# catethon/sessions/string.py and td/session/telethon.go.
_MIN_LENGTH = 1 + 4 * ((1 + 4 + 2 + 256 + 2) // 3)


def validate_string_session(value):
    """Raise ValueError unless `value` is a StringSession the Go parser reads.

    Mirrors td/session/telethon.go: version byte exactly ``'1'``, URL-safe
    base64 body, and a decoded length of 263 (IPv4) or 275 (IPv6) bytes.
    """
    if not isinstance(value, str) or not value:
        raise ValueError('session string is empty')
    if value[0] != _VERSION:
        raise ValueError(
            'unsupported StringSession version %r; only %r is understood'
            % (value[0], _VERSION))
    body = value[1:]
    if len(body) < _MIN_LENGTH - 1:
        raise ValueError('session string is too short (%d chars)' % len(value))
    try:
        raw = base64.urlsafe_b64decode(body)
    except (binascii.Error, ValueError) as exc:
        raise ValueError('session body is not URL-safe base64: %s' % exc)
    if len(raw) not in (263, 275):
        raise ValueError(
            'decoded session is %d bytes, expected 263 (IPv4) or 275 (IPv6)'
            % len(raw))
    return value


def string_session_for(dc_id, server_address, port, auth_key):
    """Build a StringSession and validate it in one step.

    The caller owns where the auth key came from; this never reads a file.
    """
    session = StringSession()
    session.set_dc(dc_id, server_address, port)
    from ..crypto import AuthKey
    session.auth_key = AuthKey(bytes(auth_key))
    saved = session.save()
    return validate_string_session(saved)


def session_from_env(environ=None):
    """Return a validated StringSession from the environment, or None.

    CATETHON_SESSION wins; TELETHON_SESSION is the pre-rename name an existing
    deployment may still export. An empty value means "no string session", not
    an error -- the caller then falls back to a file session, exactly as the
    Go fetchers do when SESSION is unset.
    """
    env = os.environ if environ is None else environ
    for name in (SESSION_ENV, LEGACY_SESSION_ENV):
        value = (env.get(name) or '').strip()
        if value:
            return StringSession(validate_string_session(value))
    return None
