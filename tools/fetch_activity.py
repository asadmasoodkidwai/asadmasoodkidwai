#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_activity.py -- reads a GitHub account's activity and writes data/activity.json.

    GH_TOKEN=<token> GH_LOGIN=<username> python tools/fetch_activity.py

Standard library only. For public data the token needs no scopes (the workflow's built-in
GITHUB_TOKEN works). A classic personal access token with the `read:user` scope also counts
private contributions, the same way your profile page does.

What it records (same definitions the old stats cards used):
  stars            stars on repositories you own (forks excluded)
  commits_last_year, prs, issues, contributed_to
  languages        top 6 by bytes across your own non-fork repositories, as % of those 6
  streaks          from your contribution calendar, account creation -> today (UTC)
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com/graphql"
TOP_LANGS = 6

Q_REPOS = """
query($login: String!, $after: String) {
  user(login: $login) {
    createdAt
    pullRequests { totalCount }
    issues { totalCount }
    repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, after: $after) {
      pageInfo { hasNextPage endCursor }
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } }
      }
    }
  }
}
"""

Q_RANGE = """
query($login: String!, $from: DateTime, $to: DateTime) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      contributionCalendar { weeks { contributionDays { date contributionCount } } }
    }
  }
}
"""


def gql(query, variables, token):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(API, body, {"Authorization": "Bearer " + token,
                                             "Content-Type": "application/json",
                                             "User-Agent": "profile-activity-refresh"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise SystemExit("GitHub rejected the token (HTTP %d). Check the PROFILE_TOKEN secret." % e.code)
            if attempt == 3:
                raise
            time.sleep(2 * 2 ** attempt)
        except (urllib.error.URLError, TimeoutError):
            if attempt == 3:
                raise
            time.sleep(2 * 2 ** attempt)
    if data.get("errors"):
        raise SystemExit("GitHub returned errors: %s" % json.dumps(data["errors"])[:600])
    return data["data"]


def iso(d):
    return d.isoformat()


def chunks(start, today):
    """Calendar queries may span at most one year, so walk from account creation in <=365-day steps."""
    a = start
    while a <= today:
        b = min(a + dt.timedelta(days=364), today)
        yield a, b
        a = b + dt.timedelta(days=1)


def streaks(days, today):
    """days: {'YYYY-MM-DD': count}.  Returns (total, current, longest); streaks are dicts(days,start,end).
    A streak that ended yesterday still counts as current (today may simply not have happened yet)."""
    ordered = sorted(d for d in days if d <= iso(today))
    total = sum(days[d] for d in ordered)
    longest = {"days": 0, "start": None, "end": None}
    run, run_start, prev = 0, None, None
    for d in ordered:
        if days[d] <= 0:
            continue
        if prev and (dt.date.fromisoformat(d) - dt.date.fromisoformat(prev)).days == 1:
            run += 1
        else:
            run, run_start = 1, d
        prev = d
        if run >= longest["days"]:                      # ties go to the most recent run
            longest = {"days": run, "start": run_start, "end": d}
    current = {"days": 0, "start": None, "end": None}
    if prev and (today - dt.date.fromisoformat(prev)).days <= 1:
        current = {"days": run, "start": run_start, "end": prev}
    return total, current, longest


def collect(login, token, today=None, call=gql):
    today = today or dt.datetime.now(dt.timezone.utc).date()
    stars, sizes, after, created = 0, {}, None, None
    stats = {}
    while True:
        u = call(Q_REPOS, {"login": login, "after": after}, token)["user"]
        if u is None:
            raise SystemExit("GitHub user %r not found" % login)
        if created is None:
            created = dt.date.fromisoformat(u["createdAt"][:10])
            stats = dict(prs=u["pullRequests"]["totalCount"], issues=u["issues"]["totalCount"],
                         contributed_to=u["repositoriesContributedTo"]["totalCount"])
        repos = u["repositories"]
        for r in repos["nodes"]:
            stars += r["stargazerCount"]
            for e in r["languages"]["edges"]:
                sizes[e["node"]["name"]] = sizes.get(e["node"]["name"], 0) + e["size"]
        if not repos["pageInfo"]["hasNextPage"]:
            break
        after = repos["pageInfo"]["endCursor"]

    days = {}
    for a, b in chunks(created, today):
        to = None if b == today else "%sT23:59:59Z" % iso(b)       # null = "now"
        cal = call(Q_RANGE, {"login": login, "from": "%sT00:00:00Z" % iso(a), "to": to}, token)
        cal = cal["user"]["contributionsCollection"]["contributionCalendar"]
        for w in cal["weeks"]:
            for d in w["contributionDays"]:
                if iso(created) <= d["date"] <= iso(today):
                    days[d["date"]] = d["contributionCount"]
    last = call(Q_RANGE, {"login": login, "from": "%sT00:00:00Z" % iso(max(created, today - dt.timedelta(days=364))),
                          "to": None}, token)["user"]["contributionsCollection"]["totalCommitContributions"]

    top = sorted(sizes.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_LANGS]
    tot = sum(s for _, s in top) or 1
    total, current, longest = streaks(days, today)
    return {"login": login, "since": iso(created), "stars": stars, "commits_last_year": last,
            "prs": stats["prs"], "issues": stats["issues"], "contributed_to": stats["contributed_to"],
            "languages": [[n, round(100.0 * s / tot, 2)] for n, s in top],
            "total_contributions": total, "current_streak": current, "longest_streak": longest}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", default=os.environ.get("GH_LOGIN") or os.environ.get("GITHUB_REPOSITORY_OWNER"))
    ap.add_argument("--out", default=os.path.join(here, "..", "data", "activity.json"))
    a = ap.parse_args()
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token or not a.login:
        sys.exit("Set GH_TOKEN and GH_LOGIN (or pass --login).")
    data = collect(a.login, token)
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    old = open(a.out, encoding="utf-8").read() if os.path.exists(a.out) else ""
    if text == old:
        print("activity unchanged")
        return
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, "w", encoding="utf-8").write(text)
    print("activity updated:", json.dumps({k: data[k] for k in ("stars", "commits_last_year", "total_contributions")}))


if __name__ == "__main__":
    main()
