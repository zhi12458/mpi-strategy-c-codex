# Audited network terminology verification

Use this gate when an internal terminology search returns no usable result,
credible internal or external sources conflict, or the correct sense or English
wording remains in substantive doubt.

## Required lookup scope

Network verification applies to Buddhist terms, titles and headings, personal
and place names, scripture and book titles, quotations, idioms, proverbs,
classical expressions, historical references, culturally fixed expressions,
and wordplay. It also applies when a familiar term may carry a different sense
in the current passage.

## Source priority

Use the most direct authoritative evidence available:

1. Official MPI or project publications and named approved translations.
2. Primary canonical text, official institutional publication, author or
   publisher record, or official name/title registry.
3. Established Buddhist translation databases and specialist dictionaries.
4. Reputable academic publishers, peer-reviewed research, and recognized
   scholarly reference works.

Search-result snippets, unattributed glossaries, SEO pages, machine-generated
summaries, forums, and social posts may help discovery but cannot be the sole
evidence for a frozen T1 decision.

## Privacy boundary

- Search the smallest public expression that can answer the question: normally
  the term, title, name, quotation fragment, or idiom plus minimal bibliographic
  context.
- Do not submit the full private paragraph or manuscript to a search provider.
- If a unique or private passage must be transmitted to resolve the question,
  obtain explicit consent first and record that authorization.

## Receipt contract

Append one record per decision to `external-lookup-receipts.jsonl`. Each record
must include:

- `schema_version`, `term_id`, source line or paragraph ID, Chinese expression,
  and lookup reason;
- internal term-search result or explicit `no_result`;
- every material web query;
- for each accepted source: direct URL, title, publisher or institution,
  access time, supported claim, and content hash or archived evidence hash;
- candidate translations, context-specific sense analysis, selected wording,
  rationale, and status;
- the reviewing model or named human decision-maker.

Use `selected` only when evidence and Chinese context support one wording. Use
`human_choice` when credible evidence permits multiple materially different
renderings. Use `blocked` when a core title, doctrinal distinction, scripture
quotation, proper name, or fixed expression cannot be resolved safely.

## Decision rule

- Web evidence informs the decision but does not override the frozen Chinese
  context or higher-priority approved project terminology without an explicit
  recorded exception.
- Never average conflicting sources or choose the most common web wording
  without checking sense and authority.
- A provisional non-core wording may remain only in an `AI reviewed draft`,
  clearly listed for human review. An unresolved core item blocks T1 completion
  and release.
- Missing or stale required lookup receipts block term freeze, translation, and
  finalization for the affected item.
