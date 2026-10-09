# pstack for Codex

An independent Codex adaptation of [Lauren Tan’s pstack](https://github.com/cursor/plugins/tree/main/pstack), licensed under MIT. The original copyright is preserved in LICENSE. This fork is not an official Cursor or OpenAI distribution.

Select poteto-mode from the installed plugin’s skill picker or ask to use `pstack-for-codex:poteto-mode` with your goal and a checkable done condition. Use `$poteto-mode` where the host supports that skill invocation. No model setup is needed. Optional setup-pstack writes project preferences that poteto-mode reads explicitly.

The plugin preserves the core skills, principles, reference prompts, 23 playbooks and portable helpers. [CODEX-RUNTIME.md](CODEX-RUNTIME.md) defines native tools, delegation, model inheritance, paths, authorization and sequential fallbacks. [COMPATIBILITY.md](COMPATIBILITY.md) records conversion and verification limits.

Subagents require exposed and permitted host capabilities. Repeated inherited-model runs are not cross-model review. Browser, forge, secret and scheduling tools are not supplied. Session loops do not run in the background after the session ends. Benny resources are historical reference data only.

Helper scripts require their documented runtimes. Resolve them from the installed plugin location. Creating this private plugin does not install it on another device or prove every external workflow. Install/connect it through the host UI and invoke the skill in a fresh task.
