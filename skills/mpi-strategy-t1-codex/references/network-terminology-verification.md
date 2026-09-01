# Audited network terminology verification

Use this gate when the internal termbase returns no usable result, credible
sources conflict, or the correct sense or English wording remains substantively
uncertain. It applies to Buddhist terms, titles, names, scripture and book
titles, quotations, idioms, proverbs, classical or culturally fixed
expressions, historical references, and wordplay.

## Evidence priority

1. The project term record, official MPI decisions, and named approved wording
   for this exact project and context.
2. Approved translations by the same teacher, author, or institution.
3. Reliable canonical translations, primary canonical text, and recognized
   Buddhist translation institutions.
4. Established Buddhist translation databases and specialist dictionaries.
5. Reputable academic publishers, peer-reviewed work, professional Buddhist
   dictionaries, and official name/title registries.

When traditions use materially different English, compare them explicitly,
identify which meaning and audience each wording serves, and record why the
project context supports one or leaves a commissioner choice. Ordinary
dictionary preference or a single search result cannot freeze a Buddhist term.

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
- Keep article-specific human decisions in a project-local profile. Do not add
  them to the global termbase or reuse them in another document without a new
  source and context check.
