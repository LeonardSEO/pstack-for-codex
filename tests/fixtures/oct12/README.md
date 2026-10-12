# October 12 sync regression

These snapshots contain all 28 sync-managed files changed between cursor/plugins
11713c683fe4add4fd403ea880580abbc9e0875f and
1b6d44ff26d4e242f4e8f68c391e6d2f7ca16def. `codex-before` contains their
existing fork counterparts at LeonardSEO/pstack-for-codex
d1b75c905cd1f95b0a0d1b5fb90f59e166b68e1e. The manifest records the source
commits, byte hashes and file modes. A missing counterpart represents an addition.

The regression installs these exact revisions into a local fixture Git repository
and validates the complete proposed plugin offline. The remaining plugin files
come from the checkout; the test restores every pending counterpart before sync.
Upstream README and manifests are outside the synchronizer's managed paths.

Copyright (c) 2026 Cursor. Original material is MIT licensed; see the repository LICENSE.
