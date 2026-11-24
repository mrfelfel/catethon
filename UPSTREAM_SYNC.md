# Upstream sync log

catethon is a fork of Telethon. This file records, for each upstream release
we move to, what was taken, what was left alone, and how the move was
verified. It is the Python-side counterpart of `td/UPSTREAM_SYNC.md`.

Read this before rebasing. The rule that makes rebasing cheap: **our code lives
in `catethon/cat/` and `tests/telethon/cat/` and nowhere else.** Everything else
in the tree is upstream's, changed only by the mechanical `telethon` ->
`catethon` rename.

## Base: Telethon 1.46.0

- Adopted upstream: Telethon **1.46.0**, **layer 233**
- Source: PyPI sdist `telethon-1.46.0.tar.gz`, sha256
  `8357f5719376a9c1ddf0999136a44594a5b21b453647f1e146c169483b6a67df`,
  uploaded 2026-11-17
- Upstream home: <https://codeberg.org/Lonami/Telethon>

### Why 1.46.0 and not the GitHub repository

The GitHub repository `LonamiWebs/Telethon` was **archived on 2026-02-09** and
its README points at Codeberg. Its `v1` branch stops at **layer 222**. Telethon
1.46.0, published seven months later from Codeberg, ships **layer 233**. The
project's own TDLib harness is pinned at layer 230 and the `td` Go fork covers
225-233, so 1.46.0 is the first Telethon whose schema overlaps what cat-server
speaks. That overlap, not the version number, is why this base was chosen.

Codeberg was unreachable from the build host when this fork was cut
(`:443` refused on the Iran network). PyPI is reachable, so PyPI is the
authoritative import source. Use PyPI again on the next rebase unless Codeberg
becomes reachable, in which case prefer Codeberg and record the tag commit.

### Changes taken

| Change | Decision |
|---|---|
| `telethon/` -> `catethon/` | Import package renamed so the fork installs beside, never over, an upstream `telethon`. 42 files carried absolute self-imports; all rewritten. |
| `pyproject.toml` packaging paths | `name`, `[tool.hatch.version] path`, sdist `include` follow the rename. |
| Distribution metadata | Name `catethon`, version `1.46.1`, MIT kept, upstream author kept. The `+catethon` local segment was dropped: PyPI refuses local versions. |
| `key.startswith("telethon.")` in `client/telegrambaseclient.py` | Now `"catethon."`. The base logger already derives from `__name__`, so only this child-key strip needed the new spelling. |
| `catethon/cat/` | Our helpers. Never imported by upstream code. |
| `catethon/cat/rsapad.py` | RSA-PAD key-exchange block. Cat Messenger's server rejects upstream's sha1 form with `-404 "hash mismatch"`; patched in by assignment so upstream files stay clean. |
| `tests/telethon/cat/` | Tests for `catethon/cat/` only. Survives a wholesale test-tree replace. |

### Deliberately left alone

| Thing | Why |
|---|---|
| Product name "Telethon", `README.rst`, all upstream URLs (`telethon.dev`, `telethon.rtfd.io`) | Attribution and honest provenance. A `catethon.dev` link would not resolve. |
| TL schema and generated `catethon/tl/` | Layer 233 as upstream shipped it. Regenerating needs `telethon_generator/`, which the sdist omits. |
| The `telethon_generator/` references in `setup.py` | Dead in the sdist (the directory is absent); harmless, and keeping them makes a future rebase onto a full source checkout trivial. |
| Upstream test failures | Three `tests/telethon/client/test_messages.py` cases fail identically on unmodified 1.46.0 (the GitHub 1.42 tests do not match 1.46 source). Not ours to fix; recorded so a future rebase does not chase them. |

### Broken build hook, fixed

Every published 1.45/1.46 **sdist** is uninstallable: `pyproject.toml` names
`[tool.hatch.build.hooks.custom]`, but the sdist does not contain
`hatch_build.py`, so `pip install .` dies with
`OSError: Build script does not exist: hatch_build.py`. The hook only
regenerates TL from `telethon_generator/`, which the sdist also omits, and our
`catethon/tl/` is already generated and committed. The stanza is removed; that
removal is what makes the fork installable. Do not re-add it without also
shipping the generator and the hook.

## How to rebase onto a new upstream release

1. Get the new upstream sdist (PyPI, or Codeberg git if reachable). Record its
   version, layer and sha256 here.
2. Unpack it into a clean tree. `git rm` the previous `catethon/` sources and
   replace them with the new `telethon/`.
3. Run the rename over the new tree, **skipping** lines that name a real
   external host (`telethon.dev`, `telethon.rtfd.io`, `*.telethon.dev`).
4. Re-apply the three packaging edits: `name`, hatch version path, sdist
   include. Re-remove the custom build-hook stanza if upstream sdist still
   lacks `hatch_build.py`.
5. Copy `catethon/cat/` and `tests/telethon/cat/` back unchanged. If a helper
   broke, the upstream API it leaned on moved -- fix the helper, not upstream.
6. Bump `UPSTREAM_VERSION` / `UPSTREAM_LAYER` in `catethon/version.py` and the
   version string.
7. Verify (see below) and commit the base import and the rename as separate
   commits, as the first two commits did.

## Verification

Run from a Python 3.9+ interpreter with a `pip` cache on a roomy volume:

```bash
python -m pip install .            # must build and install
python -c "import catethon; print(catethon.__version__, catethon.tl.alltlobjects.LAYER)"
python -m pytest tests/telethon/cat/ -q          # our helpers: must be green
python -m pytest tests/ -q                       # upstream subset: 3 known fails
```

The StringSession interop with the Go side is checked in cat-server, not here:
`td/session.TelethonSession` must decode what `catethon.cat.string_session_for`
produces. Keep both halves in step -- the format version byte is `'1'` on both.

## 2026-11-24: initial import

- Base: 1.46.0, layer 233, PyPI sdist sha256 recorded above
- Fork commits: `Import Telethon 1.46.0 (layer 233) verbatim`, then
  `Rename the import package telethon -> catethon`, then the helpers commit
- Fork repo: <https://github.com/mrfelfel/catethon>, branch `catethon/main`
- Verified: `pip install .` green; `import catethon` -> `1.46.0+catethon`,
  layer 233; `tests/telethon/cat` 23 passed; full subset 55 passed, 3 known
  upstream drifts; Go `td/session` decoded `catethon.cat.string_session_for`
  output with DC, IP, port and 256-byte key intact

### 2026-11-24 — public client for Cat Messenger

The fork is now the public Python client for Cat Messenger ("The Cat"), not just
an internal helper: `README.md` targets outside users and `catethon/cat/server.py`
defaults to the production edge so `prepare()` connects on install.

Connect values, all verified against the live server on 2026-11-24:

- host `62.220.127.238`, port `30001`, DC `2`, TCP (abridged and full both
  accepted on the plain port; `ConnectionTcpObfuscated` at the wrapper level
  works too)
- server public key packaged at `catethon/cat/keys/thecat-prod-rsa.pub`,
  SHA-256 `7514f405f0c0969b5cc0301c6cfff9ad3d507bdb4471db5397f3e7447da60395`
- the live server's resPQ announces fingerprint `0x19a8af0a0c89b11a`, which is
  what `catethon.crypto.rsa._compute_fingerprint` derives from the packaged key —
  a direct check that the baked key is the server's key, not just a doc copy
- `client.connect()` completes (new auth key created); `is_user_authorized()` is
  False until a phone login, as expected

The handshake only completes with RSA-PAD, not upstream's sha1 scheme; see the
commit message for `catethon/cat/rsapad.py` and `td/crypto/rsa_pad.go`.
