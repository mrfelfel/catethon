# catethon

**catethon is the Python client for Cat Messenger (`The Cat`).**

It speaks MTProto to Cat Messenger's own servers — not to Telegram's cloud —
so a Python program can log in, read chats, send messages, and fetch media on
The Cat the same way a phone app does.

catethon is a fork of [Telethon](https://codeberg.org/Lonami/Telethon), the
long-standing asyncio MTProto library. The protocol engine is Telethon's; what
this fork adds is the Cat Messenger server, its public key, and sensible
defaults, so that connecting is one line instead of a runbook.

- Import name: `catethon`
- Distribution name: `catethon`
- Version: `1.46.0+catethon` (upstream Telethon 1.46.0, layer 233)
- Licence: MIT (upstream's, unchanged — see [`NOTICE`](NOTICE))
- Cat Messenger: <https://catroom.ir> · source: <https://github.com/mrfelfel/catethon>

## Install

catethon is not on PyPI. Install it from this repository:

```bash
pip install "catethon @ git+https://github.com/mrfelfel/catethon.git@catethon/main"
```

Behind a SOCKS proxy (many networks need one to reach Cat Messenger):

```bash
pip install "catethon[socks] @ git+https://github.com/mrfelfel/catethon.git@catethon/main"
```

Python 3.9 or newer.

## Connect to Cat Messenger

This is the whole thing:

```python
import asyncio
from catethon.cat import prepare

async def main():
    # api_id / api_hash come from Cat Messenger (the same values the official
    # apps use); see "Application id" below.
    prepared = prepare()
    client = prepared.make_client(api_id=17349, api_hash="...")

    await client.connect()
    if not await client.is_user_authorized():
        await client.send_code_request("+98...")
        await client.sign_in("+98...", input("code: "))

    async for dialog in client.iter_dialogs():
        print(dialog.name)

    await client.disconnect()

asyncio.run(main())
```

`prepare()` points the client at the Cat Messenger server, registers that
server's public key, and picks the transport. You do not choose a DC or paste
a key.

### What `prepare()` sets

| value | default | override |
|---|---|---|
| host | `62.220.127.238` | `prepare(host=...)` |
| port | `30001` | `prepare(port=...)` |
| DC id | `2` | `prepare(dc_id=...)` |
| transport | TCP full | `prepare(transport="http")` |
| server key | bundled, fingerprint-checked | — |

The server's public key ships in
[`catethon/cat/keys/thecat-prod-rsa.pub`](catethon/cat/keys/thecat-prod-rsa.pub)
and its SHA-256 is checked when it loads, so a corrupted checkout fails at
import instead of as a handshake timeout. That is the same key the production
server announces during key exchange (fingerprint `0x19a8af0a0c89b11a`).

### Application id

MTProto requires an `api_id` / `api_hash` pair that identifies the
*application*, not the user. Cat Messenger uses the published Telegram Desktop
pair, which is what `catethon.cat.config` defaults to; you can leave it alone:

```python
from catethon.cat import from_env
settings = from_env()        # api_id=17349, api_hash=..., proxy from env
```

Your phone number, login code and 2FA password are your own account
credentials and are never bundled or stored by this library.

### Proxy

If your network needs a SOCKS proxy, set it once and both the URL parsing and
the session wiring are handled:

```bash
export SOCKS5_PROXY=socks5h://127.0.0.1:1080
```

```python
from catethon.cat import from_env, parse_proxy
settings = from_env()
client = prepared.make_client(
    settings.api_id, settings.api_hash, proxy=parse_proxy(settings.proxy_url))
```

`parse_proxy` accepts `socks5://`, `socks5h://` (remote DNS), `socks4://` and
`http://`. It needs the `socks` extra.

## Sessions

Two ways to stay logged in:

- **A file session** — pass a filename: `make_client` works with Telethon's
  usual file-backed session, so the login persists on disk.
- **A session string** — export it once and reuse it:

  ```python
  from catethon.cat import session_from_env, string_session_for
  session = session_from_env()      # reads CATETHON_SESSION / TELETHON_SESSION
  ```

Session strings use Telethon's documented format, so a string made by another
Telethon tool is readable here. Treat a session string like a password: anyone
who has it is logged in as you.

## Documentation

Everything Telethon documents still applies — the client, the raw API, the
event handlers. Only the import root changed:

```python
# Telethon docs say:            catethon says:
from telethon import ...     #  from catethon import ...
```

Upstream docs: <https://docs.telethon.dev> · raw API reference:
<https://tl.telethon.dev>. Substitute `catethon` for `telethon` in import
paths.

Fork specifics — what changed, what was left alone, and how to rebase onto a
new Telethon release — are in [`FORK.md`](FORK.md) and
[`UPSTREAM_SYNC.md`](UPSTREAM_SYNC.md).

## Licence and provenance

MIT, exactly as upstream. Telethon is Copyright (c) 2016-Present LonamiWebs;
that notice is kept in [`LICENSE`](LICENSE) and the provenance statement is in
[`NOTICE`](NOTICE). The fork changes the import package name and adds
`catethon/cat/`; it does not relicense anything.
