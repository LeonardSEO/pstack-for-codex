# Codex runtime contract

These rules govern every skill, reference, playbook and helper in this fork. Follow the host's system/developer instructions, repository AGENTS.md and the user's authorized scope first.

## Native tools and delegation

Discover actual tools from the current host. For shell, files, plans and questions use the exposed equivalents of exec_command, apply_patch, update_plan and request_user_input. Questions have the schema and option limits the host actually exposes. Use plain chat when no structured question tool exists. Never invent tool arguments.

When native delegation is available and permitted, use spawn_agent with task_name and a self-contained message. In ChatGPT Work, collaboration tools are direct calls, not nested tools in functions.exec. Use send_message, followup_task, list_agents, interrupt_agent and wait_agent only when exposed. Consult the actual schema. Do not pass Cursor task-type, environment, background, branch or read-only flags. A read-only role is a prompt constraint, not a tool-enforced sandbox. All agents may share one filesystem. Give each writer an isolated worktree or disjoint files, explicit scope and a verification contract. Do not assume an agent automatically gets another machine, a pushed branch, credentials or the user's desktop.

spawn_agent returns an agent identifier or task name, not its findings. Collect completion messages or use the host’s native wait/result tools; drain all required terminal results before synthesis. For blinded evals and bakeoffs, explicitly use fork_turns: none when supported and pass only the task, required grounding and isolated output path. Keep the rubric and rival candidates out of the candidate history. If clean history isolation is unavailable, report the eval as contaminated and do not promote based on it.

Give engineering delegates the path to agents/poteto-agent.md and require them to read poteto-mode first. Give comment reviewers agents/comment-sicko.md and the scoped diff. Other workflow roles use their bundled reference prompts. Default to the parent model and effort. Only select a different model or effort when the host explicitly supports the value and the user or applicable repository instructions authorize it. Never guess model identifiers or fall back to another family after an error. Report unsupported selections and inherit the parent. Two runs of one model do not constitute model diversity or calibrated evidence of correctness.

When delegation is unavailable, disallowed or exceeds the exposed concurrency limit, perform the same exploration, alternatives and review phases sequentially. Label sequential self-review as such; do not claim independent verification. Preserve every required check. Independent verification that is an enforced shipping gate remains blocked until a permitted independent reviewer is available.

## Configuration and paths

poteto-mode explicitly reads .agents/pstack-config.md in the current project if it exists. This file is not a Codex auto-loaded rule. Missing config means inherit-parent for all roles, two candidates for comparisons, and session-bounded execution. Never rewrite the host's config.toml or global AGENTS.md to set model defaults.

Resolve sibling skills and helper paths relative to this plugin's root or the current skill file, regardless of the installation/cache path. Project-local generated skills use .agents/skills/<name>/SKILL.md. Do not assume nested personal categories are discoverable. Plugin support scripts may require Bash, Node, Bun, git, gh or jq; check their availability before invoking them. The Bun PR watcher can install its locked dependencies through its bundled bootstrap; inspect that bootstrap before running it. Do not claim authenticated forge access from executable presence alone.

## History, sessions and integrations

Read only transcripts explicitly identified by the host or user and scoped to the current task. If none are exposed, use available in-session context, a permitted history connector, the user's state capsule and live git/issue state. Do not scan unrelated home-directory chats. Report a missing transcript receipt rather than claiming a history audit happened.

A sustained loop is repeated verified work in the current session. No skill schedules itself, survives restart, creates cloud agents or wakes a closed session. Future or recurring work requires an available scheduling tool, user scheduling intent and confirmation from that tool. A restart invalidates agent IDs unless the host proves otherwise; recover from persisted artifacts and live state. Benny templates are historical automation examples only.

Use connected MCP tools and project harnesses only when present and authorized. For browser/desktop control follow the host's interaction policy and supported tools; a browser is not automatically available. For webhook UIs use only verified backend endpoints and supported secret handling. No plugin-owned MCP server, credentials, cloud runner or webhook is installed by this package.

## Scope, writes and claims

Reversible work within the request can proceed. Sending messages, publishing, merging, deploying, deleting data, force-pushing and enabling recurring jobs require authorization covering that action and compliance with host approval rules. Never grant permission on the user's behalf. Preserve unrelated and uncommitted work. Use fresh worktrees instead of resetting a dirty checkout. A plan to open a PR does not itself authorize posting arbitrary messages or merging it. Open a PR only when the request or repository workflow warrants it.

Name which checks actually ran, their evidence and limitations. Static package validation proves structure, not successful installation on the user's Mac or every external integration. Report blocked checks as blocked, never as passed.

## Skill authoring

For creating or editing a skill, preserve supplied source and read an available host skill-authoring skill when present. Otherwise follow this bundled procedure: use a lowercase kebab-case folder matching YAML name; include name and a precise trigger description in SKILL.md frontmatter; keep actionable workflow steps in the body and conditional detail in referenced files; resolve support paths relative to the skill; expose only actual host tools; validate YAML and local links; run scripts and representative isolated tasks; report untested integrations. Optional agents/openai.yaml can provide presentation and policy.allow_implicit_invocation: false where supported. Do not claim a description-optimization harness exists unless available. Save through the host's actual plugin/skill persistence flow, preserving existing identity for updates. A local file alone is not proof of account installation.
