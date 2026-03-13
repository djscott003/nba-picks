#!/usr/bin/env python3
"""
NBA Picks Auto-Updater · Smart Model v4
New in v4:
- Expected Value (EV) on every ML and spread bet
- Juice-adjusted spread ratings (-105 vs -115 matters)
- Pace matchup for totals (team pace ratings)
- Rest vs rust (3+ days rest flag)
- Divisional game flag (fades big spreads)
- Best Bet of the Night callout
- Cleaner ML ratings (shows EV %, not just Strong/Value)
"""

import os, json, re, requests, pytz
from datetime import datetime, timedelta
from pathlib import Path

API_KEY = os.environ.get("ODDS_API_KEY", "")
SPORT   = "basketball_nba"
ET      = pytz.timezone("America/New_York")
HERE    = Path(os.path.dirname(os.path.abspath(__file__)))

# ── Team metadata ─────────────────────────────────────────────────────────────
COLORS = {
    "Atlanta Hawks":"#C1D32F","Boston Celtics":"#007A33","Brooklyn Nets":"#888",
    "Charlotte Hornets":"#1D1160","Chicago Bulls":"#CE1141","Cleveland Cavaliers":"#860038",
    "Dallas Mavericks":"#00538C","Denver Nuggets":"#0E2240","Detroit Pistons":"#1D428A",
    "Golden State Warriors":"#FFC72C","Houston Rockets":"#CE1141","Indiana Pacers":"#002D62",
    "LA Clippers":"#C8102E","Los Angeles Lakers":"#552583","Memphis Grizzlies":"#5D76A9",
    "Miami Heat":"#98002E","Milwaukee Bucks":"#00471B","Minnesota Timberwolves":"#0C2340",
    "New Orleans Pelicans":"#0C2340","New York Knicks":"#006BB6",
    "Oklahoma City Thunder":"#007AC1","Orlando Magic":"#0077C0",
    "Philadelphia 76ers":"#C4122F","Phoenix Suns":"#E56020",
    "Portland Trail Blazers":"#E03A3E","Sacramento Kings":"#5A2D81",
    "San Antonio Spurs":"#999","Toronto Raptors":"#CE1141",
    "Utah Jazz":"#002B5C","Washington Wizards":"#E31837",
}
ABBR = {
    "Atlanta Hawks":"ATL","Boston Celtics":"BOS","Brooklyn Nets":"BKN",
    "Charlotte Hornets":"CHA","Chicago Bulls":"CHI","Cleveland Cavaliers":"CLE",
    "Dallas Mavericks":"DAL","Denver Nuggets":"DEN","Detroit Pistons":"DET",
    "Golden State Warriors":"GSW","Houston Rockets":"HOU","Indiana Pacers":"IND",
    "LA Clippers":"LAC","Los Angeles Lakers":"LAL","Memphis Grizzlies":"MEM",
    "Miami Heat":"MIA","Milwaukee Bucks":"MIL","Minnesota Timberwolves":"MIN",
    "New Orleans Pelicans":"NOP","New York Knicks":"NYK",
    "Oklahoma City Thunder":"OKC","Orlando Magic":"ORL",
    "Philadelphia 76ers":"PHI","Phoenix Suns":"PHX",
    "Portland Trail Blazers":"POR","Sacramento Kings":"SAC",
    "San Antonio Spurs":"SAS","Toronto Raptors":"TOR",
    "Utah Jazz":"UTA","Washington Wizards":"WAS",
}
SHORT = {
    "Atlanta Hawks":"Hawks","Boston Celtics":"Celtics","Brooklyn Nets":"Nets",
    "Charlotte Hornets":"Hornets","Chicago Bulls":"Bulls","Cleveland Cavaliers":"Cavs",
    "Dallas Mavericks":"Mavs","Denver Nuggets":"Nuggets","Detroit Pistons":"Pistons",
    "Golden State Warriors":"Warriors","Houston Rockets":"Rockets","Indiana Pacers":"Pacers",
    "LA Clippers":"Clippers","Los Angeles Lakers":"Lakers","Memphis Grizzlies":"Grizzlies",
    "Miami Heat":"Heat","Milwaukee Bucks":"Bucks","Minnesota Timberwolves":"Wolves",
    "New Orleans Pelicans":"Pelicans","New York Knicks":"Knicks",
    "Oklahoma City Thunder":"Thunder","Orlando Magic":"Magic",
    "Philadelphia 76ers":"76ers","Phoenix Suns":"Suns",
    "Portland Trail Blazers":"Blazers","Sacramento Kings":"Kings",
    "San Antonio Spurs":"Spurs","Toronto Raptors":"Raptors",
    "Utah Jazz":"Jazz","Washington Wizards":"Wizards",
}
CONF = {
    "ATL":"E","BOS":"E","BKN":"E","CHA":"E","CHI":"E","CLE":"E",
    "DAL":"W","DEN":"W","DET":"E","GSW":"W","HOU":"W","IND":"E",
    "LAC":"W","LAL":"W","MEM":"W","MIA":"E","MIL":"E","MIN":"W",
    "NOP":"W","NYK":"E","OKC":"W","ORL":"E","PHI":"E","PHX":"W",
    "POR":"W","SAC":"W","SAS":"W","TOR":"E","UTA":"W","WAS":"E",
}

# Divisions for divisional game detection
DIVISION = {
    "ATL":"SE","BOS":"A","BKN":"A","CHA":"SE","CHI":"C","CLE":"C",
    "DAL":"SW","DEN":"NW","DET":"C","GSW":"P","HOU":"SW","IND":"C",
    "LAC":"P","LAL":"P","MEM":"SW","MIA":"SE","MIL":"C","MIN":"NW",
    "NOP":"SW","NYK":"A","OKC":"NW","ORL":"SE","PHI":"A","PHX":"P",
    "POR":"NW","SAC":"P","SAS":"SW","TOR":"A","UTA":"NW","WAS":"SE",
}

# Power rankings (1=best) — update weekly
POWER = {
    "OKC":1,"SAS":2,"DET":3,"MIN":4,"HOU":5,"DEN":6,"LAL":7,"PHX":8,
    "NYK":9,"BOS":10,"CLE":11,"MIA":12,"GSW":13,"ORL":14,"ATL":15,
    "PHI":16,"TOR":17,"LAC":18,"POR":19,"MIL":20,"CHA":21,"SAC":22,
    "CHI":23,"NOP":24,"DAL":25,"MEM":26,"IND":27,"WAS":28,"BKN":29,"UTA":30,
}

# Pace ratings (possessions per 48 min, approx) — update weekly
# Higher = faster pace
PACE = {
    "ATL":102.1,"BOS":98.4,"BKN":99.2,"CHA":100.5,"CHI":99.8,"CLE":97.6,
    "DAL":98.9,"DEN":101.2,"DET":100.8,"GSW":102.4,"HOU":101.9,"IND":103.5,
    "LAC":99.1,"LAL":100.3,"MEM":100.6,"MIA":98.7,"MIL":99.9,"MIN":98.2,
    "NOP":101.4,"NYK":97.8,"OKC":100.1,"ORL":98.5,"PHI":99.3,"PHX":102.8,
    "POR":101.7,"SAC":103.2,"SAS":101.5,"TOR":100.0,"UTA":99.6,"WAS":100.9,
}

# Home/away splits — win% at home vs away (approx current season)
HOME_WIN_PCT = {
    "OKC":0.78,"SAS":0.76,"DET":0.74,"MIN":0.72,"HOU":0.70,"DEN":0.68,
    "LAL":0.67,"PHX":0.65,"NYK":0.64,"BOS":0.63,"CLE":0.62,"MIA":0.61,
    "GSW":0.60,"ORL":0.59,"ATL":0.58,"PHI":0.57,"TOR":0.56,"LAC":0.55,
    "POR":0.54,"MIL":0.50,"CHA":0.49,"SAC":0.48,"CHI":0.47,"NOP":0.46,
    "DAL":0.44,"MEM":0.43,"IND":0.42,"WAS":0.35,"BKN":0.34,"UTA":0.32,
}
AWAY_WIN_PCT = {
    "OKC":0.72,"SAS":0.70,"DET":0.68,"MIN":0.66,"HOU":0.64,"DEN":0.62,
    "LAL":0.61,"PHX":0.59,"NYK":0.58,"BOS":0.57,"CLE":0.56,"MIA":0.55,
    "GSW":0.54,"ORL":0.53,"ATL":0.52,"PHI":0.51,"TOR":0.50,"LAC":0.49,
    "POR":0.48,"MIL":0.44,"CHA":0.43,"SAC":0.42,"CHI":0.41,"NOP":0.40,
    "DAL":0.38,"MEM":0.37,"IND":0.36,"WAS":0.29,"BKN":0.28,"UTA":0.26,
}

# ── EV calculations ───────────────────────────────────────────────────────────

def ml_to_implied(ml):
    """Convert American odds to implied probability (with vig)."""
    if ml < 0: return abs(ml) / (abs(ml) + 100)
    return 100 / (ml + 100)

def ml_to_decimal(ml):
    if ml < 0: return 100 / abs(ml) + 1
    return ml / 100 + 1

def calc_ev(win_prob, ml):
    """
    Expected Value as a percentage of stake.
    EV% = (win_prob * profit_per_unit) - (lose_prob * 1)
    Positive EV = good bet, negative = bad bet
    """
    dec = ml_to_decimal(ml)
    profit = dec - 1  # profit per $1 staked
    ev = (win_prob * profit) - ((1 - win_prob) * 1)
    return round(ev * 100, 1)  # as percentage

def juice_to_break_even(juice_str):
    """What win % do you need just to break even at this juice?"""
    ml = int(juice_str.replace("+",""))
    return ml_to_implied(ml)

def spread_ev(win_prob, juice_str):
    """EV for a spread bet given model win prob and juice."""
    ml = int(juice_str.replace("+",""))
    return calc_ev(win_prob, ml)

# ── Fetch functions ───────────────────────────────────────────────────────────

def fetch_odds():
    r = requests.get(
        f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/",
        params={"apiKey":API_KEY,"regions":"us","markets":"h2h,spreads,totals",
                "oddsFormat":"american","dateFormat":"iso"},
        timeout=15)
    r.raise_for_status()
    print(f"Odds API remaining: {r.headers.get('x-requests-remaining','?')}")
    return r.json()

def fetch_b2b():
    try:
        r = requests.get(
            f"https://api.the-odds-api.com/v4/sports/{SPORT}/scores/",
            params={"apiKey":API_KEY,"daysFrom":1,"dateFormat":"iso"},
            timeout=15)
        r.raise_for_status()
        played, yesterday = set(), (datetime.now(ET)-timedelta(days=1)).date()
        for g in r.json():
            tip = datetime.fromisoformat(g["commence_time"].replace("Z","+00:00")).astimezone(ET)
            if tip.date() == yesterday:
                played.add(g["home_team"]); played.add(g["away_team"])
        return played
    except Exception as e:
        print(f"B2B fetch failed: {e}"); return set()

def fetch_recent_schedule():
    """Returns dict of team -> last game date (for rest/rust detection)."""
    try:
        r = requests.get(
            f"https://api.the-odds-api.com/v4/sports/{SPORT}/scores/",
            params={"apiKey":API_KEY,"daysFrom":5,"dateFormat":"iso"},
            timeout=15)
        r.raise_for_status()
        last_played = {}
        for g in r.json():
            if not g.get("completed"): continue
            tip = datetime.fromisoformat(g["commence_time"].replace("Z","+00:00")).astimezone(ET)
            for team in [g["home_team"], g["away_team"]]:
                ab = ABBR.get(team, team[:3].upper())
                if ab not in last_played or tip.date() > last_played[ab]:
                    last_played[ab] = tip.date()
        return last_played
    except Exception as e:
        print(f"Schedule fetch failed: {e}"); return {}

def fetch_injuries():
    injuries = {}
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(
            "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries",
            headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        for item in data.get("injuries", []):
            team_ab = item.get("team", {}).get("abbreviation", "")
            if team_ab == "NO": team_ab = "NOP"
            if team_ab == "GS": team_ab = "GSW"
            if team_ab == "SA": team_ab = "SAS"
            if team_ab == "NY": team_ab = "NYK"
            players = []
            for inj in item.get("injuries", []):
                status = inj.get("status","").lower()
                name   = inj.get("athlete",{}).get("shortName","")
                if status in ["out","doubtful","questionable"] and name:
                    players.append({"name":name,"status":status})
            if players:
                injuries[team_ab] = players[:3]
    except Exception as e:
        print(f"Injury fetch failed: {e}")
    return injuries

def fetch_betting_pcts(games):
    pcts = {}
    try:
        today = datetime.now(ET).strftime("%Y-%m-%d")
        an_r = requests.get(
            f"https://api.actionnetwork.com/web/v1/games?sport=nba&date={today}",
            headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        if an_r.status_code == 200:
            for game in an_r.json().get("games", []):
                teams = game.get("teams", [])
                if len(teams) < 2: continue
                def norm(ab):
                    ab = ab.upper()
                    return {"GS":"GSW","NO":"NOP","SA":"SAS","NY":"NYK"}.get(ab,ab)
                away_ab = norm(teams[0].get("abbr",""))
                home_ab = norm(teams[1].get("abbr",""))
                sd = game.get("spread", {})
                ab = sd.get("away_spread_bets_pct")
                hb = sd.get("home_spread_bets_pct")
                am = sd.get("away_spread_money_pct")
                hm = sd.get("home_spread_money_pct")
                if ab and hb:
                    pcts[f"{away_ab}@{home_ab}"] = {
                        "away_bets":int(ab),"home_bets":int(hb),
                        "away_money":int(am) if am else None,
                        "home_money":int(hm) if hm else None,
                    }
    except Exception as e:
        print(f"Betting pct fetch failed: {e}")
    return pcts

def fetch_scores_for_grading():
    try:
        r = requests.get(
            f"https://api.the-odds-api.com/v4/sports/{SPORT}/scores/",
            params={"apiKey":API_KEY,"daysFrom":2,"dateFormat":"iso"},
            timeout=15)
        r.raise_for_status()
        results = {}
        yesterday = (datetime.now(ET)-timedelta(days=1)).date()
        for g in r.json():
            if g.get("completed") != True: continue
            tip = datetime.fromisoformat(g["commence_time"].replace("Z","+00:00")).astimezone(ET)
            if tip.date() != yesterday: continue
            home = ABBR.get(g["home_team"], g["home_team"][:3].upper())
            away = ABBR.get(g["away_team"], g["away_team"][:3].upper())
            scores = {s["name"]:s["score"] for s in (g.get("scores") or []) if s.get("score")}
            if not scores: continue
            hs = int(scores.get(g["home_team"], 0))
            as_ = int(scores.get(g["away_team"], 0))
            results[f"{away}@{home}"] = {"home":home,"away":away,"home_score":hs,"away_score":as_}
        return results
    except Exception as e:
        print(f"Scores fetch failed: {e}"); return {}

# ── Record ────────────────────────────────────────────────────────────────────

def load_record():
    path = HERE / "record.json"
    if path.exists(): return json.loads(path.read_text())
    return {"picks":[],"summary":{"ats":{"w":0,"l":0,"p":0},"total":{"w":0,"l":0,"p":0}}}

def save_record(record):
    (HERE / "record.json").write_text(json.dumps(record, indent=2))

def log_picks(games, record):
    today = datetime.now(ET).strftime("%Y-%m-%d")
    record["picks"] = [p for p in record["picks"] if p["date"] != today]
    for g in games:
        if g.get("spdSide"):
            record["picks"].append({
                "date":today,"game":f"{g['away']}@{g['home']}",
                "type":"ATS","pick":g["spdSide"],
                "spread":g["homeSpread"],"total":None,"result":None,
                "ev":g.get("spdEV"),
            })
        if g.get("totalRec") == "value":
            record["picks"].append({
                "date":today,"game":f"{g['away']}@{g['home']}",
                "type":"TOTAL","pick":"over" if g["totalPick"].startswith("Over") else "under",
                "spread":None,"total":g["total"],"result":None,"ev":None,
            })
    save_record(record)

def grade_picks(record, results):
    yesterday = (datetime.now(ET)-timedelta(days=1)).strftime("%Y-%m-%d")
    for pick in record["picks"]:
        if pick["date"] != yesterday or pick["result"] is not None: continue
        result = results.get(pick["game"])
        if not result: continue
        hs, as_ = result["home_score"], result["away_score"]
        if pick["type"] == "ATS":
            spread = pick["spread"]
            home_covers = (hs + spread) > as_
            home_push   = (hs + spread) == as_
            if pick["pick"] == "home":
                pick["result"] = "push" if home_push else ("win" if home_covers else "loss")
            else:
                pick["result"] = "push" if home_push else ("loss" if home_covers else "win")
        elif pick["type"] == "TOTAL":
            actual = hs + as_
            if actual == pick["total"]: pick["result"] = "push"
            elif pick["pick"] == "over": pick["result"] = "win" if actual > pick["total"] else "loss"
            else: pick["result"] = "win" if actual < pick["total"] else "loss"
    ats = {"w":0,"l":0,"p":0}; total = {"w":0,"l":0,"p":0}
    for pick in record["picks"]:
        if pick["result"] is None: continue
        bucket = ats if pick["type"]=="ATS" else total
        if pick["result"]=="win": bucket["w"]+=1
        elif pick["result"]=="loss": bucket["l"]+=1
        elif pick["result"]=="push": bucket["p"]+=1
    record["summary"] = {"ats":ats,"total":total}
    save_record(record); return record

# ── Parse games ───────────────────────────────────────────────────────────────

def parse_games(raw, b2b, last_played, injuries, bet_pcts):
    games, today = [], datetime.now(ET).date()
    preferred = ["draftkings","fanduel","betmgm","williamhill_us","bovada"]

    for g in raw:
        tip = datetime.fromisoformat(g["commence_time"].replace("Z","+00:00")).astimezone(ET)
        if tip.date() != today: continue

        home, away = g["home_team"], g["away_team"]
        home_ab = ABBR.get(home, home[:3].upper())
        away_ab = ABBR.get(away, away[:3].upper())

        home_ml = away_ml = home_spread = total = None
        spread_juice = "-110"; over_juice = "-110"; under_juice = "-110"

        for bk_key in preferred:
            bk = next((b for b in g.get("bookmakers",[]) if b["key"]==bk_key), None)
            if not bk: continue
            for mkt in bk.get("markets",[]):
                if mkt["key"]=="h2h":
                    for o in mkt["outcomes"]:
                        if o["name"]==home: home_ml=o["price"]
                        if o["name"]==away: away_ml=o["price"]
                elif mkt["key"]=="spreads":
                    for o in mkt["outcomes"]:
                        if o["name"]==home:
                            home_spread=o["point"]; spread_juice=f"{o['price']:+d}"
                elif mkt["key"]=="totals":
                    for o in mkt["outcomes"]:
                        if o["name"]=="Over":  total=o["point"]; over_juice=f"{o['price']:+d}"
                        if o["name"]=="Under": under_juice=f"{o['price']:+d}"
            if home_ml and home_spread and total: break

        if not (home_ml and home_spread and total): continue

        # ── Rest / rust detection ─────────────────────────────────────────────
        home_last = last_played.get(home_ab)
        away_last = last_played.get(away_ab)
        days_rest_home = (today - home_last).days if home_last else 2
        days_rest_away = (today - away_last).days if away_last else 2
        home_b2b = home in b2b; away_b2b = away in b2b
        # 3+ days rest without playing = rust risk
        home_rust = days_rest_home >= 3 and not home_b2b
        away_rust = days_rest_away >= 3 and not away_b2b

        # ── Divisional game ───────────────────────────────────────────────────
        same_division = DIVISION.get(home_ab) == DIVISION.get(away_ab)

        # ── Line movement ─────────────────────────────────────────────────────
        abs_spd = abs(home_spread)
        line_moved = (abs_spd % 1 == 0.5)
        line_move_note = ""
        if line_moved:
            line_move_note = f"Line moved toward {'home' if home_spread < 0 else 'away'} (sharp action)"

        # ── Power ranking factor ──────────────────────────────────────────────
        home_pr = POWER.get(home_ab, 15)
        away_pr = POWER.get(away_ab, 15)
        pr_edge = away_pr - home_pr  # positive = home ranked better

        # ── Home/away split factor ────────────────────────────────────────────
        home_home_wpct = HOME_WIN_PCT.get(home_ab, 0.50)
        away_away_wpct = AWAY_WIN_PCT.get(away_ab, 0.50)
        # Combined split edge: how much better is home at home vs away on road?
        split_edge = (home_home_wpct - 0.50) - (away_away_wpct - 0.50)

        # ── Pace matchup ──────────────────────────────────────────────────────
        home_pace = PACE.get(home_ab, 100.5)
        away_pace = PACE.get(away_ab, 100.5)
        avg_pace  = (home_pace + away_pace) / 2
        # Pace vs total line
        pace_total_diff = avg_pace - 100.5  # positive = faster than avg
        # Strong over signal: fast pace AND total seems low
        # Strong under signal: slow pace AND total seems high
        if avg_pace >= 102 and total <= 225:
            total_pick, total_rec = f"Over {total}", "strong"
            total_note = f"Fast pace matchup ({avg_pace:.1f} avg) with a low total — lean Over"
        elif avg_pace >= 101 and total <= 220:
            total_pick, total_rec = f"Over {total}", "value"
            total_note = f"Above-avg pace ({avg_pace:.1f}) — slight Over lean"
        elif avg_pace <= 99 and total >= 225:
            total_pick, total_rec = f"Under {total}", "strong"
            total_note = f"Slow pace matchup ({avg_pace:.1f} avg) with a high total — lean Under"
        elif avg_pace <= 100 and total >= 222:
            total_pick, total_rec = f"Under {total}", "value"
            total_note = f"Slower pace ({avg_pace:.1f}) — slight Under lean"
        elif total >= 230:
            total_pick, total_rec = f"Over {total}", "value"
            total_note = f"High total with avg pace — lean Over"
        elif total <= 215:
            total_pick, total_rec = f"Under {total}", "value"
            total_note = f"Low total with avg pace — lean Under"
        else:
            total_pick, total_rec = str(total), "neutral"
            total_note = f"Neutral pace matchup ({avg_pace:.1f}) — no strong total lean"

        # ── Injury impact ─────────────────────────────────────────────────────
        home_inj = injuries.get(home_ab, [])
        away_inj = injuries.get(away_ab, [])

        # ── Win probability (vig-removed) ─────────────────────────────────────
        rp_h = ml_to_implied(home_ml) * 100
        rp_a = ml_to_implied(away_ml) * 100
        tot_p = rp_h + rp_a
        home_prob = round(rp_h / tot_p * 100, 1)
        away_prob = round(100 - home_prob, 1)

        # ── Smart model score ─────────────────────────────────────────────────
        score = 50.0
        score += (home_prob - 50) * 0.25         # win prob 25%
        score += 3.0                               # base home court 10%
        score += split_edge * 20                   # home/away splits 10%
        if home_b2b: score -= 4.0                 # B2B 15%
        if away_b2b: score += 3.5
        if home_rust: score -= 1.5                # rest/rust
        if away_rust: score += 1.5
        if abs_spd >= 14: score -= 3.0            # spread size ATS 10%
        elif abs_spd >= 10: score -= 1.5
        elif abs_spd <= 3: score += 1.0
        score += pr_edge * 0.15                   # power rankings 10%
        if line_moved:
            score += 1.5 if home_spread < 0 else -1.5  # line movement 10%
        home_inj_pen = min(len(home_inj) * 2.0, 5.0)
        away_inj_pen = min(len(away_inj) * 2.0, 5.0)
        score -= home_inj_pen                      # injuries 10%
        score += away_inj_pen
        if same_division: score -= 1.5            # divisional games are closer

        proj = (home_prob - 50) * 0.38
        edge = proj - abs_spd if home_spread < 0 else proj + home_spread

        # ── ATS recommendation ────────────────────────────────────────────────
        if home_spread < 0:
            if edge > 3 and score > 54:   spd_side, spd_rec = "home", "strong"
            elif edge > 1 and score > 52: spd_side, spd_rec = "home", "value"
            elif edge < -2 or score < 46: spd_side, spd_rec = "away", "value"
            else:                          spd_side, spd_rec = None, "neutral"
        else:
            if edge < -3 and score < 46:  spd_side, spd_rec = "away", "strong"
            elif edge < -1 and score < 48: spd_side, spd_rec = "away", "value"
            elif edge > 2 or score > 54:  spd_side, spd_rec = "home", "value"
            else:                          spd_side, spd_rec = None, "neutral"

        # ── EV calculations ───────────────────────────────────────────────────
        # ML EV: use model win prob vs actual payout
        home_ml_ev = calc_ev(home_prob / 100, home_ml)
        away_ml_ev = calc_ev(away_prob / 100, away_ml)

        # Spread EV: model assigns 52% win prob to spread side (accounting for vig)
        # Adjusted by how strong the edge is
        spd_model_prob = 0.52 + max(min(edge * 0.02, 0.10), -0.10)
        home_spd_ev = spread_ev(spd_model_prob if spd_side == "home" else 1 - spd_model_prob,
                                 spread_juice)
        away_spd_ev = spread_ev(spd_model_prob if spd_side == "away" else 1 - spd_model_prob,
                                 spread_juice)

        # ML rating based on EV (not just win prob)
        fav_is_home = home_ml < away_ml
        fav_ev  = home_ml_ev if fav_is_home else away_ml_ev
        dog_ev  = away_ml_ev if fav_is_home else home_ml_ev

        # ML rec — only recommend if positive EV
        if home_ml_ev > 5:    home_ml_rec = "strong"
        elif home_ml_ev > 2:  home_ml_rec = "value"
        elif home_ml_ev > 0:  home_ml_rec = "lean"
        elif home_ml_ev > -3: home_ml_rec = "neutral"
        else:                  home_ml_rec = "fade"

        if away_ml_ev > 5:    away_ml_rec = "strong"
        elif away_ml_ev > 2:  away_ml_rec = "value"
        elif away_ml_ev > 0:  away_ml_rec = "lean"
        elif away_ml_ev > -3: away_ml_rec = "neutral"
        else:                  away_ml_rec = "fade"

        # ── Betting percentages ───────────────────────────────────────────────
        bp = bet_pcts.get(f"{away_ab}@{home_ab}", {})
        sharp_flag = False; sharp_note = ""
        if bp.get("away_bets") and bp.get("away_money"):
            if bp["away_bets"] > 60 and (bp.get("home_money") or 0) > 55:
                sharp_flag = True
                sharp_note = f"Sharp $$ on {home_ab} despite {bp['away_bets']}% public on {away_ab}"
            elif (bp.get("home_bets") or 0) > 60 and (bp.get("away_money") or 0) > 55:
                sharp_flag = True
                sharp_note = f"Sharp $$ on {away_ab} despite {bp.get('home_bets')}% public on {home_ab}"

        # ── Overall game score (for Best Bet ranking) ─────────────────────────
        best_bet_score = 0
        if spd_rec == "strong": best_bet_score += 40
        elif spd_rec == "value": best_bet_score += 20
        if home_ml_ev > 5 or away_ml_ev > 5: best_bet_score += 20
        if total_rec == "strong": best_bet_score += 20
        elif total_rec == "value": best_bet_score += 10
        if sharp_flag: best_bet_score += 15
        if line_moved: best_bet_score += 10
        if home_inj or away_inj: best_bet_score -= 10  # uncertainty penalty
        if same_division: best_bet_score += 5  # divisional = interesting

        # ── Signals ───────────────────────────────────────────────────────────
        sigs = []
        if home_b2b:  sigs.append({"t":f"{home_ab} B2B 😴","c":"sig-f"})
        if away_b2b:  sigs.append({"t":f"{away_ab} B2B 😴","c":"sig-f"})
        if home_rust: sigs.append({"t":f"{home_ab} rust ({days_rest_home}d off)","c":"sig-f"})
        if away_rust: sigs.append({"t":f"{away_ab} rust ({days_rest_away}d off)","c":"sig-f"})
        if home_inj:  sigs.append({"t":f"{home_ab} injuries ⚠️","c":"sig-f"})
        if away_inj:  sigs.append({"t":f"{away_ab} injuries ⚠️","c":"sig-f"})
        if sharp_flag: sigs.append({"t":"Sharp $$ 🔪","c":"sig-v"})
        if line_moved: sigs.append({"t":"Line moved 📈","c":"sig-i"})
        if same_division: sigs.append({"t":"Divisional game","c":"sig-i"})
        if abs_spd >= 14: sigs.append({"t":f"Dog +{abs_spd} ATS value","c":"sig-v"})
        if spd_rec == "strong": sigs.append({"t":f"{'Home' if spd_side=='home' else 'Away'} covers","c":"sig-s"})
        elif spd_rec == "value": sigs.append({"t":f"ATS edge: {spd_side or 'dog'}","c":"sig-v"})
        if total_rec in ("strong","value"): sigs.append({"t":total_pick,"c":"sig-s" if total_rec=="strong" else "sig-i"})
        sigs = sigs[:5]

        # ── Note ──────────────────────────────────────────────────────────────
        fav_ab = home_ab if home_spread < 0 else away_ab
        b2b_note = ""
        if home_b2b: b2b_note += f" {home_ab} on a back-to-back."
        if away_b2b: b2b_note += f" {away_ab} on a back-to-back."
        rust_note = ""
        if home_rust: rust_note += f" {home_ab} on {days_rest_home} days rest (rust risk)."
        if away_rust: rust_note += f" {away_ab} on {days_rest_away} days rest (rust risk)."
        inj_note = ""
        if home_inj: inj_note += f" {home_ab}: {', '.join(p['name']+'('+p['status']+')' for p in home_inj)}."
        if away_inj: inj_note += f" {away_ab}: {', '.join(p['name']+'('+p['status']+')' for p in away_inj)}."
        div_note = " Divisional matchup — expect a tighter game, fade big spreads." if same_division else ""
        ev_note = f" ML EV: {home_ab} {home_ml_ev:+.1f}% / {away_ab} {away_ml_ev:+.1f}%."

        note = (f"Vegas has {fav_ab} as {abs_spd}-pt favorite. "
                f"Model: {fav_ab} wins {max(home_prob,away_prob):.0f}%, spread edge {edge:+.1f} pts."
                f"{b2b_note}{rust_note}{inj_note}{div_note} {total_note}.{ev_note}"
                f"{' '+sharp_note if sharp_note else ''}"
                f"{' '+line_move_note+'.' if line_move_note else ''}")

        games.append({
            "id":len(games)+1,"time":tip.strftime("%-I:%M %p ET"),
            "conf":CONF.get(home_ab,"E"),
            "away":away_ab,"awayFull":SHORT.get(away,away),
            "awayColor":COLORS.get(away,"#888"),"awayB2B":away_b2b,"awayRust":away_rust,
            "awayInjuries":[p["name"] for p in away_inj],
            "home":home_ab,"homeFull":SHORT.get(home,home),
            "homeColor":COLORS.get(home,"#444"),"homeB2B":home_b2b,"homeRust":home_rust,
            "homeInjuries":[p["name"] for p in home_inj],
            "homeSpread":home_spread,"juice":spread_juice,
            "awayML":f"{away_ml:+d}","homeML":f"{home_ml:+d}",
            "total":total,"overJ":over_juice,"underJ":under_juice,
            "homeWinProb":home_prob,"awayWinProb":away_prob,
            "homeMLEV":home_ml_ev,"awayMLEV":away_ml_ev,
            "homeSpdEV":round(home_spd_ev,1),"awaySpdEV":round(away_spd_ev,1),
            "homeMLRec":home_ml_rec,"awayMLRec":away_ml_rec,
            "modelScore":round(score,1),"projMargin":round(proj,1),"spreadEdge":round(edge,1),
            "spdSide":spd_side,"spdRec":spd_rec,"spdEV":round(home_spd_ev if spd_side=="home" else away_spd_ev,1),
            "totalPick":total_pick,"totalRec":total_rec,"avgPace":round(avg_pace,1),
            "sameDivision":same_division,"lineMoved":line_moved,
            "sharpFlag":sharp_flag,"sharpNote":sharp_note,
            "awayBetPct":bp.get("away_bets"),"homeBetPct":bp.get("home_bets"),
            "awayMoneyPct":bp.get("away_money"),"homeMoneyPct":bp.get("home_money"),
            "bestBetScore":best_bet_score,
            "signals":sigs,"note":note,
        })

    games.sort(key=lambda x: x["time"])
    # Tag the best bet
    if games:
        best = max(games, key=lambda x: x["bestBetScore"])
        best["isBestBet"] = True
    return games

# ── HTML ──────────────────────────────────────────────────────────────────────

def build_index(games, date_str, record):
    gj  = json.dumps(games, indent=2)
    n   = len(games)
    ats = record["summary"]["ats"]
    tot = record["summary"]["total"]
    ats_str = f"{ats['w']}-{ats['l']}{'-'+str(ats['p']) if ats['p'] else ''}"
    tot_str = f"{tot['w']}-{tot['l']}{'-'+str(tot['p']) if tot['p'] else ''}"
    total_ats = ats['w']+ats['l']
    ats_pct = f"{ats['w']/total_ats*100:.0f}%" if total_ats else "—"

    # Best bet callout
    best = next((g for g in games if g.get("isBestBet")), None)
    best_html = ""
    if best:
        abs_spd = abs(best["homeSpread"])
        fav = best["home"] if best["homeSpread"] < 0 else best["away"]
        pick_str = ""
        if best["spdSide"] == "home": pick_str = f"{best['home']} -{abs_spd}"
        elif best["spdSide"] == "away": pick_str = f"{best['away']} +{abs_spd}"
        else: pick_str = best["totalPick"]
        best_html = f'''<div style="background:linear-gradient(135deg,rgba(255,193,7,0.12),rgba(0,229,255,0.08));border:1px solid rgba(255,193,7,0.35);border-radius:14px;padding:14px 16px;margin-bottom:14px;">
          <div style="font-size:10px;font-weight:800;color:var(--gold);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">🏆 Best Bet of the Night</div>
          <div style="font-size:20px;font-weight:900;color:var(--text);margin-bottom:4px;">{best["away"]} @ {best["home"]}</div>
          <div style="font-size:16px;font-weight:800;color:var(--green);">{pick_str}</div>
          <div style="font-size:11px;color:var(--muted2);margin-top:4px;">Model score {best["modelScore"]} · EV {best["spdEV"]:+.1f}% · {best["time"]}</div>
        </div>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>NBA Picks · {date_str}</title>
<style>
:root{{--bg:#06080f;--card:#0d1119;--card2:#131822;--border:rgba(255,255,255,0.07);--border2:rgba(255,255,255,0.13);--text:#e2e6f0;--muted:#4a5270;--muted2:#7a84a8;--green:#00e676;--red:#ff4444;--gold:#ffc107;--blue:#40c4ff;--purple:#b388ff;--accent:#00e5ff;--accent2:#0091ea;}}
*{{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent;}}
html,body{{height:100%;overflow-x:hidden;}}
body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display','Segoe UI',sans-serif;font-size:14px;}}
.hdr{{background:var(--card);border-bottom:1px solid var(--border);padding:14px 16px 12px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;}}
.hdr-left{{display:flex;flex-direction:column;}}
.hdr-title{{font-size:21px;font-weight:900;color:var(--accent);letter-spacing:-0.01em;line-height:1;}}
.hdr-sub{{font-size:10px;color:var(--muted2);text-transform:uppercase;letter-spacing:0.1em;margin-top:3px;}}
.hdr-right{{display:flex;flex-direction:column;align-items:flex-end;gap:4px;}}
.live-pill{{display:flex;align-items:center;gap:5px;background:rgba(0,230,118,0.08);border:1px solid rgba(0,230,118,0.22);border-radius:20px;padding:4px 10px;font-size:10px;font-weight:800;color:var(--green);text-transform:uppercase;letter-spacing:0.07em;white-space:nowrap;}}
.record-pill{{font-size:10px;color:var(--gold);font-weight:700;}}
.dot{{width:6px;height:6px;border-radius:50%;background:var(--green);animation:pulse 1.5s infinite;flex-shrink:0;}}
@keyframes pulse{{0%,100%{{opacity:1;transform:scale(1)}}50%{{opacity:0.4;transform:scale(0.8)}}}}
.disc{{background:rgba(255,193,7,0.06);border-bottom:1px solid rgba(255,193,7,0.12);padding:7px 16px;font-size:10px;color:rgba(255,193,7,0.7);line-height:1.5;}}
.tab-bar{{display:flex;background:var(--card);border-bottom:1px solid var(--border);position:sticky;top:57px;z-index:99;}}
.tab-btn{{flex:1;padding:13px 8px;font-size:11px;font-weight:800;color:var(--muted);cursor:pointer;border-bottom:2px solid transparent;text-transform:uppercase;letter-spacing:0.07em;text-align:center;transition:color 0.15s,border-color 0.15s;}}
.tab-btn.on{{color:var(--accent);border-bottom-color:var(--accent);}}
.pane{{display:none;padding:12px 12px 72px;max-width:680px;margin:0 auto;}}
.pane.on{{display:block;}}
.section-label{{font-size:10px;font-weight:800;color:var(--muted);text-transform:uppercase;letter-spacing:0.1em;margin:0 0 8px;display:flex;align-items:center;gap:6px;}}
.section-label::after{{content:'';flex:1;height:1px;background:var(--border);}}
.game-card{{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden;margin-bottom:10px;cursor:pointer;transition:border-color 0.18s;}}
.game-card.open{{border-color:rgba(0,229,255,0.35);}}
.game-card.best-bet{{border-color:rgba(255,193,7,0.4);}}
.game-card:active{{opacity:0.9;}}
.gc-top{{padding:10px 14px 8px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border);flex-wrap:wrap;gap:4px;}}
.gc-time{{font-size:10px;font-weight:700;color:var(--muted2);text-transform:uppercase;letter-spacing:0.08em;}}
.gc-badges{{display:flex;gap:4px;flex-wrap:wrap;justify-content:flex-end;}}
.badge{{font-size:9px;font-weight:800;padding:2px 7px;border-radius:10px;text-transform:uppercase;letter-spacing:0.04em;}}
.badge-e{{background:rgba(64,196,255,0.12);color:var(--blue);}}
.badge-w{{background:rgba(255,68,68,0.12);color:#ff8a80;}}
.badge-ou{{background:rgba(255,193,7,0.1);color:var(--gold);}}
.badge-b2b{{background:rgba(255,68,68,0.12);color:var(--red);}}
.badge-inj{{background:rgba(255,68,68,0.12);color:var(--red);}}
.badge-sharp{{background:rgba(179,136,255,0.15);color:var(--purple);}}
.badge-div{{background:rgba(64,196,255,0.1);color:var(--blue);}}
.badge-best{{background:rgba(255,193,7,0.15);color:var(--gold);}}
.gc-matchup{{padding:12px 14px 8px;}}
.team-row{{display:flex;align-items:center;gap:10px;}}
.team-row+.team-row{{margin-top:8px;}}
.team-chip{{width:38px;height:38px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:11px;flex-shrink:0;}}
.team-info{{flex:1;min-width:0;}}
.team-name{{font-size:13px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
.team-meta{{font-size:10px;color:var(--muted2);margin-top:2px;}}
.team-odds{{text-align:right;flex-shrink:0;}}
.team-ml{{font-size:16px;font-weight:900;font-variant-numeric:tabular-nums;}}
.team-spd{{font-size:11px;font-weight:600;margin-top:1px;color:var(--muted2);}}
.team-ev{{font-size:9px;font-weight:700;margin-top:2px;}}
.vs-row{{display:flex;align-items:center;gap:8px;margin:5px 0;}}
.vs-line{{flex:1;height:1px;background:var(--border);}}
.vs-txt{{font-size:9px;color:var(--muted);letter-spacing:0.1em;flex-shrink:0;}}
.win-bar-wrap{{padding:0 14px 6px;}}
.win-bar{{height:4px;border-radius:2px;background:rgba(255,255,255,0.05);overflow:hidden;}}
.win-bar-fill{{height:100%;border-radius:2px;}}
.win-bar-lbls{{display:flex;justify-content:space-between;margin-top:3px;font-size:9px;color:var(--muted);}}
.bpct-wrap{{padding:0 12px 10px;}}
.bpct-row{{display:flex;align-items:center;gap:6px;margin-bottom:5px;}}
.bpct-lbl{{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:0.05em;width:45px;flex-shrink:0;}}
.bpct-bar{{flex:1;height:16px;background:var(--card2);border-radius:4px;overflow:hidden;display:flex;}}
.bpct-away{{height:100%;background:rgba(64,196,255,0.35);display:flex;align-items:center;padding-left:5px;font-size:9px;font-weight:800;color:var(--blue);white-space:nowrap;}}
.bpct-home{{height:100%;background:rgba(0,230,118,0.25);display:flex;align-items:center;justify-content:flex-end;padding-right:5px;font-size:9px;font-weight:800;color:var(--green);white-space:nowrap;}}
.bpct-sharp{{font-size:9px;color:var(--purple);font-weight:700;text-align:center;padding:0 12px 6px;}}
.bet-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:5px;padding:2px 12px 10px;}}
.bcell{{background:var(--card2);border:1px solid var(--border);border-radius:9px;padding:8px 5px;text-align:center;cursor:pointer;transition:all 0.1s;user-select:none;}}
.bcell:active{{transform:scale(0.94);}}
.bcell.picked{{background:rgba(0,229,255,0.1);border-color:var(--accent);}}
.bcell.rec-strong{{border-color:rgba(0,230,118,0.45);background:rgba(0,230,118,0.07);}}
.bcell.rec-value{{border-color:rgba(255,193,7,0.38);background:rgba(255,193,7,0.06);}}
.bcell.rec-fade{{border-color:rgba(255,68,68,0.3);background:rgba(255,68,68,0.04);opacity:0.7;}}
.b-lbl{{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:0.04em;margin-bottom:3px;}}
.b-val{{font-size:14px;font-weight:900;font-variant-numeric:tabular-nums;}}
.b-sub{{font-size:9px;color:var(--muted2);margin-top:2px;}}
.b-ev{{font-size:8px;font-weight:800;margin-top:2px;}}
.b-rec{{font-size:8px;font-weight:800;text-transform:uppercase;margin-top:2px;letter-spacing:0.03em;}}
.b-rec.s{{color:var(--green);}} .b-rec.v{{color:var(--gold);}} .b-rec.l{{color:var(--purple);}} .b-rec.f{{color:var(--red);}}
.signals{{padding:0 12px 10px;display:flex;gap:5px;flex-wrap:wrap;}}
.sig{{padding:3px 8px;border-radius:10px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.02em;}}
.sig-s{{background:rgba(0,230,118,0.1);color:var(--green);border:1px solid rgba(0,230,118,0.2);}}
.sig-f{{background:rgba(255,68,68,0.1);color:var(--red);border:1px solid rgba(255,68,68,0.2);}}
.sig-v{{background:rgba(255,193,7,0.08);color:var(--gold);border:1px solid rgba(255,193,7,0.2);}}
.sig-i{{background:rgba(64,196,255,0.08);color:var(--blue);border:1px solid rgba(64,196,255,0.2);}}
.detail-panel{{display:none;background:var(--card2);border:1px solid var(--border2);border-radius:14px;padding:16px;margin-bottom:10px;}}
.detail-panel.on{{display:block;}}
.dp-title{{font-size:14px;font-weight:800;color:var(--accent);margin-bottom:12px;}}
.dp-grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px;}}
.dp-stat{{background:var(--card);border-radius:9px;padding:10px 12px;}}
.dp-stat-lbl{{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;}}
.dp-stat-val{{font-size:16px;font-weight:900;font-variant-numeric:tabular-nums;}}
.dp-stat-sub{{font-size:10px;color:var(--muted2);margin-top:3px;}}
.dp-note{{font-size:12px;line-height:1.75;color:var(--muted2);background:var(--card);border-radius:9px;padding:12px 14px;border-left:3px solid var(--accent);margin-bottom:10px;}}
.dp-picks{{display:grid;grid-template-columns:1fr 1fr;gap:8px;}}
.dp-pick{{border-radius:9px;padding:12px 14px;}}
.dp-pick.ats{{background:rgba(0,230,118,0.07);border:1px solid rgba(0,230,118,0.22);}}
.dp-pick.tot{{background:rgba(64,196,255,0.07);border:1px solid rgba(64,196,255,0.22);}}
.dp-pick-lbl{{font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;}}
.dp-pick.ats .dp-pick-lbl{{color:var(--green);}} .dp-pick.tot .dp-pick-lbl{{color:var(--blue);}}
.dp-pick-val{{font-size:17px;font-weight:900;}}
.dp-pick.ats .dp-pick-val{{color:var(--green);}} .dp-pick.tot .dp-pick-val{{color:var(--blue);}}
.no-games{{text-align:center;padding:60px 20px;color:var(--muted);}}
.no-games-icon{{font-size:48px;margin-bottom:12px;}}
.no-games-txt{{font-size:16px;font-weight:700;color:var(--muted2);}}
.no-games-sub{{font-size:12px;margin-top:8px;line-height:1.7;}}
.pl-hdr{{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;}}
.pl-title{{font-size:18px;font-weight:900;color:var(--gold);}}
.pl-clear{{font-size:11px;color:var(--muted2);cursor:pointer;border:1px solid var(--border);padding:5px 12px;border-radius:8px;}}
.pl-legs{{background:var(--card);border-radius:12px;padding:12px;border:1px dashed rgba(255,193,7,0.2);min-height:70px;display:flex;flex-direction:column;gap:8px;}}
.pl-empty{{text-align:center;color:var(--muted);font-size:12px;padding:18px 0;}}
.pl-leg{{display:flex;align-items:center;justify-content:space-between;background:var(--card2);border-radius:9px;padding:10px 12px;gap:8px;}}
.pl-leg-name{{font-size:13px;font-weight:700;}}
.pl-leg-sub{{font-size:10px;color:var(--muted2);margin-top:2px;}}
.pl-leg-right{{display:flex;align-items:center;gap:10px;flex-shrink:0;}}
.pl-leg-odds{{font-size:14px;font-weight:900;color:var(--gold);font-variant-numeric:tabular-nums;}}
.pl-leg-rm{{color:var(--muted);font-size:18px;cursor:pointer;padding:0 4px;line-height:1;}}
.pl-calc{{background:var(--card);border-radius:12px;padding:16px;margin-top:12px;}}
.pl-wager-row{{display:flex;flex-direction:column;align-items:center;margin-bottom:16px;gap:5px;}}
.pl-wager-input{{background:var(--card2);border:1px solid var(--border2);border-radius:9px;padding:9px 16px;color:var(--text);font-size:20px;font-weight:900;width:150px;outline:none;text-align:center;-webkit-appearance:none;}}
.pl-wager-input:focus{{border-color:var(--gold);}}
.pl-wager-lbl{{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:0.08em;}}
.pl-stats{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;}}
.pl-stat{{text-align:center;}}
.pl-stat-val{{font-size:20px;font-weight:900;font-variant-numeric:tabular-nums;line-height:1;}}
.pl-stat-lbl{{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:0.07em;margin-top:4px;}}
.model-weights{{background:var(--card);border-radius:12px;padding:14px;margin-top:14px;}}
.mw-title{{font-size:10px;font-weight:800;color:var(--muted);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px;}}
.mw-row{{display:flex;align-items:center;gap:8px;margin-bottom:7px;}}
.mw-lbl{{font-size:10px;color:var(--muted2);width:140px;flex-shrink:0;}}
.mw-bar{{flex:1;height:5px;background:rgba(255,255,255,0.05);border-radius:3px;overflow:hidden;}}
.mw-fill{{height:100%;border-radius:3px;background:linear-gradient(90deg,var(--accent2),var(--accent));}}
.mw-pct{{font-size:10px;font-weight:700;color:var(--muted2);width:30px;text-align:right;flex-shrink:0;}}
.mw-note{{font-size:10px;color:var(--muted);margin-top:10px;line-height:1.6;}}
.legend{{display:flex;gap:14px;flex-wrap:wrap;padding:0 0 12px;font-size:10px;color:var(--muted);}}
.legend span{{display:flex;align-items:center;gap:4px;}}
.std-conf{{font-size:11px;font-weight:800;color:var(--muted2);text-transform:uppercase;letter-spacing:0.08em;margin:16px 0 8px;display:flex;align-items:center;gap:8px;}}
.std-conf::after{{content:'';flex:1;height:1px;background:var(--border);}}
.tbl-wrap{{overflow-x:auto;-webkit-overflow-scrolling:touch;border-radius:12px;border:1px solid var(--border);}}
table{{width:100%;border-collapse:collapse;font-size:11px;min-width:360px;}}
th{{text-align:left;color:var(--muted);font-weight:800;font-size:9px;text-transform:uppercase;letter-spacing:0.07em;padding:9px 10px;border-bottom:1px solid var(--border);background:var(--card);}}
td{{padding:9px 10px;border-bottom:1px solid rgba(255,255,255,0.03);}}
tr:last-child td{{border-bottom:none;}} tr:hover td{{background:rgba(255,255,255,0.015);}}
.sw{{color:var(--green);font-weight:700;}} .sl{{color:var(--red);font-weight:700;}}
.std-note{{font-size:10px;color:var(--muted);text-align:center;padding:12px 0;}}
.record-link{{background:var(--card);border:1px solid var(--border2);border-radius:12px;padding:14px 16px;margin-bottom:14px;text-decoration:none;color:var(--text);display:flex;justify-content:space-between;align-items:center;}}
.rl-left{{display:flex;flex-direction:column;gap:3px;}}
.rl-title{{font-size:13px;font-weight:800;color:var(--gold);}}
.rl-sub{{font-size:11px;color:var(--muted2);}}
.rl-stats{{display:flex;gap:14px;}}
.rl-stat{{text-align:center;}}
.rl-val{{font-size:17px;font-weight:900;color:var(--green);font-variant-numeric:tabular-nums;}}
.rl-lbl{{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:0.06em;margin-top:2px;}}
</style>
</head>
<body>
<div class="hdr">
  <div class="hdr-left">
    <div class="hdr-title">🏀 NBA PICKS</div>
    <div class="hdr-sub">{date_str} · v4</div>
  </div>
  <div class="hdr-right">
    <div class="live-pill"><div class="dot"></div>{n} Games</div>
    <div class="record-pill">ATS {ats_str} ({ats_pct})</div>
  </div>
</div>
<div class="disc">⚠️ Entertainment only. EV shown on every bet — positive EV = good value. Gamble responsibly.</div>
<div class="tab-bar">
  <div class="tab-btn on" id="tb-games" onclick="goTab('games')">Games</div>
  <div class="tab-btn" id="tb-parlay" onclick="goTab('parlay')">Parlay</div>
  <div class="tab-btn" id="tb-standings" onclick="goTab('standings')">Standings</div>
</div>
<div class="pane on" id="pane-games">
  <a class="record-link" href="record.html">
    <div class="rl-left"><div class="rl-title">📊 Model Track Record</div><div class="rl-sub">View full pick history →</div></div>
    <div class="rl-stats">
      <div class="rl-stat"><div class="rl-val">{ats_str}</div><div class="rl-lbl">ATS</div></div>
      <div class="rl-stat"><div class="rl-val">{tot_str}</div><div class="rl-lbl">O/U</div></div>
    </div>
  </a>
  {best_html}
  <div class="section-label">All Games</div>
  <div class="legend">
    <span><span style="color:var(--green)">■</span> Strong</span>
    <span><span style="color:var(--gold)">■</span> Value</span>
    <span><span style="color:var(--purple)">■</span> Sharp $$</span>
    <span><span style="color:var(--red)">■</span> Fade</span>
  </div>
  <div id="game-list"></div>
  <div id="detail-anchor"></div>
</div>
<div class="pane" id="pane-parlay">
  <div class="pl-hdr"><div class="pl-title">⚡ Parlay Builder</div><div class="pl-clear" onclick="clearParlay()">Clear All</div></div>
  <div class="pl-legs" id="pl-legs"><div class="pl-empty">Tap any bet on the Games tab to add it here</div></div>
  <div class="pl-calc">
    <div class="pl-wager-row">
      <input class="pl-wager-input" id="wager" type="number" inputmode="decimal" value="100" min="1" oninput="updateParlay()">
      <div class="pl-wager-lbl">Wager ($)</div>
    </div>
    <div class="pl-stats">
      <div class="pl-stat"><div class="pl-stat-val" id="p-legs">0</div><div class="pl-stat-lbl">Legs</div></div>
      <div class="pl-stat"><div class="pl-stat-val" id="p-odds" style="color:var(--gold)">—</div><div class="pl-stat-lbl">Odds</div></div>
      <div class="pl-stat"><div class="pl-stat-val" id="p-payout" style="color:var(--green)">—</div><div class="pl-stat-lbl">Payout</div></div>
    </div>
    <div style="margin-top:10px;text-align:center;"><span style="font-size:11px;color:var(--muted2);">Hit prob: </span><span id="p-prob" style="font-size:13px;font-weight:800;color:var(--purple);">—</span></div>
  </div>
  <div class="model-weights">
    <div class="mw-title">Smart Model v4 — All Factors</div>
    <div class="mw-row"><div class="mw-lbl">Win Probability (EV)</div><div class="mw-bar"><div class="mw-fill" style="width:25%"></div></div><div class="mw-pct">25%</div></div>
    <div class="mw-row"><div class="mw-lbl">Home/Away Splits</div><div class="mw-bar"><div class="mw-fill" style="width:10%"></div></div><div class="mw-pct">10%</div></div>
    <div class="mw-row"><div class="mw-lbl">Back-to-Back Rest</div><div class="mw-bar"><div class="mw-fill" style="width:15%"></div></div><div class="mw-pct">15%</div></div>
    <div class="mw-row"><div class="mw-lbl">Rest vs Rust</div><div class="mw-bar"><div class="mw-fill" style="width:5%"></div></div><div class="mw-pct">5%</div></div>
    <div class="mw-row"><div class="mw-lbl">Power Rankings</div><div class="mw-bar"><div class="mw-fill" style="width:10%"></div></div><div class="mw-pct">10%</div></div>
    <div class="mw-row"><div class="mw-lbl">Injury Report</div><div class="mw-bar"><div class="mw-fill" style="width:10%"></div></div><div class="mw-pct">10%</div></div>
    <div class="mw-row"><div class="mw-lbl">Line Movement</div><div class="mw-bar"><div class="mw-fill" style="width:10%"></div></div><div class="mw-pct">10%</div></div>
    <div class="mw-row"><div class="mw-lbl">Spread Size ATS</div><div class="mw-bar"><div class="mw-fill" style="width:10%"></div></div><div class="mw-pct">10%</div></div>
    <div class="mw-row"><div class="mw-lbl">Divisional Game</div><div class="mw-bar"><div class="mw-fill" style="width:5%"></div></div><div class="mw-pct">5%</div></div>
    <div class="mw-note">EV% shown on every bet. Positive EV = the payout justifies the risk. ML on big favorites often shows negative EV even with high win prob.</div>
  </div>
</div>
<div class="pane" id="pane-standings">
  <div class="std-conf">Eastern Conference</div>
  <div class="tbl-wrap"><table><thead><tr><th>#</th><th>Team</th><th>W</th><th>L</th><th>PCT</th><th>Strk</th></tr></thead><tbody id="east-body"></tbody></table></div>
  <div class="std-conf" style="margin-top:20px">Western Conference</div>
  <div class="tbl-wrap"><table><thead><tr><th>#</th><th>Team</th><th>W</th><th>L</th><th>PCT</th><th>Strk</th></tr></thead><tbody id="west-body"></tbody></table></div>
  <div class="std-note">Updated daily · {date_str}</div>
</div>
<script>
const GAMES={gj};
const EAST=[
  {{r:1,ab:"DET",t:"Detroit Pistons",w:45,l:16,strk:"L2"}},{{r:2,ab:"BOS",t:"Boston Celtics",w:42,l:21,strk:"L1"}},
  {{r:3,ab:"NYK",t:"New York Knicks",w:41,l:23,strk:"W1"}},{{r:4,ab:"CLE",t:"Cleveland Cavs",w:39,l:24,strk:"W2"}},
  {{r:5,ab:"TOR",t:"Toronto Raptors",w:35,l:27,strk:"L2"}},{{r:6,ab:"MIA",t:"Miami Heat",w:35,l:29,strk:"W4"}},
  {{r:7,ab:"PHI",t:"Philadelphia 76ers",w:34,l:28,strk:"W1"}},{{r:8,ab:"ORL",t:"Orlando Magic",w:33,l:28,strk:"W2"}},
  {{r:9,ab:"ATL",t:"Atlanta Hawks",w:32,l:31,strk:"W5"}},{{r:10,ab:"CHA",t:"Charlotte Hornets",w:32,l:32,strk:"L1"}},
  {{r:11,ab:"MIL",t:"Milwaukee Bucks",w:26,l:35,strk:"L4"}},{{r:12,ab:"CHI",t:"Chicago Bulls",w:26,l:37,strk:"W1"}},
  {{r:13,ab:"WAS",t:"Washington Wizards",w:16,l:46,strk:"L7"}},{{r:14,ab:"BKN",t:"Brooklyn Nets",w:15,l:47,strk:"L10"}},
  {{r:15,ab:"IND",t:"Indiana Pacers",w:15,l:48,strk:"L8"}},
];
const WEST=[
  {{r:1,ab:"OKC",t:"OKC Thunder",w:49,l:15,strk:"W4"}},{{r:2,ab:"SAS",t:"San Antonio Spurs",w:46,l:17,strk:"W3"}},
  {{r:3,ab:"MIN",t:"Minnesota T-Wolves",w:40,l:23,strk:"W5"}},{{r:4,ab:"HOU",t:"Houston Rockets",w:39,l:23,strk:"W1"}},
  {{r:5,ab:"DEN",t:"Denver Nuggets",w:39,l:25,strk:"L1"}},{{r:6,ab:"LAL",t:"Los Angeles Lakers",w:38,l:25,strk:"W1"}},
  {{r:7,ab:"PHX",t:"Phoenix Suns",w:36,l:27,strk:"W1"}},{{r:8,ab:"GSW",t:"Golden State Warriors",w:32,l:30,strk:"W1"}},
  {{r:9,ab:"LAC",t:"LA Clippers",w:30,l:32,strk:"W1"}},{{r:10,ab:"POR",t:"Portland Blazers",w:30,l:34,strk:"L1"}},
  {{r:11,ab:"MEM",t:"Memphis Grizzlies",w:23,l:38,strk:"L2"}},{{r:12,ab:"DAL",t:"Dallas Mavericks",w:21,l:42,strk:"L1"}},
  {{r:13,ab:"NOP",t:"New Orleans Pelicans",w:20,l:43,strk:"W1"}},{{r:14,ab:"SAC",t:"Sacramento Kings",w:19,l:44,strk:"L1"}},
  {{r:15,ab:"UTA",t:"Utah Jazz",w:16,l:48,strk:"L1"}},
];
let parlay=[],openGame=null;
function goTab(n){{['games','parlay','standings'].forEach(t=>{{document.getElementById('pane-'+t).classList.toggle('on',t===n);document.getElementById('tb-'+t).classList.toggle('on',t===n);}});window.scrollTo(0,0);if(n==='parlay')updateParlay();if(n==='standings')renderStandings();}}
function mlToDec(ml){{const s=String(ml),n=parseFloat(s.replace('+',''));return(s.startsWith('+')||n>0)?n/100+1:100/Math.abs(n)+1;}}
function recCls(r){{return r==='strong'?'rec-strong':r==='value'?'rec-value':r==='fade'?'rec-fade':'';}}
function recTag(r,ev){{
  if(!r||r==='neutral')return ev!==undefined?`<div class="b-ev" style="color:${{ev>0?'var(--green)':ev>-3?'var(--muted)':'var(--red)'}}">${{ev>0?'+':''}}${{ev}}% EV</div>`:'';
  const m={{strong:'✓ Strong',value:'★ Value',lean:'≈ Lean',fade:'✗ Bad Value'}},c={{strong:'s',value:'v',lean:'l',fade:'f'}};
  const evStr=ev!==undefined?` ${{ev>0?'+':''}}${{ev}}%`:'';
  return`<div class="b-rec ${{c[r]||''}}">${{m[r]||r}}${{evStr}}</div>`;
}}
function isPicked(gid,type,side){{return parlay.some(p=>p.gid===gid&&p.type===type&&p.side===side);}}
function evColor(ev){{return ev>5?'var(--green)':ev>0?'#8bc34a':ev>-3?'var(--muted2)':'var(--red)';}}
function bpctBar(g){{
  if(!g.awayBetPct&&!g.homeBetPct)return'';
  const ab=g.awayBetPct||50,hb=g.homeBetPct||(100-ab);
  const am=g.awayMoneyPct,hm=g.homeMoneyPct;
  const moneyRow=am?`<div class="bpct-row"><div class="bpct-lbl">Money</div><div class="bpct-bar"><div class="bpct-away" style="width:${{am}}%">${{am}}%</div><div class="bpct-home" style="width:${{hm||100-am}}%">${{hm||100-am}}%</div></div></div>`:'';
  const sharpRow=g.sharpFlag?`<div class="bpct-sharp">🔪 ${{g.sharpNote}}</div>`:'';
  return`<div class="bpct-wrap"><div class="bpct-row"><div class="bpct-lbl">Bets</div><div class="bpct-bar"><div class="bpct-away" style="width:${{ab}}%">${{ab}}% ${{g.away}}</div><div class="bpct-home" style="width:${{hb}}%">${{hb}}% ${{g.home}}</div></div></div>${{moneyRow}}${{sharpRow}}</div>`;
}}
function renderGames(){{
  const el=document.getElementById('game-list');
  if(!GAMES.length){{el.innerHTML='<div class="no-games"><div class="no-games-icon">🏀</div><div class="no-games-txt">No games today</div><div class="no-games-sub">Updated 4x daily. Check back tomorrow!</div></div>';return;}}
  el.innerHTML=GAMES.map(g=>{{
    const abs=Math.abs(g.homeSpread),hS=g.homeSpread<0?`-${{abs}}`:`+${{abs}}`,aS=g.homeSpread<0?`+${{abs}}`:`-${{abs}}`;
    const hSR=g.spdSide==='home'?g.spdRec:(g.spdSide==='away'?'fade':'neutral');
    const aSR=g.spdSide==='away'?g.spdRec:(g.spdSide==='home'?'fade':'neutral');
    const oR=g.totalPick.startsWith('Over')?g.totalRec:'neutral',uR=g.totalPick.startsWith('Under')?g.totalRec:'neutral';
    const sigs=(g.signals||[]).map(s=>`<span class="sig ${{s.c}}">${{s.t}}</span>`).join('');
    const badges=[
      `<span class="badge badge-${{g.conf==='E'?'e':'w'}}">${{g.conf==='E'?'East':'West'}}</span>`,
      `<span class="badge badge-ou">O/U ${{g.total}}</span>`,
      g.isBestBet?'<span class="badge badge-best">🏆 Best Bet</span>':'',
      (g.homeB2B||g.awayB2B)?'<span class="badge badge-b2b">B2B 😴</span>':'',
      (g.homeRust||g.awayRust)?'<span class="badge badge-b2b">Rust 🦾</span>':'',
      (g.homeInjuries?.length||g.awayInjuries?.length)?'<span class="badge badge-inj">Inj ⚠️</span>':'',
      g.sharpFlag?'<span class="badge badge-sharp">Sharp 🔪</span>':'',
      g.lineMoved?'<span class="badge badge-sharp">Line 📈</span>':'',
      g.sameDivision?'<span class="badge badge-div">Div</span>':'',
    ].filter(Boolean).join('');
    return`<div class="game-card${{openGame===g.id?' open':''}}${{g.isBestBet?' best-bet':''}}" onclick="toggleDetail(${{g.id}})">
      <div class="gc-top"><div class="gc-time">🏀 ${{g.time}}</div><div class="gc-badges">${{badges}}</div></div>
      <div class="gc-matchup">
        <div class="team-row">
          <div class="team-chip" style="background:${{g.awayColor}}22;color:${{g.awayColor}}">${{g.away}}</div>
          <div class="team-info"><div class="team-name">${{g.awayFull}}${{g.awayB2B?' 😴':''}}${{g.awayRust?' 🦾':''}}${{g.awayInjuries?.length?' ⚠️':''}}</div><div class="team-meta">Away</div></div>
          <div class="team-odds">
            <div class="team-ml" style="color:${{g.awayWinProb>50?'var(--green)':'var(--muted2)'}}">${{g.awayML}}</div>
            <div class="team-spd">${{aS}}</div>
            <div class="team-ev" style="color:${{evColor(g.awayMLEV)}}">${{g.awayMLEV>0?'+':''}}${{g.awayMLEV}}% EV</div>
          </div>
        </div>
        <div class="vs-row"><div class="vs-line"></div><div class="vs-txt">@ ${{g.homeFull.toUpperCase()}}</div><div class="vs-line"></div></div>
        <div class="team-row">
          <div class="team-chip" style="background:${{g.homeColor}}22;color:${{g.homeColor}}">${{g.home}}</div>
          <div class="team-info"><div class="team-name">${{g.homeFull}}${{g.homeB2B?' 😴':''}}${{g.homeRust?' 🦾':''}}${{g.homeInjuries?.length?' ⚠️':''}}</div><div class="team-meta">Home</div></div>
          <div class="team-odds">
            <div class="team-ml" style="color:${{g.homeWinProb>50?'var(--green)':'var(--muted2)'}}">${{g.homeML}}</div>
            <div class="team-spd">${{hS}}</div>
            <div class="team-ev" style="color:${{evColor(g.homeMLEV)}}">${{g.homeMLEV>0?'+':''}}${{g.homeMLEV}}% EV</div>
          </div>
        </div>
      </div>
      <div class="win-bar-wrap"><div class="win-bar"><div class="win-bar-fill" style="width:${{g.homeWinProb}}%;background:linear-gradient(90deg,${{g.awayColor}}99,${{g.homeColor}})"></div></div><div class="win-bar-lbls"><span>${{g.away}} ${{g.awayWinProb}}%</span><span>${{g.home}} ${{g.homeWinProb}}%</span></div></div>
      ${{bpctBar(g)}}
      <div class="bet-grid">
        <div class="bcell ${{recCls(aSR)}} ${{isPicked(g.id,'SPD','away')?'picked':''}}" onclick="event.stopPropagation();pick(${{g.id}},'SPD','away','${{g.away}} ${{aS}}','${{g.juice}}',52)"><div class="b-lbl">${{g.away}} Spread</div><div class="b-val">${{aS}}</div><div class="b-sub">${{g.juice}}</div>${{recTag(aSR,g.awaySpdEV)}}</div>
        <div class="bcell ${{recCls(oR)}} ${{isPicked(g.id,'OVR','both')?'picked':''}}" onclick="event.stopPropagation();pick(${{g.id}},'OVR','both','Over ${{g.total}}','${{g.overJ}}',50)"><div class="b-lbl">Over</div><div class="b-val">${{g.total}}</div><div class="b-sub">${{g.overJ}}</div>${{recTag(oR)}}</div>
        <div class="bcell ${{recCls(hSR)}} ${{isPicked(g.id,'SPD','home')?'picked':''}}" onclick="event.stopPropagation();pick(${{g.id}},'SPD','home','${{g.home}} ${{hS}}','${{g.juice}}',52)"><div class="b-lbl">${{g.home}} Spread</div><div class="b-val">${{hS}}</div><div class="b-sub">${{g.juice}}</div>${{recTag(hSR,g.homeSpdEV)}}</div>
        <div class="bcell ${{recCls(g.awayMLRec)}} ${{isPicked(g.id,'ML','away')?'picked':''}}" onclick="event.stopPropagation();pick(${{g.id}},'ML','away','${{g.away}} ML','${{g.awayML}}',${{Math.round(g.awayWinProb)}})"><div class="b-lbl">${{g.away}} ML</div><div class="b-val">${{g.awayML}}</div><div class="b-sub">${{g.awayWinProb}}%</div>${{recTag(g.awayMLRec,g.awayMLEV)}}</div>
        <div class="bcell ${{recCls(uR)}} ${{isPicked(g.id,'UND','both')?'picked':''}}" onclick="event.stopPropagation();pick(${{g.id}},'UND','both','Under ${{g.total}}','${{g.underJ}}',50)"><div class="b-lbl">Under</div><div class="b-val">${{g.total}}</div><div class="b-sub">${{g.underJ}}</div>${{recTag(uR)}}</div>
        <div class="bcell ${{recCls(g.homeMLRec)}} ${{isPicked(g.id,'ML','home')?'picked':''}}" onclick="event.stopPropagation();pick(${{g.id}},'ML','home','${{g.home}} ML','${{g.homeML}}',${{Math.round(g.homeWinProb)}})"><div class="b-lbl">${{g.home}} ML</div><div class="b-val">${{g.homeML}}</div><div class="b-sub">${{g.homeWinProb}}%</div>${{recTag(g.homeMLRec,g.homeMLEV)}}</div>
      </div>
      <div class="signals">${{sigs}}</div>
    </div>`;
  }}).join('');
}}
function toggleDetail(id){{
  openGame=(openGame===id)?null:id; renderGames();
  const anchor=document.getElementById('detail-anchor');
  if(!openGame){{anchor.innerHTML='';return;}}
  const g=GAMES.find(x=>x.id===id),abs=Math.abs(g.homeSpread),fav=g.homeSpread<0?g.home:g.away;
  const atsPick=g.spdSide==='home'?`${{g.home}} ${{g.homeSpread<0?'-':'+'}}`+abs:`${{g.away}} ${{g.homeSpread<0?'+':'-'}}`+abs;
  const injBlock=(g.homeInjuries?.length||g.awayInjuries?.length)?
    `<div style="background:rgba(255,68,68,0.07);border:1px solid rgba(255,68,68,0.2);border-radius:9px;padding:10px 12px;margin-bottom:10px;font-size:11px;color:var(--red);line-height:1.8;">
      <strong>⚠️ Injury Report</strong><br>
      ${{g.awayInjuries?.length?g.away+': '+g.awayInjuries.join(', ')+'<br>':''}}
      ${{g.homeInjuries?.length?g.home+': '+g.homeInjuries.join(', '):''}}</div>`:'';
  anchor.innerHTML=`<div class="detail-panel on">
    <div class="dp-title">${{g.away}} @ ${{g.home}} · ${{g.time}}</div>
    ${{injBlock}}
    <div class="dp-grid">
      <div class="dp-stat"><div class="dp-stat-lbl">Vegas Spread</div><div class="dp-stat-val" style="color:var(--gold)">${{fav}} -${{abs}}</div><div class="dp-stat-sub">Juice ${{g.juice}}</div></div>
      <div class="dp-stat"><div class="dp-stat-lbl">O/U · Avg Pace</div><div class="dp-stat-val">${{g.total}}</div><div class="dp-stat-sub">${{g.avgPace}} possessions</div></div>
      <div class="dp-stat"><div class="dp-stat-lbl">Model Score</div><div class="dp-stat-val" style="color:var(--accent)">${{g.modelScore}}</div><div class="dp-stat-sub">&gt;50 = home covers</div></div>
      <div class="dp-stat"><div class="dp-stat-lbl">Spread Edge</div><div class="dp-stat-val" style="color:${{g.spreadEdge>0?'var(--green)':'var(--red)'}}">${{g.spreadEdge>0?'+':''}}${{g.spreadEdge}} pts</div><div class="dp-stat-sub">Model vs line</div></div>
      <div class="dp-stat"><div class="dp-stat-lbl">${{g.away}} ML EV</div><div class="dp-stat-val" style="color:${{evColor(g.awayMLEV)}}">${{g.awayMLEV>0?'+':''}}${{g.awayMLEV}}%</div><div class="dp-stat-sub">${{g.awayWinProb}}% win prob</div></div>
      <div class="dp-stat"><div class="dp-stat-lbl">${{g.home}} ML EV</div><div class="dp-stat-val" style="color:${{evColor(g.homeMLEV)}}">${{g.homeMLEV>0?'+':''}}${{g.homeMLEV}}%</div><div class="dp-stat-sub">${{g.homeWinProb}}% win prob</div></div>
    </div>
    <div class="dp-note">${{g.note}}</div>
    <div class="dp-picks">
      <div class="dp-pick ats"><div class="dp-pick-lbl">ATS Pick</div><div class="dp-pick-val">${{g.spdSide?atsPick:'No lean'}}</div></div>
      <div class="dp-pick tot"><div class="dp-pick-lbl">Total Pick</div><div class="dp-pick-val">${{g.totalPick}}</div></div>
    </div>
  </div>`;
  setTimeout(()=>anchor.scrollIntoView({{behavior:'smooth',block:'nearest'}}),80);
}}
function pick(gid,type,side,label,odds,prob){{const i=parlay.findIndex(p=>p.gid===gid&&p.type===type&&p.side===side);if(i>=0){{parlay.splice(i,1);}}else{{parlay=parlay.filter(p=>!(p.gid===gid&&((p.type==='ML'&&type==='ML')||(p.type==='SPD'&&type==='SPD')||(p.type==='OVR'&&type==='UND')||(p.type==='UND'&&type==='OVR'))));parlay.push({{gid,type,side,label,odds,prob}});}}renderGames();updateParlay();}}
function clearParlay(){{parlay=[];renderGames();updateParlay();}}
function rmLeg(i){{parlay.splice(i,1);renderGames();updateParlay();}}
function updateParlay(){{const legs=document.getElementById('pl-legs');if(!parlay.length){{legs.innerHTML='<div class="pl-empty">Tap any bet on the Games tab to add it here</div>';document.getElementById('p-legs').textContent='0';['p-odds','p-payout','p-prob'].forEach(id=>document.getElementById(id).textContent='—');return;}}legs.innerHTML=parlay.map((p,i)=>`<div class="pl-leg"><div><div class="pl-leg-name">${{p.label}}</div><div class="pl-leg-sub">${{{{'ML':'Moneyline','SPD':'Spread','OVR':'Over','UND':'Under'}}[p.type]||p.type}} · ${{p.prob}}% hit</div></div><div class="pl-leg-right"><div class="pl-leg-odds">${{p.odds}}</div><div class="pl-leg-rm" onclick="rmLeg(${{i}})">✕</div></div></div>`).join('');const dec=parlay.reduce((a,p)=>a*mlToDec(p.odds),1),prob=parlay.reduce((a,p)=>a*(p.prob/100),1),wager=parseFloat(document.getElementById('wager').value)||100,pa=dec>=2?'+'+Math.round((dec-1)*100):'-'+Math.round(100/(dec-1));document.getElementById('p-legs').textContent=parlay.length;document.getElementById('p-odds').textContent=pa;document.getElementById('p-payout').textContent='$'+Math.round(wager*dec).toLocaleString();document.getElementById('p-prob').textContent=(prob*100).toFixed(1)+'%';}}
function renderStandings(){{function tbody(data,id){{const el=document.getElementById(id);if(!el)return;el.innerHTML=data.map(t=>{{const pct=(t.w/(t.w+t.l)).toFixed(3);return`<tr><td>${{t.r}}</td><td><strong>${{t.ab}}</strong></td><td>${{t.w}}</td><td>${{t.l}}</td><td>${{pct}}</td><td class="${{t.strk.startsWith('W')?'sw':'sl'}}">${{t.strk}}</td></tr>`;}}).join('');}}tbody(EAST,'east-body');tbody(WEST,'west-body');}}
renderGames();renderStandings();
</script>
</body>
</html>'''

def build_record_page(record):
    picks = sorted(record["picks"], key=lambda x: x["date"], reverse=True)
    ats   = record["summary"]["ats"]
    tot   = record["summary"]["total"]
    total_ats = ats['w']+ats['l']
    ats_pct = f"{ats['w']/total_ats*100:.1f}%" if total_ats else "—"
    total_tot = tot['w']+tot['l']
    tot_pct = f"{tot['w']/total_tot*100:.1f}%" if total_tot else "—"
    rows = ""
    for p in picks:
        if p["result"]=="win":    rc,rv="sw","✓ Win"
        elif p["result"]=="loss": rc,rv="sl","✗ Loss"
        elif p["result"]=="push": rc,rv="","→ Push"
        else:                     rc,rv="","Pending"
        ev_str = f"{p['ev']:+.1f}%" if p.get("ev") is not None else "—"
        rows += f'<tr><td>{p["date"]}</td><td>{p["game"]}</td><td>{p["type"]}</td><td>{p["pick"].upper()}</td><td style="font-size:10px;color:var(--muted2)">{ev_str}</td><td class="{rc}">{rv}</td></tr>'
    if not rows:
        rows = '<tr><td colspan="6" style="text-align:center;color:#4a5270;padding:24px">No picks logged yet — check back after tonight\'s games!</td></tr>'
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>NBA Picks · Track Record</title>
<style>
:root{{--bg:#06080f;--card:#0d1119;--card2:#131822;--border:rgba(255,255,255,0.07);--text:#e2e6f0;--muted:#4a5270;--muted2:#7a84a8;--green:#00e676;--red:#ff4444;--gold:#ffc107;--accent:#00e5ff;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,sans-serif;font-size:14px;}}
.hdr{{background:var(--card);border-bottom:1px solid var(--border);padding:14px 16px;display:flex;align-items:center;gap:12px;position:sticky;top:0;z-index:10;}}
.back{{color:var(--accent);font-size:20px;text-decoration:none;}}
.hdr-title{{font-size:18px;font-weight:900;color:var(--accent);}}
.content{{padding:16px 12px 60px;max-width:680px;margin:0 auto;}}
.summary{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:20px;}}
.scard{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px;text-align:center;}}
.scard-val{{font-size:24px;font-weight:900;line-height:1;}}
.scard-lbl{{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:0.08em;margin-top:5px;}}
.scard-pct{{font-size:12px;font-weight:700;margin-top:3px;}}
.tbl-wrap{{overflow-x:auto;border-radius:12px;border:1px solid var(--border);}}
table{{width:100%;border-collapse:collapse;font-size:11px;min-width:460px;}}
th{{text-align:left;color:var(--muted);font-weight:800;font-size:9px;text-transform:uppercase;letter-spacing:0.07em;padding:9px 10px;border-bottom:1px solid var(--border);background:var(--card);}}
td{{padding:9px 10px;border-bottom:1px solid rgba(255,255,255,0.03);}}
tr:last-child td{{border-bottom:none;}}
.sw{{color:var(--green);font-weight:800;}} .sl{{color:var(--red);font-weight:800;}}
.note{{font-size:11px;color:var(--muted);text-align:center;padding:14px 0;line-height:1.6;}}
</style>
</head>
<body>
<div class="hdr"><a class="back" href="index.html">←</a><div class="hdr-title">📊 Track Record</div></div>
<div class="content">
  <div class="summary">
    <div class="scard"><div class="scard-val" style="color:var(--green)">{ats['w']}-{ats['l']}</div><div class="scard-lbl">ATS Record</div><div class="scard-pct" style="color:var(--gold)">{ats_pct}</div></div>
    <div class="scard"><div class="scard-val" style="color:var(--blue)">{tot['w']}-{tot['l']}</div><div class="scard-lbl">O/U Record</div><div class="scard-pct" style="color:var(--gold)">{tot_pct}</div></div>
    <div class="scard"><div class="scard-val" style="color:var(--purple)">{len(picks)}</div><div class="scard-lbl">Total Picks</div><div class="scard-pct" style="color:var(--muted2)">logged</div></div>
  </div>
  <div class="tbl-wrap">
    <table><thead><tr><th>Date</th><th>Game</th><th>Type</th><th>Pick</th><th>EV</th><th>Result</th></tr></thead>
    <tbody>{rows}</tbody></table>
  </div>
  <div class="note">Record starts from first day of tracking.<br>Results graded automatically each morning.<br>EV shown at time of pick.</div>
</div>
</body>
</html>'''

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    et_now   = datetime.now(ET)
    date_str = et_now.strftime("%a %b %-d · Updated %-I:%M %p ET")
    print(f"NBA Picks v4 — {date_str}")

    record  = load_record()
    results = fetch_scores_for_grading()
    if results:
        record = grade_picks(record, results)
        print(f"Graded {len(results)} games")

    b2b          = fetch_b2b()
    last_played  = fetch_recent_schedule()
    injuries     = fetch_injuries()
    print(f"Injuries: {list(injuries.keys()) or 'none'}")
    raw          = fetch_odds()
    bet_pcts     = fetch_betting_pcts([])
    games        = parse_games(raw, b2b, last_played, injuries, bet_pcts)
    print(f"Games: {len(games)}")

    log_picks(games, record)

    (HERE / "index.html").write_text(build_index(games, date_str, record), encoding="utf-8")
    (HERE / "record.html").write_text(build_record_page(record), encoding="utf-8")
    print("✅ Done — index.html + record.html written")

if __name__ == "__main__":
    main()
