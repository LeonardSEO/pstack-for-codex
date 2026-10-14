# Upstream synchronization and Codex adaptations

The October 12 and 13 failures came from complete-file rewrite guards, not Git
conflicts. A display-name normalization and then an inserted absolute-path
instruction changed a source hash. Keeping the old rewrite under a new accepted
hash would have discarded the second change's intent.

## Comparison with pstack-claude

Inspected michael-denyer/pstack-claude at
[990cd7b](https://github.com/michael-denyer/pstack-claude/tree/990cd7b02ac6f3e8f825716f7c72e2f06d8f4a92).
Its [sync tool](https://github.com/michael-denyer/pstack-claude/blob/990cd7b02ac6f3e8f825716f7c72e2f06d8f4a92/tools/sync.mjs)
uses scoped mechanical substitutions, runtime derivation and three-way merges of
old upstream, new upstream and the local port. Its `forks.json` records deliberate
port features and policy deviations with a reason. Undeclared forks and denylist
hits block writes. Symlinks, binary conflicts and path collisions receive explicit
handling. This keeps compatible changes flowing without treating an entire
file as an approved instruction set.

The comparison has a different publication boundary. Its sync can write text
conflict markers and advance the pin. The generator and
[CI](https://github.com/michael-denyer/pstack-claude/blob/990cd7b02ac6f3e8f825716f7c72e2f06d8f4a92/.github/workflows/ci.yml)
then reject unresolved markers, check declared forks at the pin, validate generated
files, and run fixtures, helper tests and other package checks. The inspected
workflows contain CI and security checks, rather than a scheduled sync publisher.
Its [release instructions](https://github.com/michael-denyer/pstack-claude/blob/990cd7b02ac6f3e8f825716f7c72e2f06d8f4a92/CONTRIBUTING.md#releasing)
require a version change, changelog entry and regenerated manifests in the change
or a following release PR.

## Design in this fork

Our daily workflow publishes directly after validation, so conflicts remain a
hard stop before package writes, version changes or checkpoint advancement. We
adopt derivation and declared forks while retaining this stricter boundary.

- Small translations replace recognized host-specific instructions. Missing or
  rewritten fragments pass through instead of requiring an exact-source exception.
  Portable role identifiers use scoped mechanical substitutions. The complete
  staged package is the compatibility boundary; ambiguous matches still block.
- Engineering roles retain the source description and body after metadata and
  tool adaptation. The Codex runtime preamble remains authoritative. The parent
  owns the playbook; delegates read the actual absolute skill path supplied by
  their parent. The previous entire delegation block is now several translations,
  so inserted instructions no longer disappear behind a block replacement.
- Policy forks record immutable normalized upstream text, its Codex counterpart
  and a rationale in `codex_adaptations.json`. A new source is merged against
  those anchors. Overlapping changes or competing clean results block. No new
  whole-file accepted hash is needed for a compatible edit. Edits within an
  intentionally replaced policy can still require review.
- `legacy_renderings` provide the one-time three-way transition from historical
  compact role/block rewrites to the derived representation. They are not a gate
  on future upstream sources. Real local edits survive a clean transition; a
  collision remains a conflict. The live fork never supplies an upstream base.
- Validation scans both skill Markdown and agent Markdown for unsupported host
  instructions, model identifiers, unresolved markers and broken local links.
  The complete candidate is validated in staging before applying any changes.
- Thermo-Nuclear's directory is excluded from synchronization and its attribution
  remains independent. A repeat at the checkpoint validates and writes nothing.

This is not a semantic proof of arbitrary prose. Git determines textual
compatibility; protected translations, policy forks and runtime validation enforce
known boundaries. New unsupported capabilities, ambiguous translations, overlapping
policy changes or an upstream change in a deliberately replaced region can still
need human review. Do not add a blanket ours/theirs resolution or advance the pin
to make a failed sync look successful.

## Regression evidence

The offline October 12 fixture replays all 28 changed managed paths, including the
name-only change. The October 13 fixture replays both managed paths at pinned
source `1dcc2bacde73ddd284803b7af28164d0436198fc` from checkpoint
`1b6d44ff26d4e242f4e8f68c391e6d2f7ca16def`. Tests also apply future semantic edits
within the role and parent paragraph, preserve local notes and Codex policy,
reject unsupported host flags, prove conflict and
validation-failure atomicity, and repeat synchronization without changes.

The later October 13 update exposed another complete-file fork: poteto-help had
replaced the upstream skill table with a compact summary. Adding a skill or
changing a table description therefore collided with the rewrite. The help page
now preserves upstream routing content and translates only host-specific
instructions. Its old fork pairs are migration inputs, not future merge anchors.
Delegate discovery resolves the skill in the same installed plugin, or asks the
parent for its absolute path, instead of searching Cursor installations.

The `oct13-latest` fixture replays all seven managed paths from `1dcc2bac` to
`dbf49813` (upstream pstack 0.15.23), including the new in-your-own-words skill
and ketchup changes. It also tests later help-table edits without new registry
entries, local-note preservation, compatibility failures, and an
unchanged second sync. Historical fixtures derive their expected skill count
from the package plus the fixture's additions/deletions so new bundled skills
do not invalidate unrelated regression checks.

The October 14 fixture replays all 39 managed paths from `dbf49813` to
`1e5c90a4` (pstack 0.15.24). It covers future additions to translated paragraphs
and complete rewrites using native host instructions. Both sync automatically;
unsupported Cursor syntax and genuine local edit conflicts still fail atomically.

## Version and runner policy

The plugin takes its version from `pstack/.cursor-plugin/plugin.json` at the exact
upstream commit being synchronized. There is no separate Codex patch counter.
Version-only changes and the migration from a former 1.0.x version are validated
and applied through the same staging path. Missing or invalid source versions
block all writes. Existing published tags are not moved or overwritten.

Both GitHub Actions workflows use `ubuntu-24.04`, avoiding automatic migration
of `ubuntu-latest` to Ubuntu 26. Runner upgrades are explicit repository changes.
