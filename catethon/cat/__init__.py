"""Cat-project helpers layered on top of upstream Telethon.

Everything in this package is *ours*, and nothing in the rest of catethon
imports it. The upstream tree stays byte-identical apart from the mechanical
`telethon` -> `catethon` rename, so a rebase onto a new upstream release never
merges this code. Keep it that way: a helper that must be called from inside
`catethon.client` belongs in cat-server, not here.

What lives here answers questions the Go side of the project already settled:

- `.config`  -- api_id/api_hash, device identity and proxy source taken from
  the same environment `cmd/giftfetch` and `cmd/bots/grammystore` read, so a
  Python tool and a Go fetcher describe the same client.
- `.session` -- turn an environment StringSession into one the Go parser in
  `td/session` provably accepts, before any network call.
- `.proxy`   -- the URL -> proxy-tuple translation those tools need.

Nothing here reads an account token or writes a session to disk on its own;
the caller owns that, the way the Go fetchers leave the session file to the
operator.
"""

from .config import CatClientSettings, from_env
from .proxy import parse_proxy
from .session import session_from_env, string_session_for

__all__ = [
    'CatClientSettings',
    'from_env',
    'parse_proxy',
    'session_from_env',
    'string_session_for',
]
