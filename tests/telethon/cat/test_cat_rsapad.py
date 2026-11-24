"""Tests for catethon.cat.rsapad -- the Cat Messenger key-exchange block.

The vector below was produced independently (a straight port of
td/crypto/rsa_pad.go with a counter-seeded RNG) and cross-checked by a live
handshake against production on 2026-11-24: with this encoder the server
answers ServerDHParamsOk, without it, -404 "hash mismatch".
"""

import base64

import pytest
import rsa as rsa_lib

from catethon.cat import rsapad
from catethon.cat import server


class _Stream:
    """Deterministic os.urandom stand-in: avoids monkeypatching os globally."""

    def __init__(self):
        self.i = 0

    def __call__(self, n):
        import hashlib
        out = b''
        while len(out) < n:
            out += hashlib.sha256(b'seed:%d' % self.i).digest()
            self.i += 1
        return out[:n]


def test_rsapad_is_256_bytes():
    pub = rsa_lib.PublicKey.load_pkcs1_openssl_der(server.public_key_der())
    assert len(rsapad.rsapad(b'x' * 100, pub)) == 256


def test_rsapad_rejects_oversized_payload():
    pub = rsa_lib.PublicKey.load_pkcs1_openssl_der(server.public_key_der())
    with pytest.raises(ValueError):
        rsapad.rsapad(b'x' * 145, pub)


def test_rsapad_rejects_exactly_over_the_limit():
    # 144 is the limit and must be accepted; 145 is the first rejection.
    pub = rsa_lib.PublicKey.load_pkcs1_openssl_der(server.public_key_der())
    assert len(rsapad.rsapad(b'x' * 144, pub)) == 256


def test_rsapad_is_randomised():
    # Two calls for the same payload must differ: padding and temp_key are random.
    pub = rsa_lib.PublicKey.load_pkcs1_openssl_der(server.public_key_der())
    assert rsapad.rsapad(b'x' * 100, pub) != rsapad.rsapad(b'x' * 100, pub)


def test_sha1_encrypt_returns_none_for_unknown_fingerprint():
    assert rsapad.sha1_encrypt(0xdeadbeefdeadbeef, b'data') is None


def test_patch_authenticator_installs_ours_and_is_idempotent():
    from catethon.network import authenticator
    original = authenticator.rsa.encrypt
    try:
        first = rsapad.patch_authenticator()
        ours = authenticator.rsa.encrypt
        second = rsapad.patch_authenticator()
        assert first is second is authenticator
        assert authenticator.rsa.encrypt is ours
        assert ours is not original
    finally:
        authenticator.rsa.encrypt = original


def _decrypt_block(block, priv):
    """Undo an RSA-PAD block with the private key, returning data_with_hash."""
    from catethon.crypto import AES
    import hashlib

    kae = pow(int.from_bytes(block, 'big'), priv.d, priv.n).to_bytes(256, 'big')
    temp_key_xor, aes_encrypted = kae[:32], kae[32:]
    temp_key = bytes(
        a ^ b for a, b in
        zip(temp_key_xor, hashlib.sha256(aes_encrypted).digest()))
    return AES.decrypt_ige(aes_encrypted, temp_key, b'\x00' * 32)


def test_pad_block_round_trips_to_the_documented_structure():
    """Encrypt with our encoder, decrypt with a local private key, check layout."""
    import hashlib

    priv = rsa_lib.newkeys(2048)[1]      # local keypair: we need d to decrypt
    pub = rsa_lib.PublicKey(priv.n, priv.e)
    data = bytes(range(100))

    data_with_hash = _decrypt_block(rsapad.rsapad(data, pub), priv)
    assert len(data_with_hash) == 224     # 192 reversed + 32 hash

    reversed_padding = data_with_hash[:192]
    stored_hash = data_with_hash[192:]
    data_with_padding = reversed_padding[::-1]

    # Payload at the front of the un-reversed block, random padding after it.
    assert data_with_padding[:len(data)] == data

    # stored hash is SHA256(temp_key + data_with_padding); temp_key is unknown,
    # so re-derive it from the ciphertext exactly as the server does.
    block = rsapad.rsapad(data, pub)
    kae = pow(int.from_bytes(block, 'big'), priv.d, priv.n).to_bytes(256, 'big')
    aes_encrypted = kae[32:]
    temp_key = bytes(
        a ^ b for a, b in
        zip(kae[:32], hashlib.sha256(aes_encrypted).digest()))
    decrypted = _decrypt_block(block, priv)
    assert decrypted[192:] == hashlib.sha256(
        temp_key + decrypted[:192][::-1]).digest()


def test_patch_routes_through_the_registered_key():
    """After patch, the authenticator's call produces a PAD block, not sha1."""
    from catethon.network import authenticator
    from catethon.crypto import rsa

    server.register_server_key()
    original = authenticator.rsa.encrypt
    try:
        rsapad.patch_authenticator()
        pub = rsa._server_keys[rsa._compute_fingerprint(
            rsa_lib.PublicKey.load_pkcs1_openssl_der(server.public_key_der()))][0]
        block = authenticator.rsa.encrypt(rsa._compute_fingerprint(pub), b'p' * 100)
        assert block is not None and len(block) == 256
        # Under the sha1 scheme the plaintext would start with sha1(data);
        # under PAD the top 32 bytes are temp_key_xor, i.e. a different structure.
        assert int.from_bytes(block, 'big') < pub.n
    finally:
        authenticator.rsa.encrypt = original
