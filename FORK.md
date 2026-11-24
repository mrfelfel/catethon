# catethon

catethon is a fork of **[Telethon](https://codeberg.org/Lonami/Telethon)**, the
asyncio MTProto client for Telegram, maintained for the
[cat-server](https://github.com/mrfelfel/cat-server) project.

- Upstream: Telethon 1.46.0, layer 233, MIT
- This fork: `1.46.0+catethon`, MIT, import package `catethon`
- Rebase log and verification: [`UPSTREAM_SYNC.md`](UPSTREAM_SYNC.md)

## What the fork changes

Almost nothing, on purpose. The tree is upstream's, mechanically renamed from
`telethon` to `catethon` so it installs beside an upstream Telethon instead of
over it. The only original code is `catethon/cat/`: small helpers that read the
api_id/api_hash, proxy and session values the project's Go tools already use,
and turn a StringSession into one the project's Go parser provably accepts.

`catethon.cat` is never imported by upstream code, which is what keeps a rebase
onto a future Telethon mechanical. If you are adding a helper that must be
called from inside the client, it belongs in cat-server, not here.

## Install

catethon is not on PyPI. Install from the fork:

```bash
pip install "git+https://github.com/mrfelfel/catethon.git@catethon/main#egg=catethon"
# with the SOCKS extra, for outbound sessions behind a proxy:
pip install "catethon[socks] @ git+https://github.com/mrfelfel/catethon.git@catethon/main"
```

cat-server takes it as the git submodule at `vendor/catethon`; see that repo's
`docs/catethon.md` for the decision chain and which services are meant to use
it.

## Use

```python
from catethon import TelegramClient
from catethon.cat import from_env, parse_proxy, session_from_env

settings = from_env()                       # api_id/api_hash, proxy, device name
session = session_from_env()                # CATETHON_SESSION / TELETHON_SESSION
async with TelegramClient(
    session or 'giftfetch',
    settings.api_id,
    settings.api_hash,
    proxy=parse_proxy(settings.proxy_url),
    **settings.client_kwargs(),
) as client:
    ...
```

Everything Telethon documents still works; only the import root changed. The
upstream documentation, examples and `tl.telethon.dev` reference all apply as
written, substituting `catethon` for `telethon` in imports.

## Licence

MIT, identical to upstream. The upstream copyright notice is preserved in
[`LICENSE`](LICENSE); the fork does not relicense anything. See
[`NOTICE`](NOTICE) for the provenance statement MIT requires us to keep.
