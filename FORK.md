# catethon — fork notes for maintainers

For what catethon is and how to use it, read [`README.md`](README.md) first.
This file is the maintainer's view: what the fork changes, what it leaves alone,
and why.

**catethon is the Python client for Cat Messenger (`The Cat`), for anyone who
wants to connect to it** — the fork exists so that connecting is a working
default, not a runbook. It is maintained in
[cat-server](https://github.com/mrfelfel/cat-server), but it is a general client:
someone outside the project can `pip install` it from git and log in.

- Upstream: Telethon 1.46.0, layer 233, MIT
- This fork: `1.46.0+catethon`, MIT, import package `catethon`
- Rebase log and verification: [`UPSTREAM_SYNC.md`](UPSTREAM_SYNC.md)

## What the fork changes

The upstream tree is mechanically renamed from `telethon` to `catethon` so it
installs beside an upstream Telethon instead of over it. The original code, all
in `catethon/cat/`, makes the client work against Cat Messenger:

| module | what it does | why it must be ours |
|---|---|---|
| `server` | host, port, DC id, transport and the server's public key | Cat Messenger runs its own MTProto edge; upstream only knows Telegram's cloud |
| `rsapad` | the RSA-PAD (OAEP-style) key-exchange block | **the server rejects upstream's sha1 form with `-404 "hash mismatch"`** — see below |
| `config` | api_id/api_hash, device name, proxy from env | one source, shared with the project's Go tools |
| `session` | validate a StringSession against the format the Go reader decodes | the one wire format two languages must agree on |
| `proxy` | URL → Telethon proxy tuple | the Go tools document `socks5h://`; Telethon wants an object |

`catethon.cat` is never imported by upstream code. That is what keeps a rebase
onto a future Telethon mechanical.

### The one non-obvious change: RSA-PAD

Upstream Telethon encrypts `p_q_inner_data` with the original MTProto scheme
(`sha1(data) + data + random`). Cat Messenger's server is built on Telegram's
newer auth_key spec, which `td/crypto/rsa_pad.go` calls `RSAPad`:

```
data_with_padding := data + random, 192 bytes, data <= 144
data_pad_reversed := BYTE_REVERSE(data_with_padding)
data_with_hash    := data_pad_reversed + SHA256(temp_key + data_with_padding)
aes_encrypted     := AES256_IGE(data_with_hash, temp_key, 0)
temp_key_xor      := temp_key XOR SHA256(aes_encrypted)
key_aes_encrypted := temp_key_xor + aes_encrypted        (256 bytes)
encrypted_data    := RSA(key_aes_encrypted, server_pubkey)
```

Sending the sha1 form gets `-404 "hash mismatch"`: the server decrypts, reads a
hash it cannot match, and drops the handshake. `catethon.cat.rsapad` implements
the newer block and `patch_authenticator()` installs it **by assignment** into
`network/authenticator.py`'s `rsa.encrypt` call site — upstream source is
untouched, so a rebase replaces files cleanly. If a future upstream changes that
call signature, the rebase check below catches it.

Verified 2026-11-24: with the PAD encoder the server answers `ServerDHParamsOk`
and a full `client.connect()` to `62.220.127.238:30001` completes; without it,
the handshake fails at `ReqDHParams`.

### What is deliberately not changed

- Product name and URLs in prose and docstrings — attribution; a `catethon.dev`
  link would not resolve.
- The TL schema (layer 233 as shipped) — regenerating needs `telethon_generator/`,
  which the sdist does not contain.
- Upstream code beyond the rename; the custom hatch build-hook stanza removed so
  `pip install .` works at all (the sdist ships no `hatch_build.py`).

## Rebase check

```bash
python -m pytest tests/telethon/cat -q     # our helpers, incl. the PAD round-trip
```

The PAD patch depends on `network/authenticator.py` calling `rsa.encrypt(
fingerprint, data)` with that exact name and arity. If a rebase renames it, that
test and a live `connect()` both fail loudly — fix `rsapad.patch_authenticator`,
not upstream.
