# Validation evidence

Validated on 2026-10-09 against pinned pstack commit ccb5507cec1546dc88135c1139c811e6c59115ba.

- 51 core skills pass the host skill validator. Folder names match YAML names; unsupported Cursor metadata was replaced by agents/openai.yaml presentation and explicit invocation policy.
- 23 playbooks retained. Runnable skill and guide relative links checked. Symbolic URL examples are template placeholders, not local dependencies.
- Root manifest passes the published Agent Plugins 1.0.0 JSON schema. Listing subtitle fits the 30-character limit. Packaged logo and composer icon exist.
- Portable helper suite: 52 tests pass, 0 fail, 206 assertions using Bun 1.4.2 in an isolated scratch copy with frozen dependencies. PR watcher strict TypeScript checking passes.
- Decision logger executed with a multiline value and spreadsheet formula prefix; TSV shape and escaping pass. Modified shell helpers pass Bash syntax checks.
- Read-only how probe explains lazy cache behavior from source without writes or delegation.
- Bug-fix probe reproduces Decimal('6.5') versus expected Decimal('15.5'), corrects quantity multiplication, and passes five behavioral tests plus a separate generator/Decimal check. No commits, PRs or external writes.
- Independent package review surfaced five compatibility issues: inconsistent count config, missing authoring guidance, inherited-history leakage, transcript assumptions and spawn-result handling. Corrections implemented and re-reviewed; final textual leftovers corrected.

Not verified: installation in the user's local Codex app, real authenticated GitHub/Origin/Graphite operations, production webhook or scheduling integrations, and live browser/desktop control. These require actual host capabilities and authorization. Account plugin creation proves acceptance and availability, not those integrations.

Benny automation materials are reference-only; no schedules, endpoints or credentials were provisioned. Upstream guide pages were replaced with concise Codex guidance. MIT attribution retained.
