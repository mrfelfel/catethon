"""Tests for catethon.cat -- the fork's only original code.

These are kept apart from the upstream suites on purpose: a rebase replaces
tests/catethon/* wholesale, and this file must not be caught in that.
"""

import base64
import struct

import pytest

from catethon.cat import config, parse_proxy, session
from catethon.cat.session import (
    session_from_env,
    string_session_for,
    validate_string_session,
)
from catethon.sessions import StringSession


KEY = bytes(range(256))


def test_config_defaults_match_giftfetch():
    s = config.from_env({})
    # Same pair cmd/giftfetch and scripts/giftfetch_telethon.py ship.
    assert s.api_id == 17349
    assert s.api_hash == '344583e45741c457fe1862106095a5eb'
    assert s.proxy is None
    assert s.device_model == 'catethon'


def test_config_reads_go_side_variables():
    s = config.from_env({
        'SOCKS5_PROXY': 'socks5://127.0.0.1:1080',
        'CATETHON_DEVICE_MODEL': 'giftfetch-catethon',
    })
    assert s.proxy == 'socks5://127.0.0.1:1080'
    assert s.device_model == 'giftfetch-catethon'


def test_config_override_beats_go_variable():
    s = config.from_env({
        'CATETHON_PROXY': 'socks5h://10.0.0.1:1080',
        'SOCKS5_PROXY': 'socks5://127.0.0.1:1080',
    })
    assert s.proxy == 'socks5h://10.0.0.1:1080'


def test_config_rejects_non_integer_api_id():
    with pytest.raises(ValueError):
        config.from_env({'CATETHON_API_ID': 'not-a-number'})


def test_client_kwargs_has_no_proxy():
    # Proxy goes through connection_factory/parse_proxy, never as a URL kwarg.
    kwargs = config.from_env({'SOCKS5_PROXY': 'socks5://h:1'}).client_kwargs()
    assert 'proxy' not in kwargs
    assert kwargs['device_model'] == 'catethon'


@pytest.mark.parametrize('url,expected', [
    ('socks5://h:1080', ('socks5', 'h', 1080, None, None, False)),
    ('socks5h://u:p@h:1080', ('socks5', 'h', 1080, 'u', 'p', True)),
    ('socks4://h:1080', ('socks4', 'h', 1080, None, None, False)),
    ('http://h:8080', ('http', 'h', 8080, None, None, False)),
    ('', None),
    (None, None),
])
def test_parse_proxy_tuple_shape(url, expected):
    assert parse_proxy(url) == expected


@pytest.mark.parametrize('url', [
    'ftp://h:21', 'socks5://h', 'socks5://', 'socks5://:1080',
])
def test_parse_proxy_rejects(url):
    with pytest.raises(ValueError):
        parse_proxy(url)


def test_string_session_for_is_accepted_by_go_parser_shape():
    value = string_session_for(2, '149.154.167.51', 443, KEY)
    assert value[0] == '1'
    raw = base64.urlsafe_b64decode(value[1:])
    # td/session.TelethonSession unpacks >B{4}sH256s: 1+4+2+256 == 263 bytes.
    assert len(raw) == 263
    dc, ip, port, key = struct.unpack('>B4sH256s', raw)
    assert dc == 2
    assert tuple(ip) == (149, 154, 167, 51)
    assert port == 443
    assert key == KEY


def test_string_session_for_ipv6_is_275_bytes():
    value = string_session_for(2, '2001:db8::1', 443, KEY)
    assert len(base64.urlsafe_b64decode(value[1:])) == 275


def test_session_from_env_prefers_catethon_name():
    good = string_session_for(2, '149.154.167.51', 443, KEY)
    other = string_session_for(1, '1.2.3.4', 443, KEY)
    chosen = session_from_env({
        'CATETHON_SESSION': good,
        'TELETHON_SESSION': other,
    })
    assert chosen.dc_id == 2


def test_session_from_env_reads_legacy_name():
    good = string_session_for(4, '149.154.167.51', 443, KEY)
    assert session_from_env({'TELETHON_SESSION': good}).dc_id == 4


def test_session_from_env_empty_means_none():
    assert session_from_env({}) is None
    assert session_from_env({'CATETHON_SESSION': '  '}) is None


def test_validate_rejects_bad_version():
    with pytest.raises(ValueError):
        validate_string_session('2AAAA')


def test_validate_rejects_wrong_length():
    body = base64.urlsafe_b64encode(b'\x00' * 100).decode()
    with pytest.raises(ValueError):
        validate_string_session('1' + body)


def test_validate_roundtrips_a_real_session():
    value = StringSession()
    value.set_dc(2, '149.154.167.51', 443)
    from catethon.crypto import AuthKey
    value.auth_key = AuthKey(KEY)
    assert validate_string_session(value.save()) == value.save()
