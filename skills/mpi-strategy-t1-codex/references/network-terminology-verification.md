# Audited network terminology verification

Use this gate when the internal termbase returns no usable result, credible
sources conflict, or the correct sense or English wording remains substantively
uncertain. It applies to Buddhist terms, titles, names, scripture and book
titles, quotations, idioms, proverbs, classical or culturally fixed
expressions, historical references, and wordplay.

## Evidence priority

1. Official MPI or named approved project translations.
2. Primary canonical text, official institutional publication, author or
   publisher record, and official name/title registry.
3. Established Buddhist translation databases and specialist dictionaries.
4. Reputable academic publishers, peer-reviewed work, and recognized scholarly
   references.

Search snippets, unattributed glossaries, SEO pages, machine summaries, forums,
and social posts may aid discovery but cannot be the sole frozen evidence.

## Privacy and receipts

- Query the smallest public expression that resolves the issue. Do not submit a
  private paragraph or manuscript without explicit consent.
- Append one decision record to `external-lookup-receipts.jsonl`, including the
  expression and source ID, lookup reason, internal result, material web
  queries, direct authoritative sources and access times, supported claims,
  evidence hashes, candidate renderings, selected wording, rationale, status,
  and the model or named human decision-maker.
- Use `selected` only when evidence and context support one wording. Use
  `human_choice` for materially different supported options and `blocked` when
  a core item cannot be resolved safely.
- Web evidence does not override frozen Chinese context or higher-priority
  approved terminology without a recorded exception. Missing required evidence
  blocks the affected term freeze and T1-Codex completion.
