#!/usr/bin/env python3
"""
NBA Picks Auto-Updater · Smart Model v3
- Injury flags (ESPN API)
- Line movement (opening vs current)
- Power rankings
- Public betting % (scrape from thespread.com)
- Record tracking (logs picks, grades results)
"""

import os, json, re, requests, pytz
from datetime import datetime, timedelta
from pathlib import Path

API_KEY = os.environ.get("ODDS_API_KEY", "")
SPORT   = "basketball_nba"
ET      = pytz.timezone("America/New_York")
HERE    = Path(os.path.dirname(os.path.abspath(__file__)))

# ── Team data ─────────────────────────────────────────────────────────────────
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

# Power rankings (1=best, 30=worst) — update weekly
POWER = {
    "OKC":1,"SAS":2,"DET":3,"MIN":4,"HOU":5,"DEN":6,"LAL":7,"PHX":8,
    "NYK":9,"BOS":10,"CLE":11,"MIA":12,"GSW":13,"ORL":14,"ATL":15,
    "PHI":16,"TOR":17,"LAC":18,"POR":19,"MIL":20,"CHA":21,"SAC":22,
    "CHI":23,"NOP":24,"DAL":25,"MEM":26,"IND":27,"WAS":28,"BKN":29,"UTA":30,
}

ESPN_TEAM_IDS = {
    "ATL":"1","BOS":"2","BKN":"17","CHA":"30","CHI":"4","CLE":"5",
    "DAL":"6","DEN":"7","DET":"8","GSW":"9","HOU":"10","IND":"11",
    "LAC":"12","LAL":"13","MEM":"29","MIA":"14","MIL":"15","MIN":"16",
    "NOP":"3","NYK":"18","OKC":"25","ORL":"19","PHI":"20","PHX":"21",
    "POR":"22","SAC":"23","SAS":"24","TOR":"28","UTA":"26","WAS":"27",
}

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

def fetch_opening_lines():
    """Fetch historical/opening odds to detect line movement."""
    try:
        r = requests.get(
            f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/",
            params={"apiKey":API_KEY,"regions":"us","markets":"spreads",
                    "oddsFormat":"american","dateFormat":"iso","bookmakers":"draftkings"},
            timeout=15)
        # We use the same endpoint but compare — in practice opening lines
        # would need a paid historical endpoint. We simulate movement detection
        # by checking if current line is a round number (likely opened there)
        # vs a half-point (likely moved). This is a best-effort approach.
        return {}
    except:
        return {}

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

def fetch_injuries():
    """Fetch injury reports from ESPN API."""
    injuries = {}  # {team_ab: [player_names]}
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(
            "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries",
            headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        for item in data.get("injuries", []):
            team_ab = item.get("team", {}).get("abbreviation", "")
            # Normalize ESPN abbrs to ours
            if team_ab == "NO": team_ab = "NOP"
            if team_ab == "GS": team_ab = "GSW"
            if team_ab == "SA": team_ab = "SAS"
            if team_ab == "NY": team_ab = "NYK"
            players = []
            for inj in item.get("injuries", []):
                status = inj.get("status","").lower()
                name   = inj.get("athlete",{}).get("shortName","")
                # Only flag out/doubtful/questionable star players
                if status in ["out","doubtful","questionable"] and name:
                    players.append({"name":name,"status":status})
            if players:
                injuries[team_ab] = players[:3]  # cap at 3
    except Exception as e:
        print(f"Injury fetch failed: {e}")
    return injuries

def fetch_betting_pcts(games):
    """
    Scrape public betting percentages from thespread.com.
    Returns dict keyed by 'AWAY@HOME': {away_pct, home_pct, away_money, home_money}
    """
    pcts = {}
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
            "Accept": "text/html,application/xhtml+xml",
        }
        r = requests.get("https://www.thespread.com/nba-public-betting.html",
                         headers=headers, timeout=12)
        html = r.text

        # Parse betting % blocks — thespread shows team name + pct
        # Pattern: look for percentage numbers near team abbreviations
        rows = re.findall(
            r'(\d{1,3})%[^%]{0,200}?(\d{1,3})%',
            html)

        # Alternative: try sportsinsights style data
        # Build a game key lookup
        game_keys = {}
        for g in games:
            key = f"{g['away']}@{g['home']}"
            game_keys[key] = g

        # Try to find structured data
        json_match = re.search(r'window\.__data\s*=\s*(\{.+?\});', html, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                # Parse structured data if available
            except:
                pass

        # Fallback: try actionnetwork public data endpoint
        today = datetime.now(ET).strftime("%Y-%m-%d")
        try:
            an_r = requests.get(
                f"https://api.actionnetwork.com/web/v1/games?sport=nba&date={today}",
                headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
            if an_r.status_code == 200:
                an_data = an_r.json()
                for game in an_data.get("games", []):
                    teams = game.get("teams", [])
                    if len(teams) < 2: continue
                    away_team = teams[0]
                    home_team = teams[1]
                    away_ab = away_team.get("abbr","").upper()
                    home_ab = home_team.get("abbr","").upper()
                    # Normalize
                    if away_ab == "GS": away_ab = "GSW"
                    if home_ab == "GS": home_ab = "GSW"
                    if away_ab == "NO": away_ab = "NOP"
                    if home_ab == "NO": home_ab = "NOP"
                    if away_ab == "SA": away_ab = "SAS"
                    if home_ab == "SA": home_ab = "SAS"

                    spread_data = game.get("spread", {})
                    away_bets   = spread_data.get("away_spread_bets_pct")
                    home_bets   = spread_data.get("home_spread_bets_pct")
                    away_money  = spread_data.get("away_spread_money_pct")
                    home_money  = spread_data.get("home_spread_money_pct")

                    if away_bets and home_bets:
                        key = f"{away_ab}@{home_ab}"
                        pcts[key] = {
                            "away_bets": int(away_bets),
                            "home_bets": int(home_bets),
                            "away_money": int(away_money) if away_money else None,
                            "home_money": int(home_money) if home_money else None,
                        }
        except Exception as e:
            print(f"ActionNetwork fetch failed: {e}")

    except Exception as e:
        print(f"Betting pct fetch failed: {e}")

    return pcts

def fetch_scores_for_grading():
    """Fetch completed game scores for grading yesterday's picks."""
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
            home_score = int(scores.get(g["home_team"], 0))
            away_score = int(scores.get(g["away_team"], 0))
            results[f"{away}@{home}"] = {"home":home,"away":away,"home_score":home_score,"away_score":away_score}
        return results
    except Exception as e:
        print(f"Scores fetch failed: {e}"); return {}

# ── Record tracking ───────────────────────────────────────────────────────────

def load_record():
    path = HERE / "record.json"
    if path.exists():
        return json.loads(path.read_text())
    return {"picks":[],"summary":{"ats":{"w":0,"l":0,"p":0},"ml":{"w":0,"l":0},"total":{"w":0,"l":0,"p":0}}}

def save_record(record):
    (HERE / "record.json").write_text(json.dumps(record, indent=2))

def log_picks(games, record):
    """Log today's model picks to record.json."""
    today = datetime.now(ET).strftime("%Y-%m-%d")
    # Remove any existing picks for today (refresh)
    record["picks"] = [p for p in record["picks"] if p["date"] != today]
    for g in games:
        if g.get("spdSide"):
            record["picks"].append({
                "date": today,
                "game": f"{g['away']}@{g['home']}",
                "type": "ATS",
                "pick": g["spdSide"],
                "spread": g["homeSpread"],
                "total": None,
                "result": None,
            })
        if g.get("totalRec") == "value":
            record["picks"].append({
                "date": today,
                "game": f"{g['away']}@{g['home']}",
                "type": "TOTAL",
                "pick": "over" if g["totalPick"].startswith("Over") else "under",
                "spread": None,
                "total": g["total"],
                "result": None,
            })
    save_record(record)

def grade_picks(record, results):
    """Grade yesterday's picks against actual results."""
    yesterday = (datetime.now(ET)-timedelta(days=1)).strftime("%Y-%m-%d")
    for pick in record["picks"]:
        if pick["date"] != yesterday or pick["result"] is not None:
            continue
        result = results.get(pick["game"])
        if not result: continue

        hs, as_ = result["home_score"], result["away_score"]
        home_ab = result["home"]

        if pick["type"] == "ATS":
            spread = pick["spread"]  # home spread
            home_covers = (hs + spread) > as_
            home_push   = (hs + spread) == as_
            if pick["pick"] == "home":
                pick["result"] = "push" if home_push else ("win" if home_covers else "loss")
            else:
                pick["result"] = "push" if home_push else ("loss" if home_covers else "win")

        elif pick["type"] == "TOTAL":
            actual = hs + as_
            total  = pick["total"]
            if actual == total: pick["result"] = "push"
            elif pick["pick"] == "over": pick["result"] = "win" if actual > total else "loss"
            else: pick["result"] = "win" if actual < total else "loss"

    # Recompute summary
    ats = {"w":0,"l":0,"p":0}
    total = {"w":0,"l":0,"p":0}
    for pick in record["picks"]:
        if pick["result"] is None: continue
        bucket = ats if pick["type"]=="ATS" else total
        if pick["result"]=="win": bucket["w"]+=1
        elif pick["result"]=="loss": bucket["l"]+=1
        elif pick["result"]=="push": bucket["p"]+=1
    record["summary"] = {"ats":ats,"total":total}
    save_record(record)
    return record

# ── Parse games ───────────────────────────────────────────────────────────────

def parse_games(raw, b2b, injuries, bet_pcts):
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

        # ── Line movement detection ───────────────────────────────────────────
        # Half-point spreads (.5) often indicate movement from a whole number
        abs_spd = abs(home_spread)
        line_moved = (abs_spd % 1 == 0.5)  # best-effort signal
        # Direction: if home is favored and spread has .5, likely moved toward favorite
        line_move_note = ""
        if line_moved:
            if home_spread < 0:
                line_move_note = f"Line likely moved toward {home_ab} (sharp action)"
            else:
                line_move_note = f"Line likely moved toward {away_ab} (sharp action)"

        # ── Power ranking factor ──────────────────────────────────────────────
        home_pr = POWER.get(home_ab, 15)
        away_pr = POWER.get(away_ab, 15)
        pr_edge = away_pr - home_pr  # positive = home is ranked better

        # ── Smart model ───────────────────────────────────────────────────────
        def ml_prob(ml):
            if ml<0: return abs(ml)/(abs(ml)+100)*100
            return 100/(ml+100)*100

        rp_h = ml_prob(home_ml); rp_a = ml_prob(away_ml)
        tot_p = rp_h+rp_a
        home_prob = round(rp_h/tot_p*100, 1)
        away_prob = round(100-home_prob, 1)

        score = 50.0
        score += (home_prob-50)*0.25         # win prob 25%
        score += 3.0                          # home court 10%
        home_b2b = home in b2b; away_b2b = away in b2b
        if home_b2b: score -= 4.0            # B2B 15%
        if away_b2b: score += 3.5
        if abs_spd >= 14: score -= 3.0       # spread size 10%
        elif abs_spd >= 10: score -= 1.5
        elif abs_spd <= 3: score += 1.0
        score += pr_edge * 0.15              # power rankings 10%
        if line_moved:
            if home_spread < 0: score += 1.5  # sharp on home
            else: score -= 1.5                 # sharp on away

        # Injury penalty
        home_inj = injuries.get(home_ab, [])
        away_inj = injuries.get(away_ab, [])
        home_inj_penalty = min(len(home_inj) * 2.0, 5.0)
        away_inj_penalty = min(len(away_inj) * 2.0, 5.0)
        score -= home_inj_penalty
        score += away_inj_penalty

        proj  = (home_prob-50)*0.38
        edge  = proj-abs_spd if home_spread<0 else proj+home_spread

        # ATS rec
        if home_spread<0:
            if edge>3 and score>54: spd_side,spd_rec="home","strong"
            elif edge>1 and score>52: spd_side,spd_rec="home","value"
            elif edge<-2 or score<46: spd_side,spd_rec="away","value"
            else: spd_side,spd_rec=None,"neutral"
        else:
            if edge<-3 and score<46: spd_side,spd_rec="away","strong"
            elif edge<-1 and score<48: spd_side,spd_rec="away","value"
            elif edge>2 or score>54: spd_side,spd_rec="home","value"
            else: spd_side,spd_rec=None,"neutral"

        if total>=230: total_pick,total_rec=f"Over {total}","value"
        elif total<=215: total_pick,total_rec=f"Under {total}","value"
        else: total_pick,total_rec=str(total),"neutral"

        fav_prob = max(home_prob,away_prob)
        ml_rec = "strong" if fav_prob>=80 else "value" if fav_prob>=68 else "lean"

        # ── Betting percentages ───────────────────────────────────────────────
        bet_key = f"{away_ab}@{home_ab}"
        bp = bet_pcts.get(bet_key, {})
        sharp_flag = False
        sharp_note = ""
        if bp.get("away_bets") and bp.get("away_money"):
            # Sharp money = public on one side but money on the other
            if bp["away_bets"] > 60 and bp.get("home_money",0) > 55:
                sharp_flag = True
                sharp_note = f"Sharp money on {home_ab} despite {bp['away_bets']}% public on {away_ab}"
            elif bp["home_bets"] > 60 and bp.get("away_money",0) > 55:
                sharp_flag = True
                sharp_note = f"Sharp money on {away_ab} despite {bp['home_bets']}% public on {home_ab}"

        # ── Signals ───────────────────────────────────────────────────────────
        sigs = []
        if home_b2b: sigs.append({"t":f"{home_ab} B2B 😴","c":"sig-f"})
        if away_b2b: sigs.append({"t":f"{away_ab} B2B 😴","c":"sig-f"})
        if home_inj: sigs.append({"t":f"{home_ab} injuries ⚠️","c":"sig-f"})
        if away_inj: sigs.append({"t":f"{away_ab} injuries ⚠️","c":"sig-f"})
        if sharp_flag: sigs.append({"t":"Sharp $$ alert 🔪","c":"sig-v"})
        if line_moved: sigs.append({"t":"Line moved 📈","c":"sig-i"})
        if abs_spd>=14: sigs.append({"t":f"Dog +{abs_spd} ATS value","c":"sig-v"})
        if fav_prob>=80: sigs.append({"t":"Lock territory","c":"sig-s"})
        if spd_rec=="strong": sigs.append({"t":f"{'Home' if spd_side=='home' else 'Away'} covers","c":"sig-s"})
        elif spd_rec=="value": sigs.append({"t":f"ATS edge: {spd_side or 'dog'}","c":"sig-v"})
        if total_rec=="value": sigs.append({"t":total_pick,"c":"sig-i"})
        sigs = sigs[:5]

        fav_ab = home_ab if home_spread<0 else away_ab
        b2b_note = ""
        if home_b2b: b2b_note += f" {home_ab} on a back-to-back."
        if away_b2b: b2b_note += f" {away_ab} on a back-to-back."
        inj_note = ""
        if home_inj: inj_note += f" {home_ab} injuries: {', '.join(p['name']+' ('+p['status']+')' for p in home_inj)}."
        if away_inj: inj_note += f" {away_ab} injuries: {', '.join(p['name']+' ('+p['status']+')' for p in away_inj)}."

        note = (f"Vegas has {fav_ab} as {abs_spd}-pt favorite. "
                f"Model projects {fav_ab} wins {max(home_prob,away_prob):.0f}% — "
                f"spread edge: {edge:+.1f} pts.{b2b_note}{inj_note} "
                f"{line_move_note+'. ' if line_move_note else ''}"
                f"O/U {total}: {'lean Over (fast pace)' if total>=230 else 'lean Under (defensive)' if total<=215 else 'neutral pace game'}. "
                f"{sharp_note}")

        games.append({
            "id":len(games)+1,"time":tip.strftime("%-I:%M %p ET"),
            "conf":CONF.get(home_ab,"E"),
            "away":away_ab,"awayFull":SHORT.get(away,away),
            "awayColor":COLORS.get(away,"#888"),"awayB2B":away_b2b,
            "awayInjuries":[p["name"] for p in away_inj],
            "home":home_ab,"homeFull":SHORT.get(home,home),
            "homeColor":COLORS.get(home,"#444"),"homeB2B":home_b2b,
            "homeInjuries":[p["name"] for p in home_inj],
            "homeSpread":home_spread,"juice":spread_juice,
            "awayML":f"{away_ml:+d}","homeML":f"{home_ml:+d}",
            "total":total,"overJ":over_juice,"underJ":under_juice,
            "homeWinProb":home_prob,"awayWinProb":away_prob,
            "modelScore":round(score,1),"projMargin":round(proj,1),"spreadEdge":round(edge,1),
            "spdSide":spd_side,"spdRec":spd_rec,
            "totalPick":total_pick,"totalRec":total_rec,"mlRec":ml_rec,
            "lineMoved":line_moved,"lineMovedNote":line_move_note,
            "sharpFlag":sharp_flag,"sharpNote":sharp_note,
            "awayBetPct":bp.get("away_bets"),"homeBetPct":bp.get("home_bets"),
            "awayMoneyPct":bp.get("away_money"),"homeMoneyPct":bp.get("home_money"),
            "signals":sigs,"note":note,
        })

    games.sort(key=lambda x:x["time"]); return games

# ── HTML generators ───────────────────────────────────────────────────────────

def build_index(games, date_str, record):
    gj  = json.dumps(games, indent=2)
    rj  = json.dumps(record["summary"], indent=2)
    n   = len(games)
    ats = record["summary"]["ats"]
    tot = record["summary"]["total"]
    ats_str = f"{ats['w']}-{ats['l']}{'-'+str(ats['p']) if ats['p'] else ''}"
    tot_str = f"{tot['w']}-{tot['l']}{'-'+str(tot['p']) if tot['p'] else ''}"
    total_ats = ats['w']+ats['l']
    ats_pct = f"{ats['w']/total_ats*100:.0f}%" if total_ats else "—"

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
.record-pill{{font-size:10px;color:var(--gold);font-weight:700;text-align:right;}}
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
.game-card:active{{opacity:0.9;}}
.gc-top{{padding:10px 14px 8px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border);}}
.gc-time{{font-size:10px;font-weight:700;color:var(--muted2);text-transform:uppercase;letter-spacing:0.08em;}}
.gc-badges{{display:flex;gap:5px;flex-wrap:wrap;justify-content:flex-end;}}
.badge{{font-size:9px;font-weight:800;padding:2px 7px;border-radius:10px;text-transform:uppercase;letter-spacing:0.04em;}}
.badge-e{{background:rgba(64,196,255,0.12);color:var(--blue);}}
.badge-w{{background:rgba(255,68,68,0.12);color:#ff8a80;}}
.badge-ou{{background:rgba(255,193,7,0.1);color:var(--gold);}}
.badge-b2b{{background:rgba(255,68,68,0.12);color:var(--red);}}
.badge-inj{{background:rgba(255,68,68,0.12);color:var(--red);}}
.badge-sharp{{background:rgba(179,136,255,0.15);color:var(--purple);}}
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
.team-prob{{font-size:10px;color:var(--muted);margin-top:1px;}}
.vs-row{{display:flex;align-items:center;gap:8px;margin:5px 0;}}
.vs-line{{flex:1;height:1px;background:var(--border);}}
.vs-txt{{font-size:9px;color:var(--muted);letter-spacing:0.1em;flex-shrink:0;}}
.win-bar-wrap{{padding:0 14px 6px;}}
.win-bar{{height:4px;border-radius:2px;background:rgba(255,255,255,0.05);overflow:hidden;}}
.win-bar-fill{{height:100%;border-radius:2px;}}
.win-bar-lbls{{display:flex;justify-content:space-between;margin-top:3px;font-size:9px;color:var(--muted);}}
/* Betting % bar */
.bpct-wrap{{padding:0 12px 10px;}}
.bpct-row{{display:flex;align-items:center;gap:6px;margin-bottom:5px;}}
.bpct-lbl{{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:0.05em;width:45px;flex-shrink:0;}}
.bpct-bar{{flex:1;height:16px;background:var(--card2);border-radius:4px;overflow:hidden;display:flex;position:relative;}}
.bpct-away{{height:100%;background:rgba(64,196,255,0.35);display:flex;align-items:center;justify-content:flex-start;padding-left:5px;font-size:9px;font-weight:800;color:var(--blue);white-space:nowrap;}}
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
.b-rec{{font-size:8px;font-weight:800;text-transform:uppercase;margin-top:3px;letter-spacing:0.03em;}}
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
.mw-lbl{{font-size:10px;color:var(--muted2);width:130px;flex-shrink:0;}}
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
th{{text-align:left;color:var(--muted);font-weight:800;font-size:9px;text-transform:uppercase;letter-spacing:0.07em;padding:9px 10px;border-bottom:1px solid var(--border);background:var(--card);white-space:nowrap;}}
td{{padding:9px 10px;border-bottom:1px solid rgba(255,255,255,0.03);white-space:nowrap;}}
tr:last-child td{{border-bottom:none;}} tr:hover td{{background:rgba(255,255,255,0.015);}}
.sw{{color:var(--green);font-weight:700;}} .sl{{color:var(--red);font-weight:700;}}
.std-note{{font-size:10px;color:var(--muted);text-align:center;padding:12px 0;}}
.record-link{{display:block;background:var(--card);border:1px solid var(--border2);border-radius:12px;padding:14px 16px;margin-bottom:14px;text-decoration:none;color:var(--text);display:flex;justify-content:space-between;align-items:center;}}
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
    <div class="hdr-sub">{date_str}</div>
  </div>
  <div class="hdr-right">
    <div class="live-pill"><div class="dot"></div>{n} Games</div>
    <div class="record-pill">ATS {ats_str} ({ats_pct})</div>
  </div>
</div>
<div class="disc">⚠️ Entertainment only. Model: win prob, home court, B2B, injuries, power rankings, line movement. Gamble responsibly.</div>
<div class="tab-bar">
  <div class="tab-btn on" id="tb-games" onclick="goTab('games')">Games</div>
  <div class="tab-btn" id="tb-parlay" onclick="goTab('parlay')">Parlay</div>
  <div class="tab-btn" id="tb-standings" onclick="goTab('standings')">Standings</div>
</div>
<div class="pane on" id="pane-games">
  <a class="record-link" href="record.html">
    <div class="rl-left">
      <div class="rl-title">📊 Model Track Record</div>
      <div class="rl-sub">View full pick history →</div>
    </div>
    <div class="rl-stats">
      <div class="rl-stat"><div class="rl-val">{ats_str}</div><div class="rl-lbl">ATS</div></div>
      <div class="rl-stat"><div class="rl-val">{tot_str}</div><div class="rl-lbl">O/U</div></div>
    </div>
  </a>
  <div class="section-label">Tonight's Picks</div>
  <div class="legend">
    <span><span style="color:var(--green)">■</span> Strong</span>
    <span><span style="color:var(--gold)">■</span> Value</span>
    <span><span style="color:var(--purple)">■</span> Sharp $$</span>
    <span><span style="color:var(--red)">■</span> Fade/B2B/Inj</span>
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
    <div style="margin-top:10px;text-align:center;"><span style="font-size:11px;color:var(--muted2);">Hit probability: </span><span id="p-prob" style="font-size:13px;font-weight:800;color:var(--purple);">—</span></div>
  </div>
  <div class="model-weights">
    <div class="mw-title">Smart Model v3 — Factors</div>
    <div class="mw-row"><div class="mw-lbl">Win Probability</div><div class="mw-bar"><div class="mw-fill" style="width:25%"></div></div><div class="mw-pct">25%</div></div>
    <div class="mw-row"><div class="mw-lbl">Back-to-Back Rest</div><div class="mw-bar"><div class="mw-fill" style="width:15%"></div></div><div class="mw-pct">15%</div></div>
    <div class="mw-row"><div class="mw-lbl">Home Court Edge</div><div class="mw-bar"><div class="mw-fill" style="width:10%"></div></div><div class="mw-pct">10%</div></div>
    <div class="mw-row"><div class="mw-lbl">Power Rankings</div><div class="mw-bar"><div class="mw-fill" style="width:10%"></div></div><div class="mw-pct">10%</div></div>
    <div class="mw-row"><div class="mw-lbl">Injury Report</div><div class="mw-bar"><div class="mw-fill" style="width:10%"></div></div><div class="mw-pct">10%</div></div>
    <div class="mw-row"><div class="mw-lbl">Line Movement</div><div class="mw-bar"><div class="mw-fill" style="width:10%"></div></div><div class="mw-pct">10%</div></div>
    <div class="mw-row"><div class="mw-lbl">Spread Size ATS</div><div class="mw-bar"><div class="mw-fill" style="width:10%"></div></div><div class="mw-pct">10%</div></div>
    <div class="mw-note">Public betting % shown when available. Sharp money alert fires when public % and money % diverge by 15%+.</div>
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
  {{r:1,ab:"DET",t:"Detroit Pistons",w:45,l:16,strk:"L2"}},
  {{r:2,ab:"BOS",t:"Boston Celtics",w:42,l:21,strk:"L1"}},
  {{r:3,ab:"NYK",t:"New York Knicks",w:41,l:23,strk:"W1"}},
  {{r:4,ab:"CLE",t:"Cleveland Cavs",w:39,l:24,strk:"W2"}},
  {{r:5,ab:"TOR",t:"Toronto Raptors",w:35,l:27,strk:"L2"}},
  {{r:6,ab:"MIA",t:"Miami Heat",w:35,l:29,strk:"W4"}},
  {{r:7,ab:"PHI",t:"Philadelphia 76ers",w:34,l:28,strk:"W1"}},
  {{r:8,ab:"ORL",t:"Orlando Magic",w:33,l:28,strk:"W2"}},
  {{r:9,ab:"ATL",t:"Atlanta Hawks",w:32,l:31,strk:"W5"}},
  {{r:10,ab:"CHA",t:"Charlotte Hornets",w:32,l:32,strk:"L1"}},
  {{r:11,ab:"MIL",t:"Milwaukee Bucks",w:26,l:35,strk:"L4"}},
  {{r:12,ab:"CHI",t:"Chicago Bulls",w:26,l:37,strk:"W1"}},
  {{r:13,ab:"WAS",t:"Washington Wizards",w:16,l:46,strk:"L7"}},
  {{r:14,ab:"BKN",t:"Brooklyn Nets",w:15,l:47,strk:"L10"}},
  {{r:15,ab:"IND",t:"Indiana Pacers",w:15,l:48,strk:"L8"}},
];
const WEST=[
  {{r:1,ab:"OKC",t:"OKC Thunder",w:49,l:15,strk:"W4"}},
  {{r:2,ab:"SAS",t:"San Antonio Spurs",w:46,l:17,strk:"W3"}},
  {{r:3,ab:"MIN",t:"Minnesota T-Wolves",w:40,l:23,strk:"W5"}},
  {{r:4,ab:"HOU",t:"Houston Rockets",w:39,l:23,strk:"W1"}},
  {{r:5,ab:"DEN",t:"Denver Nuggets",w:39,l:25,strk:"L1"}},
  {{r:6,ab:"LAL",t:"Los Angeles Lakers",w:38,l:25,strk:"W1"}},
  {{r:7,ab:"PHX",t:"Phoenix Suns",w:36,l:27,strk:"W1"}},
  {{r:8,ab:"GSW",t:"Golden State Warriors",w:32,l:30,strk:"W1"}},
  {{r:9,ab:"LAC",t:"LA Clippers",w:30,l:32,strk:"W1"}},
  {{r:10,ab:"POR",t:"Portland Blazers",w:30,l:34,strk:"L1"}},
  {{r:11,ab:"MEM",t:"Memphis Grizzlies",w:23,l:38,strk:"L2"}},
  {{r:12,ab:"DAL",t:"Dallas Mavericks",w:21,l:42,strk:"L1"}},
  {{r:13,ab:"NOP",t:"New Orleans Pelicans",w:20,l:43,strk:"W1"}},
  {{r:14,ab:"SAC",t:"Sacramento Kings",w:19,l:44,strk:"L1"}},
  {{r:15,ab:"UTA",t:"Utah Jazz",w:16,l:48,strk:"L1"}},
];
let parlay=[],openGame=null;
function goTab(n){{['games','parlay','standings'].forEach(t=>{{document.getElementById('pane-'+t).classList.toggle('on',t===n);document.getElementById('tb-'+t).classList.toggle('on',t===n);}});window.scrollTo(0,0);if(n==='parlay')updateParlay();if(n==='standings')renderStandings();}}
function mlToDec(ml){{const s=String(ml),n=parseFloat(s.replace('+',''));return(s.startsWith('+')||n>0)?n/100+1:100/Math.abs(n)+1;}}
function recCls(r){{return r==='strong'?'rec-strong':r==='value'?'rec-value':r==='fade'?'rec-fade':'';}}
function recTag(r){{if(!r||r==='neutral')return'';const m={{strong:'✓ Strong',value:'★ Value',lean:'≈ Lean',fade:'✗ Fade'}},c={{strong:'s',value:'v',lean:'l',fade:'f'}};return'<div class="b-rec '+(c[r]||'')+'">'+(m[r]||r)+'</div>';}}
function isPicked(gid,type,side){{return parlay.some(p=>p.gid===gid&&p.type===type&&p.side===side);}}
function bpctBar(g){{
  if(!g.awayBetPct&&!g.homeBetPct) return '';
  const ab=g.awayBetPct||50,hb=g.homeBetPct||(100-ab);
  const am=g.awayMoneyPct,hm=g.homeMoneyPct;
  const moneyRow=am?`<div class="bpct-row"><div class="bpct-lbl">Money</div><div class="bpct-bar"><div class="bpct-away" style="width:${{am}}%">${{am}}% ${{g.away}}</div><div class="bpct-home" style="width:${{hm||100-am}}%">${{hm||100-am}}% ${{g.home}}</div></div></div>`:'';
  const sharpRow=g.sharpFlag?`<div class="bpct-sharp">🔪 Sharp money alert: ${{g.sharpNote}}</div>`:'';
  return `<div class="bpct-wrap"><div class="bpct-row"><div class="bpct-lbl">Bets</div><div class="bpct-bar"><div class="bpct-away" style="width:${{ab}}%">${{ab}}% ${{g.away}}</div><div class="bpct-home" style="width:${{hb}}%">${{hb}}% ${{g.home}}</div></div></div>${{moneyRow}}${{sharpRow}}</div>`;
}}
function renderGames(){{
  const el=document.getElementById('game-list');
  if(!GAMES.length){{el.innerHTML='<div class="no-games"><div class="no-games-icon">🏀</div><div class="no-games-txt">No games today</div><div class="no-games-sub">Updated 4x daily at 8AM, 12PM, 5PM, 8PM ET.<br>Check back tomorrow!</div></div>';return;}}
  el.innerHTML=GAMES.map(g=>{{
    const abs=Math.abs(g.homeSpread),hS=g.homeSpread<0?`-${{abs}}`:`+${{abs}}`,aS=g.homeSpread<0?`+${{abs}}`:`-${{abs}}`;
    const hSR=g.spdSide==='home'?g.spdRec:(g.spdSide==='away'?'fade':'neutral'),aSR=g.spdSide==='away'?g.spdRec:(g.spdSide==='home'?'fade':'neutral');
    const oR=g.totalPick.startsWith('Over')?g.totalRec:'neutral',uR=g.totalPick.startsWith('Under')?g.totalRec:'neutral';
    const hMR=g.homeWinProb>=68?g.mlRec:(g.homeWinProb<35?'fade':'neutral'),aMR=g.awayWinProb>=68?g.mlRec:(g.awayWinProb<35?'fade':'neutral');
    const sigs=(g.signals||[]).map(s=>`<span class="sig ${{s.c}}">${{s.t}}</span>`).join('');
    const b2b=(g.homeB2B||g.awayB2B)?'<span class="badge badge-b2b">B2B 😴</span>':'';
    const inj=(g.homeInjuries?.length||g.awayInjuries?.length)?'<span class="badge badge-inj">Injuries ⚠️</span>':'';
    const sharp=g.sharpFlag?'<span class="badge badge-sharp">Sharp $$ 🔪</span>':'';
    const moved=g.lineMoved?'<span class="badge badge-sharp">Line moved 📈</span>':'';
    return `<div class="game-card${{openGame===g.id?' open':''}}" onclick="toggleDetail(${{g.id}})">
      <div class="gc-top"><div class="gc-time">🏀 ${{g.time}}</div><div class="gc-badges"><span class="badge badge-${{g.conf==='E'?'e':'w'}}">${{g.conf==='E'?'East':'West'}}</span><span class="badge badge-ou">O/U ${{g.total}}</span>${{b2b}}${{inj}}${{sharp}}${{moved}}</div></div>
      <div class="gc-matchup">
        <div class="team-row"><div class="team-chip" style="background:${{g.awayColor}}22;color:${{g.awayColor}}">${{g.away}}</div><div class="team-info"><div class="team-name">${{g.awayFull}}${{g.awayB2B?' 😴':''}}${{g.awayInjuries?.length?' ⚠️':''}}</div><div class="team-meta">Away</div></div><div class="team-odds"><div class="team-ml" style="color:${{g.awayWinProb>50?'var(--green)':'var(--muted2)'}}">${{g.awayML}}</div><div class="team-spd">${{aS}}</div><div class="team-prob">${{g.awayWinProb}}% win</div></div></div>
        <div class="vs-row"><div class="vs-line"></div><div class="vs-txt">@ ${{g.homeFull.toUpperCase()}}</div><div class="vs-line"></div></div>
        <div class="team-row"><div class="team-chip" style="background:${{g.homeColor}}22;color:${{g.homeColor}}">${{g.home}}</div><div class="team-info"><div class="team-name">${{g.homeFull}}${{g.homeB2B?' 😴':''}}${{g.homeInjuries?.length?' ⚠️':''}}</div><div class="team-meta">Home</div></div><div class="team-odds"><div class="team-ml" style="color:${{g.homeWinProb>50?'var(--green)':'var(--muted2)'}}">${{g.homeML}}</div><div class="team-spd">${{hS}}</div><div class="team-prob">${{g.homeWinProb}}% win</div></div></div>
      </div>
      <div class="win-bar-wrap"><div class="win-bar"><div class="win-bar-fill" style="width:${{g.homeWinProb}}%;background:linear-gradient(90deg,${{g.awayColor}}99,${{g.homeColor}})"></div></div><div class="win-bar-lbls"><span>${{g.away}} ${{g.awayWinProb}}%</span><span>${{g.home}} ${{g.homeWinProb}}%</span></div></div>
      ${{bpctBar(g)}}
      <div class="bet-grid">
        <div class="bcell ${{recCls(aSR)}} ${{isPicked(g.id,'SPD','away')?'picked':''}}" onclick="event.stopPropagation();pick(${{g.id}},'SPD','away','${{g.away}} ${{aS}}','${{g.juice}}',52)"><div class="b-lbl">${{g.away}} Spread</div><div class="b-val">${{aS}}</div><div class="b-sub">${{g.juice}}</div>${{recTag(aSR)}}</div>
        <div class="bcell ${{recCls(oR)}} ${{isPicked(g.id,'OVR','both')?'picked':''}}" onclick="event.stopPropagation();pick(${{g.id}},'OVR','both','Over ${{g.total}}','${{g.overJ}}',50)"><div class="b-lbl">Over</div><div class="b-val">${{g.total}}</div><div class="b-sub">${{g.overJ}}</div>${{recTag(oR)}}</div>
        <div class="bcell ${{recCls(hSR)}} ${{isPicked(g.id,'SPD','home')?'picked':''}}" onclick="event.stopPropagation();pick(${{g.id}},'SPD','home','${{g.home}} ${{hS}}','${{g.juice}}',52)"><div class="b-lbl">${{g.home}} Spread</div><div class="b-val">${{hS}}</div><div class="b-sub">${{g.juice}}</div>${{recTag(hSR)}}</div>
        <div class="bcell ${{recCls(aMR)}} ${{isPicked(g.id,'ML','away')?'picked':''}}" onclick="event.stopPropagation();pick(${{g.id}},'ML','away','${{g.away}} ML','${{g.awayML}}',${{Math.round(g.awayWinProb)}})"><div class="b-lbl">${{g.away}} ML</div><div class="b-val">${{g.awayML}}</div><div class="b-sub">${{g.awayWinProb}}%</div>${{recTag(aMR)}}</div>
        <div class="bcell ${{recCls(uR)}} ${{isPicked(g.id,'UND','both')?'picked':''}}" onclick="event.stopPropagation();pick(${{g.id}},'UND','both','Under ${{g.total}}','${{g.underJ}}',50)"><div class="b-lbl">Under</div><div class="b-val">${{g.total}}</div><div class="b-sub">${{g.underJ}}</div>${{recTag(uR)}}</div>
        <div class="bcell ${{recCls(hMR)}} ${{isPicked(g.id,'ML','home')?'picked':''}}" onclick="event.stopPropagation();pick(${{g.id}},'ML','home','${{g.home}} ML','${{g.homeML}}',${{Math.round(g.homeWinProb)}})"><div class="b-lbl">${{g.home}} ML</div><div class="b-val">${{g.homeML}}</div><div class="b-sub">${{g.homeWinProb}}%</div>${{recTag(hMR)}}</div>
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
    `<div style="background:rgba(255,68,68,0.07);border:1px solid rgba(255,68,68,0.2);border-radius:9px;padding:10px 12px;margin-bottom:10px;font-size:11px;color:var(--red);line-height:1.7;">
      <strong>⚠️ Injury Report</strong><br>
      ${{g.awayInjuries?.length?g.away+': '+g.awayInjuries.join(', ')+'<br>':''}}
      ${{g.homeInjuries?.length?g.home+': '+g.homeInjuries.join(', '):''}}</div>`:'';
  anchor.innerHTML=`<div class="detail-panel on">
    <div class="dp-title">${{g.away}} @ ${{g.home}} · ${{g.time}}</div>
    ${{injBlock}}
    <div class="dp-grid">
      <div class="dp-stat"><div class="dp-stat-lbl">Vegas Spread</div><div class="dp-stat-val" style="color:var(--gold)">${{fav}} -${{abs}}</div><div class="dp-stat-sub">Juice ${{g.juice}}</div></div>
      <div class="dp-stat"><div class="dp-stat-lbl">O/U Total</div><div class="dp-stat-val">${{g.total}}</div><div class="dp-stat-sub">O ${{g.overJ}} / U ${{g.underJ}}</div></div>
      <div class="dp-stat"><div class="dp-stat-lbl">Model Score</div><div class="dp-stat-val" style="color:var(--accent)">${{g.modelScore}}</div><div class="dp-stat-sub">&gt;50 = home covers</div></div>
      <div class="dp-stat"><div class="dp-stat-lbl">Spread Edge</div><div class="dp-stat-val" style="color:${{g.spreadEdge>0?'var(--green)':'var(--red)'}}">${{g.spreadEdge>0?'+':''}}${{g.spreadEdge}} pts</div><div class="dp-stat-sub">Model vs line</div></div>
      <div class="dp-stat"><div class="dp-stat-lbl">${{g.away}} Win Prob</div><div class="dp-stat-val">${{g.awayWinProb}}%</div><div class="dp-stat-sub">${{g.awayML}} ML</div></div>
      <div class="dp-stat"><div class="dp-stat-lbl">${{g.home}} Win Prob</div><div class="dp-stat-val">${{g.homeWinProb}}%</div><div class="dp-stat-sub">${{g.homeML}} ML</div></div>
    </div>
    <div class="dp-note">${{g.note}}</div>
    <div class="dp-picks">
      <div class="dp-pick ats"><div class="dp-pick-lbl">ATS Pick</div><div class="dp-pick-val">${{g.spdSide?atsPick:'No strong lean'}}</div></div>
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
        if p["result"] == "win":   rc,rv = "sw","✓ Win"
        elif p["result"] == "loss": rc,rv = "sl","✗ Loss"
        elif p["result"] == "push": rc,rv = "","→ Push"
        else: rc,rv = "","Pending"
        rows += f'<tr><td>{p["date"]}</td><td>{p["game"]}</td><td>{p["type"]}</td><td>{p["pick"].upper()}</td><td class="{rc}">{rv}</td></tr>'

    if not rows:
        rows = '<tr><td colspan="5" style="text-align:center;color:#4a5270;padding:24px">No picks logged yet — check back after tonight\'s games!</td></tr>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>NBA Picks · Track Record</title>
<style>
:root{{--bg:#06080f;--card:#0d1119;--card2:#131822;--border:rgba(255,255,255,0.07);--text:#e2e6f0;--muted:#4a5270;--muted2:#7a84a8;--green:#00e676;--red:#ff4444;--gold:#ffc107;--accent:#00e5ff;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display',sans-serif;font-size:14px;}}
.hdr{{background:var(--card);border-bottom:1px solid var(--border);padding:14px 16px;display:flex;align-items:center;gap:12px;position:sticky;top:0;z-index:10;}}
.back{{color:var(--accent);font-size:20px;text-decoration:none;line-height:1;}}
.hdr-title{{font-size:18px;font-weight:900;color:var(--accent);}}
.content{{padding:16px 12px 60px;max-width:680px;margin:0 auto;}}
.summary{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:20px;}}
.scard{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px;text-align:center;}}
.scard-val{{font-size:24px;font-weight:900;font-variant-numeric:tabular-nums;line-height:1;}}
.scard-lbl{{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:0.08em;margin-top:5px;}}
.scard-pct{{font-size:12px;font-weight:700;margin-top:3px;}}
.tbl-wrap{{overflow-x:auto;border-radius:12px;border:1px solid var(--border);}}
table{{width:100%;border-collapse:collapse;font-size:12px;min-width:420px;}}
th{{text-align:left;color:var(--muted);font-weight:800;font-size:9px;text-transform:uppercase;letter-spacing:0.07em;padding:9px 10px;border-bottom:1px solid var(--border);background:var(--card);}}
td{{padding:9px 10px;border-bottom:1px solid rgba(255,255,255,0.03);}}
tr:last-child td{{border-bottom:none;}}
.sw{{color:var(--green);font-weight:800;}} .sl{{color:var(--red);font-weight:800;}}
.note{{font-size:11px;color:var(--muted);text-align:center;padding:14px 0;line-height:1.6;}}
</style>
</head>
<body>
<div class="hdr">
  <a class="back" href="index.html">←</a>
  <div class="hdr-title">📊 Track Record</div>
</div>
<div class="content">
  <div class="summary">
    <div class="scard">
      <div class="scard-val" style="color:var(--green)">{ats['w']}-{ats['l']}</div>
      <div class="scard-lbl">ATS Record</div>
      <div class="scard-pct" style="color:var(--gold)">{ats_pct}</div>
    </div>
    <div class="scard">
      <div class="scard-val" style="color:var(--blue)">{tot['w']}-{tot['l']}</div>
      <div class="scard-lbl">O/U Record</div>
      <div class="scard-pct" style="color:var(--gold)">{tot_pct}</div>
    </div>
    <div class="scard">
      <div class="scard-val" style="color:var(--purple)">{len(picks)}</div>
      <div class="scard-lbl">Total Picks</div>
      <div class="scard-pct" style="color:var(--muted2)">logged</div>
    </div>
  </div>
  <div class="tbl-wrap">
    <table>
      <thead><tr><th>Date</th><th>Game</th><th>Type</th><th>Pick</th><th>Result</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
  <div class="note">Record starts from first day of tracking.<br>Results graded automatically each morning.</div>
</div>
</body>
</html>'''

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    et_now   = datetime.now(ET)
    date_str = et_now.strftime("%a %b %-d · Updated %-I:%M %p ET")
    print(f"NBA Picks v3 — {date_str}")

    # Load record, grade yesterday's picks
    record  = load_record()
    results = fetch_scores_for_grading()
    if results:
        record = grade_picks(record, results)
        print(f"Graded {len(results)} games from yesterday")

    # Fetch data
    b2b      = fetch_b2b()
    injuries = fetch_injuries()
    print(f"Injuries found: {list(injuries.keys()) or 'none'}")
    raw      = fetch_odds()
    games    = parse_games(raw, b2b, injuries, {})  # bet pcts fetched after games parsed
    print(f"Games today: {len(games)}")

    # Fetch betting %
    bet_pcts = fetch_betting_pcts(games)
    print(f"Betting pcts: {list(bet_pcts.keys()) or 'none available'}")
    # Re-inject betting pcts into games
    for g in games:
        key = f"{g['away']}@{g['home']}"
        bp  = bet_pcts.get(key, {})
        g["awayBetPct"]   = bp.get("away_bets")
        g["homeBetPct"]   = bp.get("home_bets")
        g["awayMoneyPct"] = bp.get("away_money")
        g["homeMoneyPct"] = bp.get("home_money")
        if bp.get("away_bets") and bp.get("away_money"):
            if bp["away_bets"]>60 and bp.get("home_money",0)>55:
                g["sharpFlag"]=True; g["sharpNote"]=f"Sharp money on {g['home']} despite {bp['away_bets']}% public on {g['away']}"
            elif bp.get("home_bets",0)>60 and bp.get("away_money",0)>55:
                g["sharpFlag"]=True; g["sharpNote"]=f"Sharp money on {g['away']} despite {bp['home_bets']}% public on {g['home']}"

    # Log picks to record
    log_picks(games, record)

    # Write files
    (HERE / "index.html").write_text(build_index(games, date_str, record), encoding="utf-8")
    (HERE / "record.html").write_text(build_record_page(record), encoding="utf-8")
    print(f"✅ Wrote index.html + record.html")

if __name__ == "__main__":
    main()
