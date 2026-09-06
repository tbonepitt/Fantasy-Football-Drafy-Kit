# 2026 Offline Fantasy Draft Assistant

A single-file, offline fantasy football draft board built for a 12-team Yahoo league with custom scoring. It provides team-first recommendations, live player tracking, mock picks, bye-week warnings, local persistence, and Google Sheets-compatible exports.

The application does not require a server, account, database, package manager, or internet connection during the draft.

## Features

- Team-first Top 10 recommendations for every upcoming pick
- A 40-player live board on the main screen
- Fast **Mine**, **Gone**, and **Queue** actions
- Search and position filters
- 12-team snake-draft pick tracking
- One-click **Mock My Next Pick** simulation
- Persistent **My Team** display and roster-slot tracking
- Official 2026 NFL bye weeks and same-position conflict warnings
- Separate ranking and user-data storage
- Ranking JSON import with rollback
- Google Sheets-compatible CSV export
- Full JSON backup and local undo
- No kickers and no required tight end

## League Configuration

The recommendation engine is customized for:

- **Teams:** 12
- **Roster:** QB, 2 WR, 2 RB, 3 W/R/T flex, DEF, 4 bench, 1 IR
- **No required TE**
- **No kicker**
- **Passing:** 0.25 per completion, 1 point per 20 yards, 6-point touchdowns, -2 interceptions, -1 per quarterback sack, +5 at 300 yards, +8 at 400 yards
- **Rushing:** 0.5 per attempt, 1 point per 10 yards, +5 at 100 yards, +8 at 200 yards
- **Receiving:** 0.5 PPR, 1 point per 10 yards, +5 at 100 yards, +8 at 200 yards
- **Returns:** 1 point per 10 yards and 6 points per return touchdown
- **Big plays:** +3 for 40-yard passing, rushing, or receiving touchdowns
- **Defense:** Elevated points-allowed and yards-allowed scoring

## Quick Start

### Download Only

Download this file:

```text
outputs/2026_Fantasy_Draft_Day_Board_v3.html
```

Open it in a modern browser. All application code and default rankings are embedded in the HTML file.

### Clone the Repository

```bash
git clone <repository-url>
cd <repository-folder>
```

Then open the application:

```bash
# macOS
open outputs/2026_Fantasy_Draft_Day_Board_v3.html

# Windows PowerShell
start outputs/2026_Fantasy_Draft_Day_Board_v3.html

# Linux
xdg-open outputs/2026_Fantasy_Draft_Day_Board_v3.html
```

No build command is required.

## Using It During a Draft

1. Select your draft position from 1–12.
2. Confirm the current overall pick.
3. Use the team-first Top 10 for your selection.
4. Mark your player **Mine**.
5. Mark every opponent selection **Gone** from the 40-player board or search.
6. Add personal targets to **Queue** when useful.
7. Watch the green **My Team** strip and roster needs update.
8. Use **Undo last action** immediately after a mistake.
9. Export the final results from **All / Export**.

The recommendation order prioritizes:

1. Your roster construction and unfilled starting positions
2. Player value and the likelihood that a player survives to your following pick
3. Bye-week overlap, especially at the same position

A bye conflict is a warning and ranking tiebreaker—not an automatic reason to pass on a much better player.

## Three-Round Pre-Pick Workaround

Some leagues assign or protect the first three rounds before the live portion begins. The current application supports this without a separate mode:

1. Choose your draft position.
2. Search for every pre-picked player.
3. Mark your assigned players **Mine**.
4. Mark all other pre-picked players **Gone**.
5. Set **Current Overall Pick** to `37`, immediately after three 12-team rounds.
6. Continue the live draft normally.

Do not use **Mock My Next Pick** while entering pre-picked players. If the other 33 pre-picked players are not marked **Gone**, the application may recommend players who are already unavailable.

## Mock Drafting

Select a draft position and press **Mock My Next Pick**.

The application will:

1. Simulate opponent selections until your turn.
2. Draft the current **Best for My Team** recommendation.
3. Advance to the next selection.

Press the button repeatedly to simulate a complete draft. One use of **Undo** reverses the entire previous mock step, including its simulated opponent selections.

## Rankings and Sources

The embedded rankings blend:

- FantasyPros half-PPR expert consensus rankings
- RotoWire PPR rankings
- Yahoo average draft position
- ESPN positional rankings
- Custom adjustments for this league's scoring

The application also includes 2026 NFL bye-week data for recommendation warnings. Source links are available inside **All / Export**.

Rankings are a draft aid, not a guarantee. Injuries, depth-chart changes, suspensions, and return roles should be reviewed shortly before the draft.

## Refreshing Rankings

Ranking refresh requires Python 3, internet access, and Beautiful Soup:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install beautifulsoup4
python work/build_blended_rankings.py
```

Windows activation:

```powershell
.venv\Scripts\Activate.ps1
```

The script creates:

```text
work/blended_rankings_2026.json
```

In the application, open **All / Export**, choose **Import rankings JSON**, and select that file. Ranking imports do not replace your team, queue, draft position, current pick, or draft history.

Upstream websites can change their page structure or access rules. If the refresh script fails, inspect each source adapter in `work/build_blended_rankings.py` rather than weakening validation or importing incomplete data.

## Testing

Node.js is required only for the test harness:

```bash
node work/test_v3.cjs
```

The harness validates:

- Complete drafts from positions 1, 6, and 12
- Ten recommendations throughout the draft
- Valid roster construction
- Persistent My Team display
- Main-screen 40-player board behavior
- Mock drafting and grouped undo
- Ranking and user-data isolation
- Bye-week conflict calculations

## Project Structure

```text
.
├── README.md
├── outputs/
│   └── 2026_Fantasy_Draft_Day_Board_v3.html  # Standalone application
└── work/
    ├── build_blended_rankings.py              # Online ranking refresh
    ├── blended_rankings_2026.json             # Importable ranking package
    └── test_v3.cjs                            # Offline behavior tests
```

Files in `work/` support development and validation. The HTML file in `outputs/` is the only file required at the draft.

## Building or Modifying It With Another LLM

Give the LLM these files:

```text
README.md
outputs/2026_Fantasy_Draft_Day_Board_v3.html
work/test_v3.cjs
work/build_blended_rankings.py
```

Use a prompt similar to:

```text
Update this standalone offline fantasy draft assistant.

Read README.md first and preserve its league rules and workflows. Keep the
application as one self-contained HTML file with no CDN, server, login, or
runtime network dependency. Preserve the Mine/Gone/Queue workflow, current
pick tracking, My Team visibility, team-first Top 10, 40-player main board,
mock drafting, bye-week warnings, ranking import, backup, and CSV export.

Do not merge ranking storage with user draft storage. Do not rename existing
localStorage keys unless you also provide a migration. Do not add kickers or
make tight end required. Update work/test_v3.cjs for behavioral changes and
run it before delivering the revised HTML.
```

### Non-Negotiable Architecture Rules

- Keep the deliverable fully usable offline.
- Do not add external JavaScript, CSS, fonts, APIs, or analytics.
- Preserve the existing user-data key: `draftDayV3User`.
- Preserve the ranking key: `draftDayV3Rankings`.
- Keep ranking imports isolated from user draft data.
- Preserve players already drafted by the user when rankings are refreshed.
- Keep **Mine**, **Gone**, and **Queue** available on the main draft screen.
- Keep the Top 10 and All Players recommendation order synchronized.
- Treat TE as an optional flex player and exclude kickers.
- Keep bye conflicts subordinate to roster fit and meaningful player value.
- Run the test harness after every recommendation-engine change.

## Local Data and Backups

Draft data is stored in the browser's local storage. It is specific to the browser, device, and local file location being used.

Before moving the HTML file, changing devices, clearing browser data, or importing major ranking changes, use **Download JSON backup**. Use **Export for Google Sheets** after the draft for a portable CSV copy.

## Distribution Notes

This repository does not currently include a software license. Add an appropriate license before accepting outside contributions or granting reuse rights. Review the terms of third-party ranking sources before publicly redistributing derived ranking data.
