![pstack for Codex — Engineering workflows. Verified delivery.](assets/pstack-for-codex-banner.png)

# pstack for Codex

**Engineering workflows for OpenAI Codex: investigate, design, implement, review, and verify.**

[![Validate plugin](https://github.com/LeonardSEO/pstack-for-codex/actions/workflows/validate.yml/badge.svg)](https://github.com/LeonardSEO/pstack-for-codex/actions/workflows/validate.yml)
[![Upstream sync](https://github.com/LeonardSEO/pstack-for-codex/actions/workflows/sync-upstream.yml/badge.svg)](https://github.com/LeonardSEO/pstack-for-codex/actions/workflows/sync-upstream.yml)
[![Latest release](https://img.shields.io/github/v/release/LeonardSEO/pstack-for-codex)](https://github.com/LeonardSEO/pstack-for-codex/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An independent Codex adaptation of [Lauren Tan’s pstack](https://github.com/cursor/plugins/tree/main/pstack), with 52 core skills, 23 playbooks, and an additional **Thermo-Nuclear Code Quality Review**. Start with a goal and a checkable completion criterion. The workflows guide your agent through understanding the code, choosing an approach, making the change, and reporting evidence.

[Install](#install) · [Examples](#start-with-a-real-task) · [Skills](#choose-a-workflow) · [Updates](#updates-and-releases) · [Compatibility](#how-it-runs-in-codex)

## Install

Use a Codex CLI version with plugin marketplace support. Run in your terminal:

```bash
codex plugin marketplace add LeonardSEO/pstack-for-codex --ref main
codex plugin add pstack-for-codex@leonardseo-pstack
```

Start a **new Codex session** in your project, then invoke:

```text
$poteto-mode Fix the search filter resetting when I change pages.
Done when the selected filter survives pagination and a regression test passes.
```

You can also select the skill from your host’s skill picker. No separate model setup is required: workflows inherit the current Codex model by default.

If your CLI reports an unknown `plugin` command, update Codex to a version that supports plugins. Installation commands register the marketplace and install the plugin; they do not change your application code.

## Start with a real task

Give the agent a concrete outcome and the evidence you expect.

**Fix a regression**

```text
$poteto-mode Fix duplicate submissions when Save is clicked twice.
Done when only one record is created and the regression test passes.
```

**Understand a subsystem**

```text
$how Explain how authentication reaches the API in this repository.
Include ownership boundaries and references to the relevant code.
```

**Review a change without editing**

```text
$thermo-nuclear-code-quality-review Audit this branch against main.
Focus on structural complexity, unnecessary abstractions, and branching growth.
Report actionable findings with file and line references. Do not edit files.
```

**Compare implementation options**

```text
$arena Compare two approaches to caching the product list.
Judge them on correctness, invalidation behavior, and maintenance cost.
```

Parallel candidates require available and permitted native agent tools. When delegation is unavailable, the runtime contract specifies sequential fallback and disclosure of the verification limits.

## Choose a workflow

| Your goal | Skill | What it guides |
| --- | --- | --- |
| Take a task from investigation to verification | [`poteto-mode`](plugins/pstack-for-codex/skills/poteto-mode/SKILL.md) | Select a playbook and coordinate the work |
| Understand existing behavior | [`how`](plugins/pstack-for-codex/skills/how/SKILL.md) | Trace architecture, runtime flow, and ownership |
| Understand a design decision | [`why`](plugins/pstack-for-codex/skills/why/SKILL.md) | Investigate motivation and supporting evidence |
| Design a change across boundaries | [`architect`](plugins/pstack-for-codex/skills/architect/SKILL.md) | Examine structure before implementation |
| Compare alternative solutions | [`arena`](plugins/pstack-for-codex/skills/arena/SKILL.md) | Evaluate candidates and verify the synthesized result |
| Challenge a proposed design | [`interrogate`](plugins/pstack-for-codex/skills/interrogate/SKILL.md) | Apply adversarial review to assumptions and tradeoffs |
| Audit maintainability strictly | [`thermo-nuclear-code-quality-review`](plugins/pstack-for-codex/skills/thermo-nuclear-code-quality-review/SKILL.md) | Identify structural regressions and opportunities to remove complexity |
| Check what a change could break | [`blast-radius`](plugins/pstack-for-codex/skills/blast-radius/SKILL.md) | Examine downstream effects and prove key safety assumptions |
| Develop through observable behavior | [`tdd`](plugins/pstack-for-codex/skills/tdd/SKILL.md) | Use failing and passing tests to guide implementation |
| Make verification reusable | [`create-verification-skill`](plugins/pstack-for-codex/skills/create-verification-skill/SKILL.md) | Record a repeatable project verification workflow |
| Improve technical documentation | [`technical-writing`](plugins/pstack-for-codex/skills/technical-writing/SKILL.md) | Structure explanations around the reader’s task |
| Find your next workflow | [`poteto-help`](plugins/pstack-for-codex/skills/poteto-help/SKILL.md) | Explore the available skills and their uses |

The [full skill collection](plugins/pstack-for-codex/skills) also includes engineering principles covering domain models, type boundaries, root causes, idempotency, and behavior-focused tests.

The [23 playbooks](plugins/pstack-for-codex/skills/poteto-mode/playbooks) cover bug fixes, features, refactoring, performance investigations, prototypes, evaluations, PR preparation, shipping, and session recovery. Each workflow remains subject to your project instructions and authorized scope.

## How it runs in Codex

The port adapts the workflows to Codex’s exposed capabilities:

- **Native tools:** use the host’s actual shell, file, question, and agent tools.
- **Inherited models:** keep the current model and reasoning settings unless a supported override is authorized.
- **Explicit configuration:** optional project preferences live in `.agents/pstack-config.md`, which `poteto-mode` reads explicitly.
- **Clear approval boundaries:** repository instructions and host permissions govern publishing, deployment, messages, and destructive actions.
- **Honest verification:** distinguish static package checks, tests, independent review, and live integration evidence.

The package supplies skills, playbooks, reference prompts, and portable helpers. Browser access, forge authentication, credentials, MCP servers, and cloud runners depend on your host. Session loops end with the session; future wakeups require a separate scheduling capability. Benny resources are retained as historical references.

Read the [runtime contract](plugins/pstack-for-codex/CODEX-RUNTIME.md) for execution rules and the [compatibility report](plugins/pstack-for-codex/COMPATIBILITY.md) for conversion scope and verification limits. Helper scripts may require their documented runtimes, such as Bash, Node, Bun, `git`, `gh`, or `jq`.

## Updates and releases

### Follow validated updates on main

A [GitHub Action](.github/workflows/sync-upstream.yml) checks pstack upstream daily at **04:17 UTC** and supports manual runs. It merges compatible upstream changes with the Codex adaptations, runs validation, increments the plugin patch version, and commits to `main`. It then publishes a matching GitHub release: version `1.0.2` becomes tag `v1.0.2`, with release notes, a ZIP snapshot, and a SHA-256 checksum. Conflicts, unsupported instructions, or validation failures stop publication. The synchronizer requires no AI API key and does not execute upstream helper code.

Refresh your installation:

```bash
codex plugin marketplace upgrade leonardseo-pstack
codex plugin add pstack-for-codex@leonardseo-pstack
```

Start a new session after updating. GitHub may delay scheduled runs and disables schedules in inactive public repositories after 60 days. Repository branch rules must permit the sync workflow to push.

### Use a versioned snapshot

[Releases](https://github.com/LeonardSEO/pstack-for-codex/releases) provide tagged snapshots and release notes. For a fresh installation pinned to this release, replace `--ref main` in the installation command with `--ref v1.0.1`. A pinned marketplace stays on that ref until you change it.

Each automated release includes a ZIP archive and a SHA-256 checksum. The marketplace commands above are the recommended installation route. Runs without upstream changes do not increase the version. After validation, the workflow ensures the current version has a release, skips an already published release, and can finish a draft left by an interrupted upload. Assets are uploaded before the release becomes public.

### The additional review skill stays independent

[`thermo-nuclear-code-quality-review`](plugins/pstack-for-codex/skills/thermo-nuclear-code-quality-review/SKILL.md) comes from [Cursor’s cursor-team-kit](https://github.com/cursor/plugins/blob/main/cursor-team-kit/skills/thermo-nuclear-code-quality-review/SKILL.md). Its entire directory is excluded from pstack synchronization, including additions, edits, and deletions of a same-name upstream skill. This skill is maintained manually, with its [MIT attribution](plugins/pstack-for-codex/LICENSE-cursor-team-kit) preserved.

## Maintenance and contributions

Documentation corrections, compatibility fixes, and reproducible bug reports are welcome. [Open an issue](https://github.com/LeonardSEO/pstack-for-codex/issues) with the plugin version, Codex version, invoked skill, expected result, and relevant evidence. Remove credentials and private data before sharing logs.

For changes to the package or synchronizer, run the repository checks:

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
python3 scripts/validate.py
```

The sync uses the commit in [`upstream.json`](upstream.json) as its source base. It normalizes skill metadata and applies the reviewed Codex translations in [`scripts/codex_adaptations.json`](scripts/codex_adaptations.json) to both upstream revisions before merging with the live fork. This lets wording changes around translated instructions flow through while preserving separately maintained fork edits. The runtime contract and independent review skill remain maintained in this fork.

Translations match exact source fragments, not fuzzy patterns. Unknown edits to a translated instruction, duplicate matches, conflicting fork edits, and unreviewed changes to complete Codex rewrites stop the sync. Complete rewrites and reviewed removal of obsolete instructions require the exact normalized source SHA-256. To extend the translations, compare both source revisions and the current fork, preserve the intended upstream behavior under the Codex runtime contract, and add a regression before accepting a new variant. Never generate a merge base from the current fork or add a blanket resolution for an entire skill.

The synchronizer validates a staged copy of the complete proposed package before writing files, incrementing the saved version, or advancing the checkpoint. A repeated sync of the same source is a validated no-op. The workflow validates again before committing or releasing. Package checks validate metadata, local skill links, and compatibility rules; they do not prove every workflow or external integration works in your environment.

## Credits and license

Based on [Lauren Tan’s pstack](https://github.com/cursor/plugins/tree/main/pstack), with the additional review skill from [cursor-team-kit](https://github.com/cursor/plugins/tree/main/cursor-team-kit). Original copyright notices are preserved in [LICENSE](LICENSE) and [LICENSE-cursor-team-kit](plugins/pstack-for-codex/LICENSE-cursor-team-kit).

An independent, MIT-licensed adaptation for Codex. This project is not an official Cursor or OpenAI distribution. See [OpenAI’s plugin packaging documentation](https://developers.openai.com/plugins/build/plugins) for the plugin and marketplace formats.
