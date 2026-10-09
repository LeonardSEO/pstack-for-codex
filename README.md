# Pstack for Codex

Codex adaptation of [Lauren Tan’s pstack](https://github.com/cursor/plugins/tree/main/pstack). Includes 51 pstack skills plus the independently maintained `thermo-nuclear-code-quality-review` skill, 23 playbooks, engineering principles and verification workflows.

## Install

```bash
codex plugin marketplace add LeonardSEO/pstack-for-codex --ref main
codex plugin add pstack-for-codex@leonardseo-pstack
```

Start a new Codex session and use `$poteto-mode` with your task and a checkable completion criterion. Native agents are used when available and permitted; otherwise phases run sequentially. The current Codex model is inherited by default.

For a strict structural and maintainability audit, invoke `$thermo-nuclear-code-quality-review` explicitly. This skill is imported from [Cursor's cursor-team-kit](https://github.com/cursor/plugins/blob/main/cursor-team-kit/skills/thermo-nuclear-code-quality-review/SKILL.md), with Codex runtime and invocation metadata. Its directory is excluded from pstack synchronization, including same-name additions, edits and deletions upstream. Updates to this additional skill are manual. Cursor's MIT attribution is preserved in [LICENSE-cursor-team-kit](plugins/pstack-for-codex/LICENSE-cursor-team-kit).

## Updates

A GitHub Action checks upstream daily at **04:17 UTC** and can also run manually. Compatible upstream changes are merged with the Codex adaptations, validated, versioned and committed directly to `main`. Conflicts, unsupported instructions and validation failures stop the run without pushing. No API key or paid AI conversion is required.

```bash
codex plugin marketplace upgrade leonardseo-pstack
codex plugin add pstack-for-codex@leonardseo-pstack
```

GitHub can delay scheduled runs and disables schedules in inactive public repositories after 60 days. Branch rules must allow the repository’s GitHub Actions token to push to `main`.

## Maintenance

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
python3 scripts/validate.py
```

The sync uses the pinned commit in `upstream.json` as the merge base. Resolve any blocked upstream changes manually, preserve the runtime contract, and advance that checkpoint only after validation. Upstream helper code is never executed by the publishing workflow.

[OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins) defines the root `plugin.json`, `skills/` layout, OpenAI extension metadata and marketplace format. This is an independent MIT-licensed adaptation, not an official Cursor or OpenAI plugin. Copyright attribution is preserved in `LICENSE`.
