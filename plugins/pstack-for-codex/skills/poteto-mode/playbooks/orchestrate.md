### Orchestrate

Read CODEX-RUNTIME.md. Use this for an explicitly authorized program with multiple work units.

1. Define the goal, checkable done predicate, scope and external actions authorized by the user. Confirm available delegation and authenticated forge tools from the actual host. No cloud environment or persistent coordinator is provisioned.
2. Persist a project-local coordination record containing unit IDs, dependencies, owner, branch/worktree, immutable head SHA, status, evidence and follow-ups. Use the bundled scripts/orch/orch.ts only after inspecting its help, runtime requirements and tests. Resolve it relative to this skill, not the target repository. The frontier uses the forge PR base chain and local branch heads; select --forge origin only when that forge is configured. The parent is the sole coordinator-record writer.
3. Assign one writer per isolated worktree or disjoint file scope. Give every unit a self-contained brief with goal, boundaries and verification. Workers never rebase, retarget or merge PRs. Spawn only through native tools and within exposed limits. When delegation is unavailable, perform units sequentially and record that fallback.
4. Track actual native agent IDs while the session runs. Aggregate results and inspect evidence before accepting a unit. Failures and missing results remain gaps. Retry with an adjusted scope or record a blocker. Never silently replace an independent verification gate with self-review.
5. Re-read live refs, checks and review state before any authorized push or merge. Verification is keyed by exact head SHA; new heads need relevant checks again. Assign one stacker per stack to serialize chain rebases, force-pushes, retargets and merges; preserve unrelated work. Use git and available forge tools; Graphite and Origin are optional only if configured and supported.
6. Checkpoint completed units, running work, uncommitted changes, current refs and next commands. Scheduling and restart recovery follow CODEX-RUNTIME.md. Never assume old agent IDs or processes survived.
7. Finish only when every required unit has verified evidence or an explicit blocker. Externalize outputs to the authorized durable destination as each unit completes.

Reply with the predicate, verified units, branches/PRs, exact evidence, gaps and checkpoint path.
