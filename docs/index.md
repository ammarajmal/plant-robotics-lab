# PRL Documentation Index

- [[planning/roadmap]] — milestones and learning path
- [[planning/task_board]] — immediate tasks
- [[planning/risk_register]] — known open risks
- [[architecture/system_overview]] — component boundaries
- [[architecture/glossary]] — consistent terminology
- [[adr/0001-independent-repository]] — project independence
- [[development/git_workflow]] — development practices
- [[development/git_guide]] — Git concepts, remote setup, recovery and practice exercises
- [[development/migration_and_provenance]] — source reuse protocol
- [[development/data_sources]] — read-only data-source manifests (PRL-004)
- [[development/model_assets]] — storage conventions and checkpoint manifest
- [[development/independent_review]] — checklist for independent review (PRL-006)
- [[experiments/index]] — recorded runs and digests
- [[development/playback]] — playback architecture and test strategy
- [[development/agent_handoff]] — first agent task

Markdown links are provided for ordinary readers in the files themselves; Logseq users may link page aliases manually.

## Documentation ownership

One canonical home per kind of information; link to it rather than copying.

| Information | Canonical file |
|---|---|
| Agent rules, safety, evidence policy | `AGENTS.md` (`CLAUDE.md` only imports it) |
| Commands, quality gate, environments, recovery | `docs/development/environment.md` |
| Git practice and learning | `docs/development/git_workflow.md`, `git_guide.md` |
| Dataset and model sources, manifests | `docs/development/data_sources.md` |
| Milestones | `docs/planning/roadmap.md` |
| Task state (TODO/REVIEW/DONE) | `docs/planning/task_board.md` |
| Known risks | `docs/planning/risk_register.md` |
| Evidence for a finished task | `docs/reports/` (historical; never rewritten) |
| Components and safety invariant | `docs/architecture/` |
| Logseq pages in `knowledge/logseq/` | Personal notes; they must link here, not restate status |
