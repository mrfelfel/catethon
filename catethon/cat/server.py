"""Connect to a Cat Messenger ("The Cat") server, not to Telegram.

catethon speaks the same MTProto dialect as every other Telegram client; what
makes it a *Cat Messenger* client is three connection-time values that differ
from Telegram's own cloud:

- the server address and port (The Cat runs its own MTProto edge),
- the DC id the server advertises (2), and
- the server's RSA public key, which replaces Telegram's published keys for the
  key exchange.

All three are set here so a user never has to assemble them by hand. The
public key ships as a file beside this module
(`keys/thecat-prod-rsa.pub`), not as a string in source: a rotated key is then
a one-file change, and it can be checked against a published fingerprint.

Nothing here dials the network. `prepare()` wires a client that is *ready* to
connect; running it (`await client.connect()`) stays the caller's decision, the
same way every other Telethon entry point works.
"""

import pathlib

from ..crypto import rsa
from ..network import ConnectionHttp, ConnectionTcpFull

# The Cat production MTProto edge. Keep these in one place: a client that ships
# with these values is the difference between "works on install" and "user has
# to read a runbook".
DEFAULT_HOST = '62.220.127.238'
DEFAULT_PORT = 30001
DEFAULT_DC_ID = 2

# SHA-256 of the DER of keys/thecat-prod-rsa.pub. Printed by the server's own
# Android brief as well; recorded here so a wrong or corrupted key fails loudly
# at import-rest of the helper rather than as a handshake timeout.
KEY_FILE = pathlib.Path(__file__).with_name('keys') / 'thecat-prod-rsa.pub'
KEY_SHA256 = '7514f405f0c0969b5cc0301c6cfff9ad3d507bdb4471db5397f3e7447da60395'

# Both transports the server serves on the same port; TCP is the default a
# desktop/CLI client should use (the WebSocket path is for the browser client).
TRANSPORTS = {'tcp': ConnectionTcpFull, 'http': ConnectionHttp}

# Default login storage. A file session survives restarts; MemorySession does
# not, and a client that silently forgets the login is a worse default than one
# that leaves a file the first run created.
DEFAULT_SESSION_FILE = 'cat-messenger.session'


def public_key_der():
    """Return the packaged server key's DER bytes, checking its fingerprint."""
    import base64
    import hashlib

    text = KEY_FILE.read_text(encoding='utf-8')
    body = ''.join(
        line for line in text.splitlines() if not line.startswith('-----'))
    der = base64.b64decode(body)
    digest = hashlib.sha256(der).hexdigest()
    if digest != KEY_SHA256:
        raise RuntimeError(
            'Cat Messenger server key fingerprint changed: expected %s, got %s'
            % (KEY_SHA256, digest))
    return der


def _pkcs1_pem(pub):
    """Return `pub` as a PKCS#1 PEM ("BEGIN RSA PUBLIC KEY").

    Telethon's `rsa.add_key` calls `rsa.PublicKey.load_pkcs1`, which only
    accepts the PKCS#1 marker. The `rsa` package's own `save_pkcs1('PEM')` emits
    SubjectPublicKeyInfo in current versions, so the DER is rebuilt here from
    n/e directly. No extra dependency, and no hand-typed base64 to drift.
    """
    import base64
    import rsa as rsa_lib

    def der_len(n):
        if n < 0x80:
            return bytes([n])
        raw = n.to_bytes((n.bit_length() + 7) // 8, 'big')
        return bytes([0x80 | len(raw)]) + raw

    def der_int(value):
        raw = value.to_bytes((value.bit_length() + 7) // 8, 'big')
        if raw[0] & 0x80:
            raw = b'\x00' + raw
        return b'\x02' + der_len(len(raw)) + raw

    def der_seq(inner):
        return b'\x30' + der_len(len(inner)) + inner

    body = der_seq(der_int(pub.n) + der_int(pub.e))
    b64 = base64.b64encode(body).decode('ascii')
    lines = '\n'.join(b64[i:i + 64] for i in range(0, len(b64), 64))
    return ('-----BEGIN RSA PUBLIC KEY-----\n%s\n'
            '-----END RSA PUBLIC KEY-----\n' % lines)


def register_server_key():
    """Load the Cat Messenger key into Telethon's RSA registry.

    Telethon finds a server's key by the fingerprint the server announces during
    the key exchange; `rsa.add_key` is how a non-Telegram key joins that table.
    Idempotent: adding the same key twice just overwrites its entry.
    """
    import rsa as rsa_lib

    pub = rsa_lib.PublicKey.load_pkcs1_openssl_der(public_key_der())
    # add_key -> load_pkcs1 needs the PEM *with* its marker lines.
    rsa.add_key(_pkcs1_pem(pub), old=False)
    return pub


def prepare(session=None, *, host=DEFAULT_HOST, port=DEFAULT_PORT,
            dc_id=DEFAULT_DC_ID, transport='tcp', **client_kwargs):
    """Build a client aimed at a Cat Messenger server.

    `session` is anything TelegramClient accepts: a filename (the default — a
    login that survives restarts), a Session instance, or a session string.
    The DC is set on whatever session results, so the defaults cannot be
    forgotten.

    Returns a `PreparedConnection`; call `.make_client(api_id, api_hash)` for
    the actual TelegramClient. That client is not connected yet.
    """
    register_server_key()
    # Cat Messenger's server only accepts the newer RSA-PAD handshake block;
    # upstream Telethon sends the older sha1 form. Install ours before any
    # connect() can happen (see catethon/cat/rsapad.py).
    from .rsapad import patch_authenticator
    patch_authenticator()

    if session is None:
        session = DEFAULT_SESSION_FILE

    try:
        connection = TRANSPORTS[transport]
    except KeyError:
        raise ValueError(
            'transport must be one of %s' % sorted(TRANSPORTS))

    # Aim a live Session now, so `prepared.session` is inspectable; a filename
    # has no Session until the client is built, and make_client sets it then.
    if not isinstance(session, (str, pathlib.Path)):
        session.set_dc(dc_id, host, port)

    kwargs = dict(
        device_model='Cat Messenger',
        app_version='1.0',
        system_version='1.0',
        lang_code='en',
        system_lang_code='en',
        connection=connection,
    )
    kwargs.update(client_kwargs)
    return PreparedConnection(session=session, dc_id=dc_id, host=host,
                              port=port, connection=connection, kwargs=kwargs)


class PreparedConnection:
    """What `prepare` returns: the pieces of a ready-to-dial client."""

    def __init__(self, *, session, dc_id, host, port, connection, kwargs):
        self.session = session
        self.dc_id = dc_id
        self.host = host
        self.port = port
        self.connection = connection
        self.kwargs = kwargs

    def make_client(self, api_id, api_hash, **extra):
        """Return `catethon.TelegramClient` bound to this server, unconnected.

        A filename session has no DC until the client exists, so the client
        constructor creates it; the DC is applied immediately afterwards, before
        any connection is attempted.
        """
        from ..client.telegramclient import TelegramClient

        kwargs = dict(self.kwargs)
        kwargs.update(extra)
        client = TelegramClient(self.session, api_id, api_hash, **kwargs)
        client.session.set_dc(self.dc_id, self.host, self.port)
        return client
