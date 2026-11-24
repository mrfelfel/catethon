# Publishing catethon to PyPI

Maintainer notes. A user installs with `pip install catethon`; this file is the
part they never need to read.

**Status: prepared, not yet uploaded.** The name `catethon` is unclaimed on PyPI
(checked 2026-11-24) and the build is clean, but no PyPI credentials exist on
the build machine — see "First upload" below.

## What is already true

- `python -m build` produces `catethon-1.46.1.tar.gz` and
  `catethon-1.46.1-py3-none-any.whl`.
- `twine check` passes on both.
- The wheel imports and runs from a clean venv: `1.46.1`, layer 233,
  `prepare()` returns the production host/port.
- `catethon/cat/keys/thecat-prod-rsa.pub` ships in **both** the wheel and the
  sdist. This is load-bearing: it is a non-`.py` file inside a package, so if
  the build config ever changes, confirm it is still in the artifact — without
  it `prepare()` fails at import.

## Why the version has no `+catethon`

Earlier builds used `1.46.0+catethon`. PyPI **rejects local version identifiers**
outright (`Cannot use PEP 440 local versions`); PEP 440 reserves `name+local`
for downstream rebuilds, not index uploads. Releases therefore carry a plain
public version, `1.46.1` on the 1.46.0 base. Bump the public part for every
upload — PyPI never lets a version be reused, even after a delete.

## Releasing a new version

1. Bump `__version__` in `catethon/version.py` (public version, no `+`).
2. Update the matching line in `README.md`, `FORK.md`, `UPSTREAM_SYNC.md`.
3. Build and verify:

   ```bash
   export PIP_CACHE_DIR=/Volumes/SADDISK/pip-cache TMPDIR=/Volumes/SADDISK/tmp
   python -m venv /Volumes/SADDISK/build-venv
   /Volumes/SADDISK/build-venv/bin/pip install build twine
   /Volumes/SADDISK/build-venv/bin/python -m build --outdir /Volumes/SADDISK/dist-catethon
   /Volumes/SADDISK/build-venv/bin/python -m twine check /Volumes/SADDISK/dist-catethon/*
   # prove the key file is really in the wheel:
   unzip -l /Volumes/SADDISK/dist-catethon/*.whl | grep thecat-prod-rsa.pub
   ```

4. Dry run against TestPyPI first, then the real index:

   ```bash
   twine upload --repository testpypi dist-catethon/*
   pip install --index-url https://test.pypi.org/simple/ catethon   # smoke
   twine upload dist-catethon/*
   ```

5. Tag the commit: `git tag -a v1.46.1 -m "catethon 1.46.1"; git push origin v1.46.1`.

## First upload: the credential step

There is no `.pypirc`, no stored token, and no keychain entry on this machine,
so the first upload needs a human:

- create a PyPI account / API token and store it as
  `~/.pypirc` (`[pypi]` `username = __token__`, `password = pypi-...`) or export
  `TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-...`; and
- for TestPyPI, the same under a `[testpypi]` section.

Do not put the token in the repository, in a manifest, or in a script — a PyPI
token can publish under your name.

## Why publish at all, given the git install works

`pip install "catethon @ git+…"` needs git, network access to GitHub, and a VCS
fetch; `pip install catethon` needs only PyPI. For a library whose audience is
"anyone who wants to talk to Cat Messenger", the second is the difference
between a one-line install and a paragraph. The git path stays documented as the
fallback.
