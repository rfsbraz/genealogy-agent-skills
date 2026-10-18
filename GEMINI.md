# Genealogy skills

This extension adds genealogy research skills. They load on demand when a task matches them.

- Start any family-history task with the `genealogy-mode` skill. It plans the case and routes to the other skills.
- Only `genealogy-mode`, `genealogy-interview` and `genealogy-narrative` should load on their own. The other skills are meant to be called by the user or by `genealogy-mode`. Gemini CLI cannot enforce this, so do not activate a specialist skill unless the user names it or `genealogy-mode` routes to it.
- Cite every claim and keep uncertainty visible. Do not merge people on a shared name alone.
- Emails and requests to archives are drafts. Only send them when the user explicitly authorises sending.
- Keep case files, transcriptions and the processing ledger local and out of public repositories.
