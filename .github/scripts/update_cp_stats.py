#!/usr/bin/env python3
"""Refresh competitive-programming badge values in README.md.

Design goal: "dynamic, with a hardcoded fallback."
- The badges are plain shields.io <img> images, so they ALWAYS render with
  whatever value is currently written in the README (the hardcoded fallback).
- This script runs on a schedule, fetches live stats, and rewrites ONLY the
  value segment of each badge URL.
- If an API call fails, the badge is left exactly as-is — a flaky upstream
  never yields a broken or empty badge.

Badge URL shape (shields.io):  .../badge/<LABEL>-<MESSAGE>-<COLOR>?...
We rewrite only <MESSAGE> for the CodeChef and LeetCode badges.
"""

import re
import sys
import json
import urllib.request

README = "README.md"
CODECHEF_USER = "darknight_1729"
LEETCODE_USER = "Dark_Knight_1729"


def _get(url, *, method="GET", data=None, headers=None, timeout=20):
    req = urllib.request.Request(
        url, method=method,
        data=json.dumps(data).encode() if data else None,
        headers=headers or {},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def fetch_codechef():
    """Return shields-encoded message e.g. '4★%20(1851)' or None on failure."""
    try:
        d = _get(f"https://competeapi.vercel.app/user/codechef/{CODECHEF_USER}")
        stars = str(d["rating"]).strip()      # '4★'
        cur = int(d["rating_number"])         # 1851
        # shields.io: space -> %20 ; literal '-' must be '--' (none here)
        return f"{stars}%20({cur})"
    except Exception as e:
        print(f"[codechef] fetch failed, keeping existing value: {e}", file=sys.stderr)
        return None


def fetch_leetcode():
    """Return shields-encoded message e.g. '395%20solved' or None on failure."""
    try:
        d = _get(
            "https://leetcode.com/graphql",
            method="POST",
            data={"query": 'query{matchedUser(username:"%s")'
                           '{submitStats{acSubmissionNum{difficulty count}}}}' % LEETCODE_USER},
            headers={
                "Content-Type": "application/json",
                "Referer": f"https://leetcode.com/u/{LEETCODE_USER}/",
                "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/124.0 Safari/537.36"),
                "Origin": "https://leetcode.com",
            },
        )
        nums = d["data"]["matchedUser"]["submitStats"]["acSubmissionNum"]
        total = next(x["count"] for x in nums if x["difficulty"] == "All")
        return f"{total}%20solved"
    except Exception as e:
        print(f"[leetcode] fetch failed, keeping existing value: {e}", file=sys.stderr)
        return None


def replace_badge(text, label, message):
    """Rewrite the message segment of a shields.io badge whose label == `label`.

    Matches:  /badge/<label>-<old message>-<color>?  and swaps <old message>.
    Returns (new_text, changed_bool). No-op if message is None or not found.
    """
    if message is None:
        return text, False
    # label and color contain no '-' (single dash); message may not either in our badges.
    pattern = re.compile(
        r"(img\.shields\.io/badge/%s-)[^-?]+(-[0-9A-Fa-f]{6}\?)" % re.escape(label)
    )
    if not pattern.search(text):
        print(f"[{label}] badge not found in README — skipping", file=sys.stderr)
        return text, False
    new = pattern.sub(lambda m: m.group(1) + message + m.group(2), text)
    return new, (new != text)


def main():
    with open(README, encoding="utf-8") as f:
        text = original = f.read()

    changed = False
    for label, msg in (("CodeChef", fetch_codechef()), ("LeetCode", fetch_leetcode())):
        text, did = replace_badge(text, label, msg)
        changed = changed or did

    if changed and text != original:
        with open(README, "w", encoding="utf-8") as f:
            f.write(text)
        print("README updated with fresh CP stats.")
    else:
        print("No changes (APIs unchanged or unreachable — fallback values kept).")


if __name__ == "__main__":
    main()
