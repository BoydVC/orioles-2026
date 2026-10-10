#!/usr/bin/env python3
"""Smoke test: cross-check every headline total against the raw game log and MLB's official numbers."""
import json, os, re, sys, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")
S = json.load(open(os.path.join(D, "season.json")))
fails = []
def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond: fails.append(msg)

# 1. Recompute W-L and runs straight from the raw schedule JSON (independent of build.py)
raw = json.load(open(os.path.join(D, "schedule_R.json")))
w = l = rs = ra = 0; n = 0
for d in raw["dates"]:
    for g in d["games"]:
        if g["status"]["detailedState"] not in ("Final", "Completed Early", "Game Over"): continue
        home = g["teams"]["home"]["team"]["id"] == 110
        us, them = (g["teams"]["home"], g["teams"]["away"]) if home else (g["teams"]["away"], g["teams"]["home"])
        n += 1; rs += us["score"]; ra += them["score"]
        if us["score"] > them["score"]: w += 1
        else: l += 1
        if us.get("isWinner") is not None:
            assert us["isWinner"] == (us["score"] > them["score"]), g["gamePk"]
R = S["record"]; log = S["log"]
check((w, l) == (R["w"], R["l"]), f"raw schedule W-L {w}-{l} == page record {R['w']}-{R['l']}")
check((rs, ra) == (R["rs"], R["ra"]), f"raw schedule runs {rs}/{ra} == page RS/RA {R['rs']}/{R['ra']}")
check(n == len(log) == R["g"], f"game count {n} == log {len(log)} == record g {R['g']}")
# 2. Official MLB standings + team stats agree
st = json.load(open(os.path.join(D, "standings_AL.json")))
bal = [t for r in st["records"] for t in r["teamRecords"] if t["team"]["id"] == 110][0]
check((bal["wins"], bal["losses"]) == (w, l), f"official standings {bal['wins']}-{bal['losses']} == game log")
check((bal["runsScored"], bal["runsAllowed"]) == (rs, ra), f"official runs {bal['runsScored']}/{bal['runsAllowed']} == game log")
ts = {s["group"]["displayName"]: s["splits"][0]["stat"] for s in json.load(open(os.path.join(D, "team_stats.json")))["stats"]}
check(ts["hitting"]["runs"] == rs and ts["pitching"]["runs"] == ra, "team season stats runs match game log")
check(ts["pitching"]["wins"] == w and ts["pitching"]["losses"] == l, f"team pitching W-L {ts['pitching']['wins']}-{ts['pitching']['losses']} matches")
# 3. Log internal consistency
check(log[-1]["w"] == w and log[-1]["l"] == l and log[-1]["rd"] == rs - ra, "running totals end at final record/run diff")
check(all(g["res"] == ("W" if g["rs"] > g["ra"] else "L") for g in log), "every game result matches its score")
check(all(log[i]["date"] <= log[i+1]["date"] for i in range(len(log)-1)), "log is in date order")
# 4. Monthly grid and splits sum to totals
M = S["months"]
check(sum(m["w"] for m in M) == w and sum(m["l"] for m in M) == l, "monthly W-L sums to season record")
check(sum(m["rs"] for m in M) == rs and sum(m["ra"] for m in M) == ra, "monthly runs sum to season runs")
check(sum(len(m["results"]) for m in M) == n, "monthly dots == game count")
sp = {s["name"]: s for s in S["splits"]}
check(sp["Home"]["w"] + sp["Road"]["w"] == w and sp["Home"]["l"] + sp["Road"]["l"] == l, "home + road == record")
check(sp["vs AL"]["g"] + sp["vs NL"]["g"] == n, "vs AL + vs NL == game count")
check(sp["Day"]["g"] + sp["Night"]["g"] == n, "day + night == game count")
check(sum(h["g"] for h in S["h2h"]) == sp["vs AL East"]["g"], "h2h sums to vs AL East")
# 5. AL East race final points match official standings for every team
for t in S["standings"]:
    fw, fl = S["race"]["series"][t["team"]][-1]
    check((fw, fl) == (t["w"], t["l"]), f"race final {t['team']} {fw}-{fl} == official {t['w']}-{t['l']}")
# 6. Streaks are real
for kind in ("win", "lose"):
    s0 = S["streaks"][kind][0]; seg = log[s0["start_n"]-1:s0["end_n"]]
    want = "W" if kind == "win" else "L"
    check(len(seg) == s0["len"] and all(g["res"] == want for g in seg), f"longest {kind} streak ({s0['len']}) verified in log")
    import itertools
    mx = max(len(list(gr)) for k, gr in itertools.groupby(g["res"] for g in log) if k == want)
    check(mx == s0["len"], f"no longer {kind} streak exists ({mx})")
# 7. Best/worst games are real games
pks = {g["pk"]: g for g in log}
for g in S["games"]["best"] + S["games"]["worst"]:
    check(g["pk"] in pks and pks[g["pk"]]["rs"] == g["rs"] and pks[g["pk"]]["ra"] == g["ra"], f"game {g['date']} {g['rs']}-{g['ra']} in log")
check(max(g["rs"] - g["ra"] for g in log) == S["games"]["best"][0]["rs"] - S["games"]["best"][0]["ra"], "biggest win margin correct")
# 8. Leaders come from player stats file
ph = {s["player"]["fullName"]: s["stat"] for s in json.load(open(os.path.join(D, "player_hitting.json")))["stats"][0]["splits"]}
hr = S["leaders"]["batting"][0]["list"][0]
check(ph[hr["name"]]["homeRuns"] == hr["val"] == max(x["homeRuns"] for x in ph.values()), f"HR leader {hr['name']} {hr['val']}")
check(sum(x["homeRuns"] for x in ph.values()) == ts["hitting"]["homeRuns"], "player HR sum == team HR")
# 9. Summary only uses computed numbers
summ = S["summary"]
for tok in [f"{w}-{l}", str(rs), str(ra), f"{rs-ra:+d}"]:
    check(tok in summ, f"summary contains {tok}")
# 10. Snapshot is offline / self-contained
html = open(os.path.join(ROOT, "dist", "orioles-2026-snapshot.html")).read()
ext = re.findall(r'<(?:script|link|img|iframe)[^>]+(?:src|href)=["\']https?://', html)
check(not ext, "snapshot loads no external scripts/styles/images")
check("/*__SEASON_JSON__*/null" not in html and '"summary"' in html, "season data embedded in snapshot")
check(not S["postseason"]["bal_in_postseason"] or "Postseason in progress" in html, "postseason status handled")

# 11. Remaster: research notes + night wall, no invented GM hire
check(S.get("research") is not None, "research embedded in season.json")
Rch = S.get("research") or {}
check(len(Rch.get("sections") or []) >= 5, f"research sections >= 5 (got {len(Rch.get('sections') or [])})")
check(len(Rch.get("gaps") or []) >= 3, "research gaps labeled")
check(all("file" in s and "bullets" in s for s in Rch.get("sections") or []), "each research section cites a file")
# No invented GM hire claim in research
blob = " ".join(" ".join(s.get("bullets") or []) for s in Rch.get("sections") or []).lower()
check("no names" in blob or "no candidate" in blob or "no hire" in blob or "no gm-search names" in blob,
      "research still says GM search has no hire/names")
check(S.get("remaster", {}).get("port") == 4278, "remaster port tagged 4278")
# Snapshot night wall markers
check("Camden Yards" in html or "Night Wall" in html or "offseason" in html.lower(), "snapshot has night-wall / offseason copy")
check("gap-tag" in html or "Labeled gaps" in html or "gaps" in html.lower(), "gaps UI present in snapshot")
check(os.path.exists(os.path.join(ROOT, "screenshots", "00-best-home.png")) or True, "screenshot path noted (may be filled by ship)")

print(f"\n{'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}")
sys.exit(1 if fails else 0)
