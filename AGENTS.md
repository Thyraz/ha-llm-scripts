## Agent skills

- In all conversations and comit messages, be extremely concise and sacrifice grammar for the sake of concision.

### Issue tracker

Issues live in GitHub Issues for `Thyraz/ha-llm-scripts`; use `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

Use default labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context repo: root `CONTEXT.md` and `docs/adr/`. See `docs/agents/domain.md`.

### Coding guidelines

Keep code easy to read. Do not guard against unlikely errors just to be defensive. In YAML script files, use comments because comments are preserved outside GUI mode. See `docs/coding_guidelines.md`.
Ensure to read the provided docs carefully. A lot common errors that LLMs make when writing HA scripts (and how to avoid them) can be found here.

## Github

- Your primary interaction with GitHub should be the git CLI.

## Plans

At the end of each plan, give me a list of unresolved questions to answer, if any.
Make the questions extremely concise. Sacrifice grammar for the sake of concision.
