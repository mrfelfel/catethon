"""Tests for catethon.cat.server -- connecting to a Cat Messenger server.

No network: the point is that the shipped key and defaults are right and that a
prepared client is aimed at the right place, not that production is up. The key
straight-diff vs the live server was checked by hand (see UPSTREAM_SYNC.md).
"""

import base64
import hashlib

import pytest

from catethon.cat import server
from catethon.crypto import rsa
from catethon.network import ConnectionHttp, ConnectionTcpFull
from catethon.sessions import MemorySession


def test_packaged_key_matches_recorded_fingerprint():
    assert hashlib.sha256(server.public_key_der()).hexdigest() == server.KEY_SHA256


def test_packaged_key_is_the_thecat_production_key():
    # Modulus prefix from the server's Android brief; a rotation changes this
    # and KEY_SHA256 together, and the live-server check in UPSTREAM_SYNC.md.
    body = ''.join(
        line for line in server.KEY_FILE.read_text().splitlines()
        if not line.startswith('-----'))
    import rsa as rsa_lib
    key = rsa_lib.PublicKey.load_pkcs1_openssl_der(base64.b64decode(body))
    assert key.n.to_bytes((key.n.bit_length() + 7) // 8, 'big').hex() \
        .upper().startswith('D8B9CE68')
    assert key.e == 65537
    assert key.n.bit_length() == 2048


def test_register_server_key_enters_the_registry():
    key = server.register_server_key()
    # Encrypting under the announced fingerprint is what the server's key
    # exchange does; if the key were not registered this returns None.
    assert rsa.encrypt(rsa._compute_fingerprint(key), b'probe') is not None


def test_defaults_point_at_the_cat_server():
    assert server.DEFAULT_HOST == '62.220.127.238'
    assert server.DEFAULT_PORT == 30001
    assert server.DEFAULT_DC_ID == 2


def test_prepare_aims_memory_session_at_the_server():
    prepared = server.prepare(MemorySession())
    assert prepared.session.server_address == server.DEFAULT_HOST
    assert prepared.session.port == server.DEFAULT_PORT
    assert prepared.session.dc_id == server.DEFAULT_DC_ID
    assert prepared.connection is ConnectionTcpFull


def test_default_session_is_a_file():
    # A memory session would lose the login on restart; the default must persist.
    assert server.prepare().session == server.DEFAULT_SESSION_FILE


def test_prepare_accepts_http_transport():
    assert server.prepare(MemorySession(), transport='http').connection \
        is ConnectionHttp


def test_prepare_rejects_unknown_transport():
    with pytest.raises(ValueError):
        server.prepare(MemorySession(), transport='websocket')


def test_prepare_honours_overrides():
    prepared = server.prepare(MemorySession(), host='10.0.0.5', port=30098, dc_id=1)
    assert prepared.session.server_address == '10.0.0.5'
    assert prepared.session.port == 30098
    assert prepared.session.dc_id == 1


def test_prepared_make_client_sets_dc_on_a_filename_session(tmp_path):
    prepared = server.prepare(str(tmp_path / 'login.session'))
    client = prepared.make_client(17349, 'x' * 32)
    # The client constructor builds the SQLite session; the DC must be applied.
    assert client.session.server_address == server.DEFAULT_HOST
    assert client.session.port == server.DEFAULT_PORT
    assert client.session.dc_id == server.DEFAULT_DC_ID
    assert not client.is_connected()


def test_prepared_make_client_is_bound_and_unconnected():
    client = server.prepare(MemorySession()).make_client(17349, 'x' * 32)
    assert client.session.server_address == server.DEFAULT_HOST
    assert not client.is_connected()
