import json
import re
import statistics
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup


USER_AGENT = "Mozilla/5.0"
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "work" / "blended_rankings_2026.json"


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def normalize(name):
    value = name.lower().replace("’", "'")
    value = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", value)
    return re.sub(r"[^a-z0-9]", "", value)


def fantasypros():
    html = fetch("https://www.fantasypros.com/nfl/rankings/half-point-ppr-cheatsheets.php")
    match = re.search(r"var ecrData = (\{.*?\});", html, re.S)
    data = json.loads(match.group(1))
    rows = []
    for player in data["players"]:
        position = player["player_position_id"].replace("DST", "DEF")
        rank = int(player["rank_ecr"])
        if position in {"QB", "RB", "WR", "TE", "DEF"} and rank <= 360:
            rows.append({
                "name": player["player_name"],
                "team": player["player_team_id"],
                "pos": position,
                "rank": rank,
                "pos_rank": player["pos_rank"].replace("DST", "DEF"),
            })
    return rows


def rotowire():
    url = "https://aws-prod-web9.rotowire.com/football/article/final-2026-fantasy-football-cheat-sheet-ppr-leagues-printable-excel-132439"
    html = fetch(url)
    match = re.search(r"const RWCS_PLAYERS = (\[.*?\]);", html, re.S)
    rows = json.loads(match.group(1))
    return [{**row, "pos": row["pos"].replace("DST", "DEF")} for row in rows if row["pos"] != "K"]


def yahoo():
    rows = []
    for page in range(1, 6):
        html = fetch(f"https://fantasyteamadvice.com/nfl/yahoo-adp?page={page}")
        soup = BeautifulSoup(html, "html.parser")
        for row in soup.select("table tbody tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.select("td")]
            if len(cells) < 5:
                continue
            position = cells[3].replace("DST", "DEF")
            if position == "K":
                continue
            team_link = next((a.get("href", "") for a in row.select("a") if re.fullmatch(r"/nfl/teams/[a-z]{2,3}", a.get("href", ""))), "")
            rows.append({
                "name": cells[1],
                "team": team_link.rsplit("/", 1)[-1].upper() if team_link else "",
                "pos": position,
                "rank": int(cells[0]),
                "adp": float(cells[4]),
            })
    return rows


def espn():
    url = "https://www.espn.com/fantasy/football/story/_/id/47513496/2026-fantasy-football-rankings-ppr-mike-clay"
    text = BeautifulSoup(fetch(url), "html.parser").get_text(" ", strip=True)
    sections = [
        ("QB", "Quarterbacks", "Running backs"),
        ("RB", "Running backs", "Wide receivers"),
        ("WR", "Wide receivers", "Tight ends"),
        ("TE", "Tight ends", "Eric Karabell"),
    ]
    rows = []
    for position, start_label, end_label in sections:
        start = text.find(start_label)
        end = text.find(end_label, start + len(start_label))
        if start < 0:
            continue
        block = text[start + len(start_label):end if end > start else None]
        for match in re.finditer(r"(\d+)\.\s+(.+?)\s*,\s*([A-Z]{2,3})(?=\s+\d+\.|$)", block):
            rows.append({"name": match.group(2).strip(), "team": match.group(3), "pos": position, "pos_rank": int(match.group(1))})
    return rows


SPECIAL = {
    "joshallen": (16, "FORMAT QB", "Premium passing plus rushing-attempt scoring"),
    "lamarjackson": (19, "RUSH QB", "Every rush scores before yardage is added"),
    "jaydendaniels": (18, "RUSH QB", "Rushing volume stacks with premium QB scoring"),
    "jalenhurts": (16, "RUSH QB", "Goal-line rushing creates a format advantage"),
    "drakemaye": (12, "DUAL-THREAT QB", "Passing bonuses plus useful rushing volume"),
    "joeburrow": (10, "PASSING BOOST", "Completions, six-point TDs and yardage bonuses"),
    "calebwilliams": (11, "DUAL-THREAT QB", "Mobility adds points in this scoring"),
    "trevorlawrence": (8, "DUAL-THREAT QB", "Rushing attempts supplement passing value"),
    "jaxsondart": (9, "LATE RUSH QB", "Later rushing upside"),
    "bonix": (8, "LATE RUSH QB", "Designed-run floor adds value"),
    "quinshonjudkins": (10, "WORKHORSE TARGET", "Carry volume is paid directly"),
    "camskattebo": (10, "WORKHORSE TARGET", "Early-down and goal-line volume"),
    "jacorycroskeymerritt": (15, "VOLUME TARGET", "Early-down and goal-line opportunity"),
    "buckyirving": (8, "VOLUME TARGET", "Lead-back attempts fit the format"),
    "tonypollard": (10, "VOLUME TARGET", "Early-down attempts create a scoring floor"),
    "chubahubbard": (8, "VOLUME MONITOR", "Featured-runner upside; verify health"),
    "bhayshultuten": (18, "CARRIES + RETURNS", "Carries and return yards both score"),
    "rhamondrestevenson": (10, "EARLY-DOWN VALUE", "Carries and goal-line work are rewarded"),
    "jadarianprice": (10, "EARLY VOLUME", "Lead-back attempts create immediate value"),
    "marvinmims": (55, "OFFENSE + RETURNS", "Offense plus kick and punt returns"),
    "rashidshaheed": (45, "OFFENSE + RETURNS", "Return yards and receiving both count"),
    "chimeredike": (60, "RETURN-YARD TARGET", "Heavy return role plus offensive upside"),
    "parkerwashington": (22, "RETURN + OFFENSE", "Punt returns add a second scoring path"),
    "malikwashington": (35, "RETURN + OFFENSE", "Kick and punt work can add hidden points"),
    "kcconcepcion": (28, "RETURN UPSIDE", "Return opportunity plus offense"),
    "mylesprice": (35, "LATE RETURN DART", "Useful only if the return role is secure"),
    "kenenwangwu": (35, "LATE RETURN DART", "Return specialist with limited offense"),
    "raydavis": (20, "RETURN + HANDCUFF", "Return points plus contingent carries"),
    "keatonmitchell": (20, "EXPLOSIVE DART", "Long-play and possible return upside"),
    "willshipley": (20, "RETURN + HANDCUFF", "Returns plus contingent backfield work"),
}

MONITORS = {
    "rico dowdle", "david montgomery", "woody marks", "jordan mason", "rj harvey",
    "jk dobbins", "treveyon henderson", "kyle monangai", "jeremiyah love",
    "jonathon brooks", "zach charbonnet", "josh jacobs", "jaylen warren",
}


def main():
    fp_rows = fantasypros()
    rw_rows = rotowire()
    yahoo_rows = yahoo()
    espn_rows = espn()

    rw_map = {normalize(row["name"]): row for row in rw_rows}
    yahoo_map = {normalize(row["name"]): row for row in yahoo_rows}
    espn_map = {normalize(row["name"]): row for row in espn_rows}
    fp_by_position = {}
    for row in fp_rows:
        fp_by_position.setdefault(row["pos"], []).append(row)
    for rows in fp_by_position.values():
        rows.sort(key=lambda row: row["rank"])

    players = []
    for fp in fp_rows:
        key = normalize(fp["name"])
        rw = rw_map.get(key)
        yh = yahoo_map.get(key)
        ep = espn_map.get(key)
        source_values = [(fp["rank"], 0.35)]
        if rw:
            source_values.append((int(rw["rank"]), 0.25))
        if yh:
            source_values.append((float(yh["adp"]), 0.25))
        espn_proxy = None
        if ep and ep["pos_rank"] <= len(fp_by_position.get(fp["pos"], [])):
            espn_proxy = fp_by_position[fp["pos"]][ep["pos_rank"] - 1]["rank"]
            source_values.append((espn_proxy, 0.15))
        weight = sum(item[1] for item in source_values)
        base = sum(value * item_weight for value, item_weight in source_values) / weight

        adjustment = 0
        tag = "CONSENSUS"
        why = "Multi-source market baseline"
        if fp["pos"] == "RB":
            adjustment += 5
            tag = "CARRY-SCORING BOOST"
            why = "Every rushing attempt scores 0.5 before yards and touchdowns"
        if fp["pos"] == "TE":
            adjustment -= 14 if base <= 30 else 24
            tag = "OPTIONAL TE"
            why = "No required TE; must beat RB/WR flex options"
        if fp["pos"] == "DEF":
            defense_number = int(re.search(r"\d+", fp["pos_rank"]).group())
            adjustment = base - (124 + min(defense_number, 13) * 2)
            tag = "LATE DEF"
            why = "Elevated defense scoring, but build offense first"
        if key in SPECIAL:
            boost, tag, why = SPECIAL[key]
            adjustment += boost
        monitor = fp["name"].lower().replace(".", "") in MONITORS
        if monitor:
            tag = f"{tag} · MONITOR" if tag != "CONSENSUS" else "ROLE / HEALTH MONITOR"
        league_rank = max(1, base - adjustment)
        players.append({
            "n": fp["name"],
            "p": fp["pos"],
            "t": fp["team"],
            "b": round(base, 1),
            "l": round(league_rank, 1),
            "fp": fp["rank"],
            "rw": int(rw["rank"]) if rw else None,
            "yh": round(float(yh["adp"]), 1) if yh else None,
            "ep": f"{fp['pos']}{ep['pos_rank']}" if ep else None,
            "tag": tag,
            "why": why,
            "monitor": monitor,
        })

    players = [player for player in players if player["p"] != "K"]
    existing = {normalize(player["n"]) for player in players}
    if "marvinmims" not in existing:
        players.append({
            "n": "Marvin Mims Jr.", "p": "WR", "t": "DEN", "b": 255.0, "l": 170.0,
            "fp": None, "rw": None, "yh": None, "ep": None, "tag": "BRIEFING RETURN WATCH",
            "why": "Not in the current source top 360; keep visible only for a confirmed offense-plus-returns role",
            "monitor": True,
        })
    players.sort(key=lambda player: (player["l"], player["b"], player["n"]))
    players = players[:230]
    for index, player in enumerate(players, 1):
        player["rank"] = index
        player["round"] = max(1, min(13, (index + 11) // 12))

    payload = {
        "generated": "2026-09-06",
        "method": "35% FantasyPros half-PPR ECR, 25% RotoWire PPR consensus, 25% Yahoo ADP, 15% ESPN positional ordering; weights normalize when unavailable; then custom-league adjustments.",
        "sources": {
            "fp": "FantasyPros Half-PPR ECR, Sep. 6, 2026",
            "rw": "RotoWire PPR Top 250, Sep. 5, 2026",
            "yh": "Yahoo API-derived ADP mirror, accessed Sep. 6, 2026",
            "ep": "ESPN Mike Clay PPR positional rankings, Sep. 3, 2026",
        },
        "players": players,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    print(f"Wrote {len(players)} players to {OUTPUT}")
    print("Top 20:")
    for player in players[:20]:
        print(f"{player['rank']:>3}. {player['n']:<24} {player['p']:<3} league={player['l']:<5} base={player['b']:<5} {player['tag']}")


if __name__ == "__main__":
    main()
