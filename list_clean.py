#!/usr/bin/env python3
"""
ListClean Local — email list cleaning that never uploads your list.

Pipeline (all local, standard library only):
  1. Parse a CSV (auto-detects the email column) or a one-per-line TXT.
  2. Clean what has exactly one correct form: stray whitespace, upper-case
     domains / addresses (normalized to lower case), empty rows.
  3. Split out what should not be mailed blindly:
       - invalid syntax (with the reason)          -> rejects file
       - exact duplicates (case-insensitive)       -> removed, counted
       - known disposable / throwaway domains      -> flagged file
       - role accounts (info@, support@, ...)      -> flagged in report
  4. Report-only intelligence, never auto-applied:
       - likely domain typos (gmial.com -> gmail.com?) — "fixing" an
         address would fabricate a different recipient
       - probable duplicates via +tags / Gmail dots
  5. Re-validate the cleaned file: every row must pass syntax and be
     unique, or the verdict says so.

Honest scope: syntax + list hygiene only. Whether a mailbox actually
exists can only be known by sending or by a live SMTP probe, which a
local offline tool does not fake.
"""
import csv
import io
import os
import re
import sys

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
DISPOSABLE = {
    "mailinator.com", "guerrillamail.com", "guerrillamail.info", "10minutemail.com",
    "tempmail.com", "temp-mail.org", "yopmail.com", "throwawaymail.com",
    "getnada.com", "dispostable.com", "fakeinbox.com", "maildrop.cc",
    "trashmail.com", "sharklasers.com", "guerrillamailblock.com", "mintemail.com",
    "mohmal.com", "emailondeck.com", "tempail.com", "burnermail.io",
}
ROLE_LOCAL = {"info", "support", "admin", "postmaster", "noreply", "no-reply",
              "sales", "contact", "hello", "office", "billing", "help",
              "webmaster", "abuse", "marketing", "team"}
TYPO_DOMAINS = {
    "gmial.com": "gmail.com", "gmal.com": "gmail.com", "gmail.con": "gmail.com",
    "gmail.cm": "gmail.com", "gmaill.com": "gmail.com", "hotmial.com": "hotmail.com",
    "hotmal.com": "hotmail.com", "outlok.com": "outlook.com", "outllook.com": "outlook.com",
    "yahooo.com": "yahoo.com", "yaho.com": "yahoo.com", "iclod.com": "icloud.com",
    "protonmal.com": "protonmail.com", "gmx.con": "gmx.com",
}


def syntax_error(addr):
    if not addr:
        return "empty"
    if addr.count("@") != 1:
        return "must contain exactly one @"
    local, domain = addr.split("@")
    if not local:
        return "empty local part"
    if local.startswith(".") or local.endswith(".") or ".." in local:
        return "local part has leading/trailing/consecutive dots"
    if not domain or "." not in domain:
        return "domain has no dot/TLD"
    if domain.startswith(".") or domain.endswith(".") or ".." in domain:
        return "domain has leading/trailing/consecutive dots"
    if " " in addr:
        return "contains spaces"
    if not EMAIL_RE.match(addr):
        return "does not match basic address syntax"
    return None


def find_email_col(fields, rows):
    for f in fields:
        if f and f.strip().lower() in ("email", "e-mail", "email address", "e-mail address",
                                       "mail", "address", "subscriber email"):
            return f
    best, best_hits = None, 0
    for f in fields:
        hits = sum(1 for r in rows[:50] if "@" in (r.get(f) or ""))
        if hits > best_hits:
            best, best_hits = f, hits
    return best


def load_addresses(path):
    """Returns (addresses_with_extras, email_col, all_fields or None)."""
    if path.lower().endswith(".txt"):
        out = []
        for line in open(path, encoding="utf-8", errors="replace"):
            out.append({"__email__": line.strip()})
        return out, "__email__", None
    raw = open(path, "rb").read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    rows = [dict(r) for r in reader]
    col = find_email_col(reader.fieldnames or [], rows)
    if not col:
        raise ValueError("could not find an email column in the CSV")
    return rows, col, reader.fieldnames


def gmail_key(addr):
    local, domain = addr.split("@")
    if domain in ("gmail.com", "googlemail.com"):
        return local.split("+")[0].replace(".", "") + "@gmail.com"
    return local.split("+")[0] + "@" + domain


def run_listclean(src_path, outdir):
    os.makedirs(outdir, exist_ok=True)
    rows, col, fields = load_addresses(src_path)
    cleaned, rejects, flagged = [], [], []
    seen, seen_gmail = {}, {}
    stats = {"normalized": 0, "duplicates": 0, "empty": 0}
    typo_notes, role_notes, probable_dupes = [], [], []

    for r in rows:
        raw = (r.get(col) or "")
        addr = raw.strip().lower()
        if addr != raw:
            stats["normalized"] += 1
        if not addr:
            stats["empty"] += 1
            continue
        err = syntax_error(addr)
        if err:
            rejects.append((raw.strip(), err))
            continue
        if addr in seen:
            stats["duplicates"] += 1
            continue
        seen[addr] = True
        local, domain = addr.split("@")
        if domain in DISPOSABLE:
            flagged.append((addr, "disposable / throwaway domain — signups from these rarely convert and hurt sender reputation"))
            continue
        if local in ROLE_LOCAL:
            role_notes.append(addr)
        if domain in TYPO_DOMAINS:
            typo_notes.append(f"{addr} — did you mean {local}@{TYPO_DOMAINS[domain]}? (left unchanged; only the list owner can confirm)")
        gk = gmail_key(addr)
        if gk in seen_gmail and seen_gmail[gk] != addr:
            probable_dupes.append(f"{addr} looks like the same mailbox as {seen_gmail[gk]} (+tag / dot variant)")
        seen_gmail.setdefault(gk, addr)
        nr = dict(r)
        nr[col] = addr
        cleaned.append(nr)

    base = os.path.splitext(os.path.basename(src_path))[0]
    clean_path = os.path.join(outdir, base + "_cleaned.csv")
    out_fields = fields if fields else [col]
    with open(clean_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=out_fields)
        w.writeheader()
        for r in cleaned:
            w.writerow({k: r.get(k, "") for k in out_fields})
    reject_path = os.path.join(outdir, base + "_rejects.csv")
    with open(reject_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["address", "reason"])
        w.writerows(rejects)
        w.writerows([(a, r) for a, r in flagged])

    # re-check the cleaned file
    bad = [r[col] for r in cleaned if syntax_error(r[col])]
    dupes_left = len(cleaned) - len({r[col] for r in cleaned})
    verdict = "PASS" if not bad and dupes_left == 0 else "NOT READY"

    lines = ["# ListClean Local — cleaning & re-check report", "",
             f"Source file: {os.path.basename(src_path)}  ·  Rows read: {len(rows)}", "",
             "## Summary",
             f"- Clean, mail-ready addresses: {len(cleaned)}",
             f"- Normalized (trimmed / lower-cased): {stats['normalized']}",
             f"- Duplicates removed: {stats['duplicates']}",
             f"- Empty rows dropped: {stats['empty']}",
             f"- Rejected as invalid: {len(rejects)} (see the rejects file, with reasons)",
             f"- Flagged as disposable-domain: {len(flagged)} (split out, see rejects file)",
             f"- Role accounts kept but worth knowing about: {len(role_notes)}", "",
             "## Role accounts (kept in the clean file)"]
    lines += [f"- {a}" for a in role_notes] or ["- none"]
    lines += ["", "## Likely domain typos (NOT auto-corrected)"]
    lines += [f"- {n}" for n in typo_notes] or ["- none spotted"]
    lines += ["", "## Probable duplicates kept (same mailbox via +tag / Gmail dots)"]
    lines += [f"- {n}" for n in probable_dupes] or ["- none spotted"]
    lines += ["", "## Re-check verdict",
              f"- {verdict}: the cleaned file was re-validated — {len(bad)} syntax failures, "
              f"{dupes_left} duplicates remaining. Scope note: this is syntax and list hygiene. "
              "Whether a mailbox exists cannot be verified offline, and this tool does not claim otherwise."]
    report_path = os.path.join(outdir, "clean_report.md")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return {"total": len(rows), "cleaned": len(cleaned), "rejects": len(rejects),
            "flagged": len(flagged), "duplicates": stats["duplicates"],
            "verdict": verdict, "clean_path": clean_path,
            "reject_path": reject_path, "report_path": report_path}


def main(argv):
    if len(argv) != 3:
        print("usage: list_clean.py <list.csv|list.txt> <outdir>")
        return 2
    s = run_listclean(argv[1], argv[2])
    print(f"total={s['total']} cleaned={s['cleaned']} rejects={s['rejects']} "
          f"flagged={s['flagged']} duplicates={s['duplicates']} verdict={s['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
