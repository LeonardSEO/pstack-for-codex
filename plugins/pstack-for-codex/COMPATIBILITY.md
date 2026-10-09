# pstack for Codex compatibility report

Source: https://github.com/cursor/plugins/tree/main/pstack
Pinned commit: ccb5507cec1546dc88135c1139c811e6c59115ba. Upstream version: 0.15.15. License: MIT, Lauren Tan.

## Conversion design

Keep all 51 core skill directories, 23 playbooks, reference prompts, engineering principles and portable helper scripts. Verify the actual inventory during packaging. Make poteto-mode the explicit primary entry point. Preserve upstream attribution without implying this fork is maintained by the original author.

Replace Cursor task arguments with host-native delegation and capability checks. Use the parent model by default. Only use model overrides explicitly supported and authorized by the host. Independent runs on one model are independent runs, not model diversity. Provide sequential execution when delegation is unavailable.

Replace setup-pstack with project-local explicit configuration loaded by poteto-mode. Do not claim Markdown config is automatically loaded by Codex. Replace Cursor rules, skill paths and transcript assumptions. Use session context or explicitly scoped history tools when transcripts are unavailable.

Remove dependencies on cursor-team-kit by bundling minimal cleanup and verification guidance. Keep browser interaction subject to host authorization. Replace Cursor Custom Modes and slash-loop instructions with explicit skill invocation and session-bounded iteration. Recurring background work requires an available scheduling capability and explicit scheduling intent.

Rewrite make-bot-ui as capability-gated webhook UI design. Do not invent webhook provisioning, credential cards or endpoints. Keep Benny automation resources as reference-only examples, outside the discoverable skills tree, with no active scheduler or webhook registered.

Replace Cursor cloud orchestration assumptions with isolated local worktrees and native agent tools. Keep merge and deployment actions within the user's authorization and the host's policies. Never treat skill instructions as permission to send messages, reset a dirty checkout or bypass enforced approval.

## Verification planned

Validate every skill's YAML metadata and local Markdown links. Scan for residual unsupported task arguments and model slugs. Exercise portable helpers and existing helper tests where the runtime is available. Forward-test a read-only explanation and a bug-fix playbook in isolated fixtures. Record blocked integration checks honestly. Account creation validates the package but does not prove every external integration or local desktop installation.
