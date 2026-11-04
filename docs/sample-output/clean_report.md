# ListClean Local — cleaning & re-check report

Source file: sample.csv  ·  Rows read: 20

## Summary
- Clean, mail-ready addresses: 10
- Normalized (trimmed / lower-cased): 2
- Duplicates removed: 2
- Empty rows dropped: 1
- Rejected as invalid: 5 (see the rejects file, with reasons)
- Flagged as disposable-domain: 2 (split out, see rejects file)
- Role accounts kept but worth knowing about: 2

## Role accounts (kept in the clean file)
- info@example.com
- support@example.org

## Likely domain typos (NOT auto-corrected)
- tom@gmial.com — did you mean tom@gmail.com? (left unchanged; only the list owner can confirm)
- sara@hotmial.com — did you mean sara@hotmail.com? (left unchanged; only the list owner can confirm)

## Probable duplicates kept (same mailbox via +tag / Gmail dots)
- alex@example.com looks like the same mailbox as alex+newsletter@example.com (+tag / dot variant)

## Re-check verdict
- PASS: the cleaned file was re-validated — 0 syntax failures, 0 duplicates remaining. Scope note: this is syntax and list hygiene. Whether a mailbox exists cannot be verified offline, and this tool does not claim otherwise.
