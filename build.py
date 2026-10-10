#!/usr/bin/env python3
"""Build the Orioles 2026 Camden Yards night wall from raw MLB Stats API JSON in data/.
Every standings/stat number is computed here from those files. Offseason notes come from
data/research_notes.json (ij_* only). Nothing baseball-factual is typed in by hand."""
import json, os, datetime as dt
from collections import defaultdict, OrderedDict

ROOT = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(ROOT, "data")
BAL = 110
ALEAST = [110, 147, 111, 141, 139]
FINAL_STATES = {"Final", "Completed Early", "Game Over"}

def load(name):
    with open(os.path.join(D, name)) as f:
        return json.load(f)

teams = {t["id"]: t for t in load("teams.json")["teams"]}
def abbr(tid): return teams.get(tid, {}).get("abbreviation", str(tid))
def tname(tid): return teams.get(tid, {}).get("teamName", teams.get(tid, {}).get("name", str(tid)))

def played_games(sched, tid):
    out = []
    for date in sched["dates"]:
        for g in date["games"]:
            if g["status"]["detailedState"] not in FINAL_STATES:
                continue
            home = g["teams"]["home"]["team"]["id"] == tid
            us = g["teams"]["home" if home else "away"]
            them = g["teams"]["away" if home else "home"]
            if us.get("score") is None or them.get("score") is None:
                continue
            out.append((g, home, us, them))
    out.sort(key=lambda x: (x[0]["gameDate"], x[0].get("gameNumber", 1)))
    return out

# ---------- Orioles game log ----------
sched = load("schedule_R.json")
all_sched = [g for d in sched["dates"] for g in d["games"]]
log = []
w = l = rs_tot = ra_tot = 0
for g, home, us, them in played_games(sched, BAL):
    rs, ra = us["score"], them["score"]
    win = rs > ra
    w += win; l += (not win)
    rs_tot += rs; ra_tot += ra
    ls = g.get("linescore", {})
    inns = ls.get("innings", [])
    n_inn = len(inns)
    walkoff = False
    if home and win and inns:
        last = inns[-1].get("home", {})
        walkoff = last.get("runs") is not None and g["status"]["detailedState"] != "Completed Early"
    log.append({
        "n": len(log) + 1,
        "pk": g["gamePk"],
        "date": g["officialDate"],
        "dh": g.get("doubleHeader", "N") != "N",
        "gnum": g.get("gameNumber", 1),
        "home": home,
        "opp": abbr(them["team"]["id"]),
        "opp_id": them["team"]["id"],
        "opp_name": them["team"]["name"],
        "venue": g["venue"]["name"],
        "rs": rs, "ra": ra, "res": "W" if win else "L",
        "w": w, "l": l, "rd": rs_tot - ra_tot,
        "innings": n_inn,
        "sched_innings": g.get("scheduledInnings", 9),
        "short": g["status"]["detailedState"] == "Completed Early",
        "walkoff": walkoff,
        "day_night": g.get("dayNight"),
    })

not_played = [{"date": g["officialDate"], "home": g["teams"]["home"]["team"]["id"] == BAL, "state": g["status"]["detailedState"],
               "reason": g["status"].get("reason"), "pk": g["gamePk"],
               "opp": abbr((g["teams"]["away"] if g["teams"]["home"]["team"]["id"] == BAL else g["teams"]["home"])["team"]["id"])}
              for g in all_sched if g["status"]["detailedState"] not in FINAL_STATES]

def rec(games):
    ww = sum(1 for g in games if g["res"] == "W")
    return {"w": ww, "l": len(games) - ww, "rs": sum(g["rs"] for g in games),
            "ra": sum(g["ra"] for g in games), "g": len(games)}

# ---------- monthly grid ----------
months = OrderedDict()
for g in log:
    m = g["date"][:7]
    key = "2026-04" if m == "2026-03" else m   # Baseball-Reference convention: March folded into April
    months.setdefault(key, []).append(g)
month_rows = []
for k, gs in months.items():
    r = rec(gs)
    label = dt.date(2026, int(k[5:]), 1).strftime("%B")
    if k == "2026-04" and any(g["date"].startswith("2026-03") for g in gs):
        label = "March/April"
    r.update({"key": k, "label": label,
              "results": [g["res"] for g in gs]})
    month_rows.append(r)

# ---------- splits ----------
splits = OrderedDict()
splits["Home"] = rec([g for g in log if g["home"]])
splits["Road"] = rec([g for g in log if not g["home"]])
splits["One-run games"] = rec([g for g in log if abs(g["rs"] - g["ra"]) == 1])
splits["Blowouts (5+ runs)"] = rec([g for g in log if abs(g["rs"] - g["ra"]) >= 5])
splits["Extra innings"] = rec([g for g in log if g["innings"] > g["sched_innings"]])
splits["vs AL East"] = rec([g for g in log if g["opp_id"] in ALEAST])
lg_of = {tid: t.get("league", {}).get("id") for tid, t in teams.items()}
splits["vs AL"] = rec([g for g in log if lg_of.get(g["opp_id"]) == 103])
splits["vs NL"] = rec([g for g in log if lg_of.get(g["opp_id"]) == 104])
splits["Day"] = rec([g for g in log if g["day_night"] == "day"])
splits["Night"] = rec([g for g in log if g["day_night"] == "night"])
splits["Doubleheader games"] = rec([g for g in log if g["dh"]])
h2h = []
for tid in ALEAST[1:]:
    r = rec([g for g in log if g["opp_id"] == tid]); r["team"] = abbr(tid); r["name"] = tname(tid)
    h2h.append(r)

# ---------- streaks ----------
def streaks(kind):
    best, cur, start = (0, None, None), 0, None
    allst = []
    for i, g in enumerate(log):
        if g["res"] == kind:
            if cur == 0: start = i
            cur += 1
            if cur > best[0]: best = (cur, start, i)
        else:
            if cur: allst.append((cur, start, i - 1))
            cur = 0
    if cur: allst.append((cur, start, len(log) - 1))
    allst.sort(key=lambda s: (-s[0], s[1]))
    return [{"len": n, "from": log[a]["date"], "to": log[b]["date"], "start_n": a + 1, "end_n": b + 1,
             "rs": sum(x["rs"] for x in log[a:b+1]), "ra": sum(x["ra"] for x in log[a:b+1])} for n, a, b in allst[:3]]
win_streaks, lose_streaks = streaks("W"), streaks("L")
# best / worst 10-game and 20-game stretches
def stretch(n, best=True):
    vals = []
    for i in range(len(log) - n + 1):
        ww = sum(1 for g in log[i:i+n] if g["res"] == "W")
        vals.append((ww, i))
    ww, i = (max if best else min)(vals, key=lambda v: (v[0], -v[1]) if best else (v[0], v[1]))
    return {"n": n, "w": ww, "l": n - ww, "from": log[i]["date"], "to": log[i+n-1]["date"], "start_n": i + 1}
stretches = {"best20": stretch(20, True), "worst20": stretch(20, False)}
# peak / low points vs .500
over = [g["w"] - g["l"] for g in log]
hi = max(range(len(log)), key=lambda i: (over[i], -i)); lo = min(range(len(log)), key=lambda i: (over[i], i))
last_at_500_or_better = max([i for i in range(len(log)) if over[i] >= 0], default=None)
peaks = {"high": {"over": over[hi], "date": log[hi]["date"], "rec": f'{log[hi]["w"]}-{log[hi]["l"]}', "n": hi + 1},
         "low": {"over": over[lo], "date": log[lo]["date"], "rec": f'{log[lo]["w"]}-{log[lo]["l"]}', "n": lo + 1},
         "last_500": None if last_at_500_or_better is None else
            {"date": log[last_at_500_or_better]["date"], "rec": f'{log[last_at_500_or_better]["w"]}-{log[last_at_500_or_better]["l"]}', "n": last_at_500_or_better + 1}}

# ---------- best / worst games ----------
def gsum(g): return {k: g[k] for k in ("n", "date", "opp", "home", "rs", "ra", "res", "innings", "walkoff", "pk", "venue")}
wins = [g for g in log if g["res"] == "W"]; losses = [g for g in log if g["res"] == "L"]
best_games = [gsum(g) for g in sorted(wins, key=lambda g: (-(g["rs"] - g["ra"]), -g["rs"], g["n"]))[:5]]
worst_games = [gsum(g) for g in sorted(losses, key=lambda g: (-(g["ra"] - g["rs"]), -g["ra"], g["n"]))[:5]]
mx_rs = max(g["rs"] for g in log)
most_runs = [gsum(g) for g in log if g["rs"] == mx_rs]
walkoffs = [gsum(g) for g in log if g["walkoff"]]
longest = max(log, key=lambda g: (g["innings"], -g["n"]))
shutouts_for = [gsum(g) for g in log if g["ra"] == 0]
shutouts_against = [gsum(g) for g in log if g["rs"] == 0]

# ---------- AL East race ----------
race = {}
all_dates = set()
for tid in ALEAST:
    s = sched if tid == BAL else load(f"schedule_R_{tid}.json")
    byd = defaultdict(lambda: [0, 0])
    for g, home, us, them in played_games(s, tid):
        byd[g["officialDate"]][0 if us["score"] > them["score"] else 1] += 1
        all_dates.add(g["officialDate"])
    race[tid] = byd
dates = sorted(all_dates)
race_series = {}
for tid in ALEAST:
    W = L = 0; pts = []
    for d_ in dates:
        a, b = race[tid].get(d_, (0, 0)); W += a; L += b
        pts.append([W, L])
    race_series[abbr(tid)] = pts
# games back each date
gb = {a: [] for a in race_series}
for i in range(len(dates)):
    lead = max(race_series.values(), key=lambda p: (p[i][0] - p[i][1]))[i]
    for a, p in race_series.items():
        gb[a].append(((lead[0] - p[i][0]) + (p[i][1] - lead[1])) / 2)
bal_days_first = sum(1 for x in gb["BAL"] if x == 0)
# days in first (shared counts) after at least one game
# ---------- standings (official) ----------
st = load("standings_AL.json")
al_east_official = []
for r in st["records"]:
    if r["division"]["id"] == 201:
        for t in r["teamRecords"]:
            al_east_official.append({"team": abbr(t["team"]["id"]), "name": t["team"]["name"], "w": t["wins"], "l": t["losses"],
                                     "pct": t["winningPercentage"], "gb": t["gamesBack"], "rs": t["runsScored"], "ra": t["runsAllowed"],
                                     "clinch": t.get("clinchIndicator"), "rank": int(t["divisionRank"]),
                                     "wc_rank": t.get("wildCardRank"), "wc_gb": t.get("wildCardGamesBack")})
al_east_official.sort(key=lambda t: t["rank"])
bal_official = next(t for t in al_east_official if t["team"] == "BAL")
# wild card: AL teams sorted
al_all = []
for r in st["records"]:
    for t in r["teamRecords"]:
        al_all.append({"team": abbr(t["team"]["id"]), "w": t["wins"], "l": t["losses"], "pct": t["winningPercentage"],
                       "clinch": t.get("clinchIndicator"), "wc_gb": t.get("wildCardGamesBack"), "wc_rank": t.get("wildCardRank"),
                       "div_rank": t.get("divisionRank")})
al_all.sort(key=lambda t: -float(t["pct"]))
bal_al_rank = [t["team"] for t in al_all].index("BAL") + 1
postseason_teams_al = [t["team"] for t in al_all if t["clinch"]]

# ---------- postseason status ----------
ps = load("postseason_all.json")
ps_games = [g for d in ps.get("dates", []) for g in d["games"]]
bal_ps = [g for g in ps_games if BAL in (g["teams"]["home"]["team"].get("id"), g["teams"]["away"]["team"].get("id"))]
ps_final = [g for g in ps_games if g["status"]["abstractGameState"] == "Final"]
ps_live = [g for g in ps_games if g["status"]["abstractGameState"] == "Live"]
ws_done = any(g.get("gameType") == "W" and g.get("seriesStatus", {}).get("isOver") for g in ps_games)
current_round = None
for g in ps_games:
    if g["status"]["abstractGameState"] in ("Live", "Preview") and g["teams"]["home"]["team"].get("id"):
        current_round = g.get("seriesDescription"); break
postseason = {"bal_in_postseason": bool(bal_ps), "bal_games": len(bal_ps), "games_final": len(ps_final),
              "games_live": len(ps_live), "current_round": current_round, "ws_complete": ws_done}

# ---------- leaders ----------
team_g = len(log)
hit = [s for s in load("player_hitting.json")["stats"][0]["splits"] if s.get("team", {}).get("id") == BAL]
pit = [s for s in load("player_pitching.json")["stats"][0]["splits"] if s.get("team", {}).get("id") == BAL]
def ip_to_outs(ip):
    a, _, b = str(ip).partition("."); return int(a) * 3 + int(b or 0)
qual_pa = 3.1 * team_g; qual_outs = 3 * team_g
def lead(rows, key, conv=float, rev=True, qual=None, fmt=None, k=3):
    rr = [r for r in rows if (qual is None or qual(r)) and r["stat"].get(key) not in (None, "", ".---", "-.--")]
    rr.sort(key=lambda r: conv(r["stat"][key]), reverse=rev)
    return [{"id": r["player"]["id"], "name": r["player"]["fullName"], "val": r["stat"][key]} for r in rr[:k]]
qh = lambda r: r["stat"]["plateAppearances"] >= qual_pa
qp = lambda r: ip_to_outs(r["stat"]["inningsPitched"]) >= qual_outs
leaders = {
  "batting": [
    {"stat": "HR", "list": lead(hit, "homeRuns", int)},
    {"stat": "RBI", "list": lead(hit, "rbi", int)},
    {"stat": "AVG", "note": f"min {qual_pa:.0f} PA", "list": lead(hit, "avg", qual=qh)},
    {"stat": "OPS", "note": f"min {qual_pa:.0f} PA", "list": lead(hit, "ops", qual=qh)},
    {"stat": "H", "list": lead(hit, "hits", int)},
    {"stat": "R", "list": lead(hit, "runs", int)},
    {"stat": "SB", "list": lead(hit, "stolenBases", int)},
    {"stat": "BB", "list": lead(hit, "baseOnBalls", int)},
  ],
  "pitching": [
    {"stat": "ERA", "note": f"min {team_g} IP", "list": lead(pit, "era", rev=False, qual=qp)},
    {"stat": "W", "list": lead(pit, "wins", int)},
    {"stat": "SO", "list": lead(pit, "strikeOuts", int)},
    {"stat": "IP", "list": lead(pit, "inningsPitched", ip_to_outs)},
    {"stat": "WHIP", "note": f"min {team_g} IP", "list": lead(pit, "whip", rev=False, qual=qp)},
    {"stat": "SV", "list": lead(pit, "saves", int)},
    {"stat": "HLD", "list": lead(pit, "holds", int)},
    {"stat": "ERA (relief, 40+ IP)", "list": lead(pit, "era", rev=False,
        qual=lambda r: ip_to_outs(r["stat"]["inningsPitched"]) >= 120 and r["stat"].get("gamesStarted", 0) <= 3)},
  ],
}
# player detail lines for leaders cards
def hline(s): x = s["stat"]; return f'{x["avg"]}/{x["obp"]}/{x["slg"]}, {x["homeRuns"]} HR, {x["rbi"]} RBI in {x["plateAppearances"]} PA'
def pline(s): x = s["stat"]; return f'{x["wins"]}-{x["losses"]}, {x["era"]} ERA, {x["strikeOuts"]} K in {x["inningsPitched"]} IP'
players = {}
for s in hit: players.setdefault(s["player"]["id"], {})["bat"] = hline(s)
for s in pit: players.setdefault(s["player"]["id"], {})["pit"] = pline(s)
ts = {s["group"]["displayName"]: s["splits"][0]["stat"] for s in load("team_stats.json")["stats"]}
team_line = {"avg": ts["hitting"]["avg"], "obp": ts["hitting"]["obp"], "slg": ts["hitting"]["slg"], "ops": ts["hitting"]["ops"],
             "hr": ts["hitting"]["homeRuns"], "sb": ts["hitting"]["stolenBases"], "runs": ts["hitting"]["runs"],
             "era": ts["pitching"]["era"], "whip": ts["pitching"]["whip"], "k": ts["pitching"]["strikeOuts"],
             "sv": ts["pitching"]["saves"], "ra": ts["pitching"]["runs"]}

# ---------- pythag ----------
pyth_pct = rs_tot ** 1.83 / (rs_tot ** 1.83 + ra_tot ** 1.83)
pyth_w = round(pyth_pct * team_g)

# ---------- summary paragraph (only computed numbers) ----------
def fdate(s): d_ = dt.date.fromisoformat(s); return d_.strftime("%b %-d")
def rstr(r): return f'{r["w"]}-{r["l"]}'
ws0, ls0 = win_streaks[0], lose_streaks[0]
best_m = max(month_rows, key=lambda m: (m["w"] - m["l"], m["w"]))
worst_m = min(month_rows, key=lambda m: (m["w"] - m["l"], m["w"]))
hr1 = leaders["batting"][0]["list"][0]; rbi1 = leaders["batting"][1]["list"][0]
era1 = leaders["pitching"][0]["list"][0] if leaders["pitching"][0]["list"] else None
so1 = leaders["pitching"][2]["list"][0]; sv1 = leaders["pitching"][5]["list"][0]
place = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth"}[bal_official["rank"]]
diff = rs_tot - ra_tot
pct_s = f"{w/(w+l):.3f}".lstrip("0")
parts = []
parts.append(f"The Orioles finished 2026 at {w}-{l} ({pct_s}), {place} in the AL East, {bal_official['gb']} games behind the "
             f"division-champion {next(t['name'] for t in al_east_official if t['rank']==1).split()[-1]}, and missed the postseason, "
             f"finishing {bal_official['wc_gb']} games out of the last AL Wild Card spot.")
parts.append(f"They scored {rs_tot} runs and allowed {ra_tot} (a {diff:+d} run differential, which projects to about "
             f"{pyth_w}-{team_g-pyth_w} by the Pythagorean formula).")
hi_s = f"The high-water mark came on {fdate(peaks['high']['date'])} at {peaks['high']['rec']} ({peaks['high']['over']:+d} vs .500); "
hi_s += f"the low point was {peaks['low']['rec']} on {fdate(peaks['low']['date'])}"
if peaks['last_500']:
    hi_s += f", and they were still at .500 ({peaks['last_500']['rec']}) as late as {fdate(peaks['last_500']['date'])}"
parts.append(hi_s + ".")
parts.append(f"{best_m['label']} was the best month ({rstr(best_m)}) and {worst_m['label']} the worst ({rstr(worst_m)}).")
parts.append(f"The longest winning streak was {ws0['len']} games ({fdate(ws0['from'])}–{fdate(ws0['to'])}) and the longest skid "
             f"{ls0['len']} ({fdate(ls0['from'])}–{fdate(ls0['to'])}).")
parts.append(f"They went {rstr(splits['One-run games'])} in one-run games, {rstr(splits['Home'])} at home and {rstr(splits['Road'])} on the road.")
lead_s = f"{hr1['name']} led the club with {hr1['val']} home runs"
lead_s += f" and {rbi1['val']} RBI" if rbi1['id'] == hr1['id'] else f", while {rbi1['name']} led with {rbi1['val']} RBI"
lead_s += "; "
if era1:
    lead_s += f"{era1['name']} posted the best qualified ERA ({era1['val']})"
    lead_s += f" and led the staff with {so1['val']} strikeouts" if so1['id'] == era1['id'] else f", {so1['name']} led in strikeouts ({so1['val']})"
else:
    lead_s += f"{so1['name']} led in strikeouts ({so1['val']})"
lead_s += f", and {sv1['name']} led in saves ({sv1['val']})."
parts.append(lead_s)
summary = " ".join(parts)

# ---------- offseason research (ij_* only; optional) ----------
research = None
rp = os.path.join(D, "research_notes.json")
if os.path.exists(rp):
    research = json.load(open(rp))

fetched_at = open(os.path.join(D, "fetched_at.txt")).read().strip()
out = {
  "meta": {"fetched_at": fetched_at, "built_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
           "sources": [
             {"name": "MLB Stats API: schedule + linescores (team 110 and AL East rivals)", "url": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId=110&season=2026&gameType=R&hydrate=linescore"},
             {"name": "MLB Stats API: AL standings", "url": "https://statsapi.mlb.com/api/v1/standings?leagueId=103&season=2026&standingsTypes=regularSeason"},
             {"name": "MLB Stats API: Orioles player season stats", "url": "https://statsapi.mlb.com/api/v1/stats?stats=season&group=hitting&teamId=110&season=2026&playerPool=ALL"},
             {"name": "MLB Stats API: team season stats", "url": "https://statsapi.mlb.com/api/v1/teams/110/stats?season=2026&group=hitting,pitching&stats=season"},
             {"name": "MLB Stats API: 2026 postseason schedule", "url": "https://statsapi.mlb.com/api/v1/schedule/postseason?season=2026&sportId=1"}]},
  "record": {"w": w, "l": l, "rs": rs_tot, "ra": ra_tot, "rd": diff, "g": team_g, "pct": f"{w/(w+l):.3f}".lstrip("0"),
             "pyth_w": pyth_w, "pyth_l": team_g - pyth_w, "al_rank": bal_al_rank, "div_rank": bal_official["rank"],
             "gb": bal_official["gb"], "wc_gb": bal_official["wc_gb"]},
  "official": {"w": bal_official["w"], "l": bal_official["l"], "rs": bal_official["rs"], "ra": bal_official["ra"]},
  "postseason": postseason, "postseason_teams_al": postseason_teams_al,
  "not_played": not_played,
  "log": log, "months": month_rows, "splits": [{"name": k, **v} for k, v in splits.items()], "h2h": h2h,
  "streaks": {"win": win_streaks, "lose": lose_streaks, **stretches}, "peaks": peaks,
  "games": {"best": best_games, "worst": worst_games, "most_runs": most_runs, "walkoffs": walkoffs,
            "longest": gsum(longest), "shutouts_for": shutouts_for, "shutouts_against": shutouts_against},
  "race": {"dates": dates, "series": race_series, "gb": gb, "bal_days_tied_or_first": bal_days_first},
  "standings": al_east_official, "leaders": leaders, "players": {str(k): v for k, v in players.items()},
  "team": team_line, "summary": summary,
  "research": research,
  "remaster": {"label": "Sat Oct 10 afternoon remaster", "aesthetic": "Camden Yards night wall", "port": 4278},
}
with open(os.path.join(D, "season.json"), "w") as f:
    json.dump(out, f, indent=1)
tpl = open(os.path.join(ROOT, "src", "template.html")).read()
html = tpl.replace("/*__SEASON_JSON__*/null", json.dumps(out, separators=(",", ":")).replace("</", "<\\/"))
os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
for p in ("dist/orioles-2026-snapshot.html", "dist/index.html"):
    with open(os.path.join(ROOT, p), "w") as f: f.write(html)
print(f"built: {w}-{l}, RS {rs_tot} RA {ra_tot}, {len(log)} games")
print(summary)
