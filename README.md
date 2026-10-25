# ListClean Local — Email List Cleaning That Never Uploads Your List

Upload-based list cleaners charge per address and take a copy of your
subscriber list. ListClean Local does the offline 90% on your own machine:
syntax validation, de-duplication, disposable-domain and role-account
flagging — then **re-validates the cleaned file** and shows its work.

## What it does
- Auto-detects the email column in a CSV (or reads a one-per-line TXT)
- Normalizes stray whitespace and case; drops empty rows
- Removes exact duplicates (case-insensitive), counted in the report
- Rejects invalid addresses **with the reason** (missing @, bad dots, no TLD…)
- Splits out known disposable/throwaway domains (built-in list)
- Flags role accounts (info@, support@, …) — kept, but you should know
- Spots likely domain typos (`gmial.com` → gmail.com?) as *suggestions only* —
  "correcting" an address would fabricate a different recipient
- Spots probable duplicates via +tags / Gmail dot variants — reported, never merged
- Re-check verdict: the cleaned file is re-validated (0 syntax failures, 0 duplicates)

## Honest scope
Whether a mailbox actually exists cannot be verified offline — only sending
(or a live probe) tells. ListClean never claims a "deliverability score"
it cannot measure.

## Verified behaviour
On a seeded 12-row list: 7 clean addresses out, 1 duplicate removed,
2 invalid rejected with reasons, 1 disposable-domain address split out,
1 role account and 1 domain-typo suggestion reported, re-check PASS.

## Run from source
```
python list_clean.py subscribers.csv output_folder
```
Writes `<name>_cleaned.csv`, `<name>_rejects.csv` and `clean_report.md`.
Standard library only. The Windows app wraps the same engine.
