# Authoritative upstream synchronization

Upstream pstack is the source of truth. This replaces the previous three-way merge and policy-fork design, which repeatedly blocked ordinary upstream edits in October 2026.

## Ownership

The complete committed pstack tree is rebuilt into the Codex package. Incoming additions, changes, removals and executable permissions win over local imported content, including guides, agent instructions, references and new directories. No live fork content is used as a merge base.

The manifest, CODEX-RUNTIME.md, independent review skill and its license are local. Codex skill metadata is retained for surviving skills and generated for new skills. The marketplace is outside the imported package. Incoming host configuration is kept as reference material under references-host; automations are mapped to references-benny. These mappings cannot silently collide with another incoming destination.

## Conversion and validation

Skill frontmatter is normalized and a runtime-contract preamble is added. Agent role instructions also refer to the contract. Known unambiguous text translations and mechanical substitutions apply. Missing or ambiguous translations preserve upstream text and emit warnings. Full-file policy forks and legacy merge bases are removed.

Content compatibility checks (unknown host tools, model names, conflict-like text and broken links) produce warnings. Source retrieval, unsafe file modes/paths, invalid skill metadata and invalid package/marketplace structure remain hard failures. Read all Git blobs before any replacement; do not synchronize from a sparse filesystem listing. Validate the complete temporary candidate before replacing the package and checkpoint, with rollback on ordinary filesystem exceptions. Abrupt process termination is not a filesystem transaction; the hosted worktree is disposable and nothing is committed until the operation succeeds.

## Publication

The existing 04:17 UTC schedule and workflow_dispatch remain. Every attempt fetches main and uses a temporary detached worktree with its current synchronizer. Stage only the plugin and upstream.json, commit only a real diff, and push HEAD:main without force. Retry an advanced main at most three times; authentication or branch-protection rejection fails immediately. A failure leaves the original checkout untouched. Release the exact successful candidate using the existing draft/upload/publish process. A published version is immutable; subsequent same-version updates are available on main.

The Action emits JSON and Markdown artifacts and a run summary with source commit, counts, warnings, attempt, push and release status. Content warnings do not imply a failed synchronization or complete runtime compatibility.

## Verification

Regression tests cover historical upstream fragments, direct upstream precedence, additions/deletions, binary and executable files, host-config isolation, preservation of Codex-owned content, warning-only translations, invalid/missing sources, staged validation failure, directory/file transitions and repeat idempotence. Publisher tests use real temporary Git remotes to verify a direct push, unchanged repetition, concurrent main changes, three-attempt exhaustion and denied pushes. Hosted acceptance requires an actual update and a subsequent unchanged run, not just a passing no-op.
