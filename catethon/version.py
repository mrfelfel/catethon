# Versions should comply with PEP440.
#
# `1.46.1`: the fork's own patch release on top of upstream 1.46.0. A local
# segment (`1.46.0+catethon`) is how a *downstream rebuild* is labelled; PyPI
# refuses to upload one ("Cannot use PEP 440 local versions"), so a package
# people `pip install catethon` has to carry a plain public version. 1.46.1
# sorts above the 1.46.0 base and below what upstream 1.46.x would be, which is
# the intended order for a fork release.
__version__ = '1.46.1'

# The upstream release this fork is cut from. UPSTREAM_SYNC.md in the repo root
# records which changes were taken and which were deliberately dropped; keep
# this string in step with the base commit message and that log.
UPSTREAM_VERSION = '1.46.0'
UPSTREAM_LAYER = 233
