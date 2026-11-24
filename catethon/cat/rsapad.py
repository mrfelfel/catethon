"""The RSA-PAD key-exchange block that Cat Messenger's server expects.

Upstream Telethon encrypts `p_q_inner_data` with the *original* MTProto scheme:
``sha1(data) + data + random``, RSA-encrypted. Cat Messenger's server is built
on the newer scheme from Telegram's auth_key spec ("Presenting Proof of Work,
Server Authentication"), the one `td/crypto/rsa_pad.go` calls `RSAPad`:

  data_with_padding := data + random, 192 bytes total, data <= 144
  data_pad_reversed := BYTE_REVERSE(data_with_padding)
  data_with_hash    := data_pad_reversed + SHA256(temp_key + data_with_padding)
  aes_encrypted     := AES256_IGE(data_with_hash, temp_key, 0)
  temp_key_xor      := temp_key XOR SHA256(aes_encrypted)
  key_aes_encrypted := temp_key_xor + aes_encrypted            (256 bytes)
  encrypted_data    := RSA(key_aes_encrypted, server_pubkey)

Sending the sha1 form gets ``-404 "hash mismatch"`` from the server -- it
decrypts, reads a hash it cannot match, and rejects the handshake. This module
produces the newer block so the handshake completes.

It is ours (``catethon.cat``), not upstream, because upstream's
`network/authenticator.py` hardcodes the sha1 call and changing it would put a
diff in a file every rebase touches. `patch_authenticator()` installs this
encoder *only* by assignment, so a rebase replaces upstream files cleanly and
this module keeps working as long as the call signature it hooks is unchanged.
"""

import hashlib
import os

from ..crypto import AES

DATA_LIMIT = 144
DATA_WITH_PADDING = 192
TEMP_KEY_SIZE = 32


def _ige_encrypt(key, data, iv=b'\x00' * 32):
    return AES.encrypt_ige(data, key, iv)


def rsapad(data, public_key):
    """Return the 256-byte RSA-PAD block for `data` under `public_key`.

    `public_key` is an `rsa.PublicKey` (the `rsa` dependency Telethon already
    has). Raises ValueError if `data` is too long for the 144-byte limit -- the
    answer is a different constructor, never silent truncation.
    """
    if len(data) > DATA_LIMIT:
        raise ValueError(
            'RSA-PAD payload is %d bytes; the format allows at most %d'
            % (len(data), DATA_LIMIT))

    data_with_padding = bytearray(DATA_WITH_PADDING)
    data_with_padding[:len(data)] = data
    data_with_padding[len(data):] = os.urandom(DATA_WITH_PADDING - len(data))
    data_pad_reversed = bytes(data_with_padding)[::-1]

    while True:
        temp_key = os.urandom(TEMP_KEY_SIZE)
        digest = hashlib.sha256(temp_key + bytes(data_with_padding)).digest()
        data_with_hash = data_pad_reversed + digest
        aes_encrypted = _ige_encrypt(temp_key, data_with_hash)
        temp_key_xor = bytes(
            a ^ b for a, b in
            zip(temp_key, hashlib.sha256(aes_encrypted).digest()))
        key_aes_encrypted = temp_key_xor + aes_encrypted

        if int.from_bytes(key_aes_encrypted, 'big') >= public_key.n:
            # RSA cannot carry a value >= the modulus; retry with a new key.
            continue

        encrypted = pow(int.from_bytes(key_aes_encrypted, 'big'),
                        public_key.e, public_key.n)
        return encrypted.to_bytes(256, 'big')


def _encoder_for(fingerprint):
    """Return the public key registered under `fingerprint`, or None."""
    from ..crypto import rsa as _rsa
    entry = _rsa._server_keys.get(fingerprint)
    return entry[0] if entry else None


def sha1_encrypt(fingerprint, data, *, use_old=False):
    """RSA-PAD replacement for `catethon.crypto.rsa.encrypt`.

    Same signature and same two attempts (current key, then old key) the
    authenticator already makes, so installing it needs no other change. When it
    cannot produce a block for the given key it returns None, exactly as
    upstream does, and the authenticator's own error path runs.
    """
    key = _encoder_for(fingerprint)
    if key is None:
        return None
    try:
        return rsapad(bytes(data), key)
    except ValueError:
        return None


def patch_authenticator():
    """Make `catethon.network.authenticator` use RSA-PAD for key exchange.

    `network/authenticator.py` imported `rsa` and calls `rsa.encrypt(...)`.
    Rebinding the module attribute is the smallest change that survives a file
    replacement: upstream's source is untouched, and this function re-applies on
    each call. Idempotent.
    """
    from ..network import authenticator
    authenticator.rsa.encrypt = sha1_encrypt
    return authenticator
