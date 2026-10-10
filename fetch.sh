#!/usr/bin/env bash
# Re-fetch all raw data from the public MLB Stats API (statsapi.mlb.com). Read-only GETs.
set -euo pipefail
cd "$(dirname "$0")/data"
API=https://statsapi.mlb.com/api/v1
for t in 110 147 111 141 139; do
  f=schedule_R_$t.json; [ $t = 110 ] && f=schedule_R.json
  curl -sfg -m 30 "$API/schedule?sportId=1&teamId=$t&season=2026&gameType=R&hydrate=linescore" -o $f.tmp && mv $f.tmp $f
done
curl -sfg -m 30 "$API/standings?leagueId=103&season=2026&standingsTypes=regularSeason" -o standings_AL.json
curl -sfg -m 30 "$API/schedule/postseason?season=2026&sportId=1" -o postseason_all.json
curl -sfg -m 30 "$API/teams/110/stats?season=2026&group=hitting,pitching&stats=season" -o team_stats.json
curl -sfg -m 30 "$API/teams?sportId=1&season=2026" -o teams.json
for g in hitting pitching; do
  curl -sfg -m 30 "$API/stats?stats=season&group=$g&teamId=110&season=2026&playerPool=ALL&limit=200&gameType=R" -o player_$g.json
done
date -Iseconds > fetched_at.txt
echo "fetched at $(cat fetched_at.txt)"
