# Random Franchise — source files

## Project plan

1. Persist data and workflow in SQLite.
2. Enforce run locks, audited wheels, banked moves, and offseason routing in services.
3. Expose ten Streamlit pages; test critical rules and UI flows.

## Complete file list

- `.github/workflows/tests.yml`
- `.gitignore`
- `.streamlit/config.toml`
- `.streamlit/secrets.toml.example`
- `LICENSE`
- `README.md`
- `START_HERE.md`
- `app.py`
- `config/default_settings.json`
- `config/default_wheels.json`
- `data/.gitkeep`
- `docs/ACCEPTANCE.md`
- `docs/ARCHITECTURE.md`
- `docs/VERIFICATION.md`
- `manage_db.py`
- `models/__init__.py`
- `models/domain.py`
- `pages/10_Creator_OBS_View.py`
- `pages/1_Dashboard.py`
- `pages/2_Roster_Manager.py`
- `pages/3_Game_Entry.py`
- `pages/4_Wheel_Room.py`
- `pages/5_Banked_Moves.py`
- `pages/6_Offseason.py`
- `pages/7_Player_Stats.py`
- `pages/8_Franchise_History.py`
- `pages/9_Settings.py`
- `pyproject.toml`
- `repositories/__init__.py`
- `repositories/sqlite.py`
- `requirements-dev.txt`
- `requirements.txt`
- `services/__init__.py`
- `services/backup_service.py`
- `services/challenge_service.py`
- `services/demo.py`
- `services/franchise_service.py`
- `services/franchise_tag_service.py`
- `services/game_engine.py`
- `services/import_export.py`
- `services/offseason_service.py`
- `services/roster_service.py`
- `services/roster_validator.py`
- `services/stat_engine.py`
- `services/wheel_engine.py`
- `tests/conftest.py`
- `tests/test_rules.py`
- `tests/test_ui.py`
- `ui/__init__.py`
- `ui/banked_moves.py`
- `ui/common.py`
- `ui/creator.py`
- `ui/dashboard.py`
- `ui/forms.py`
- `ui/game_entry.py`
- `ui/history.py`
- `ui/offseason.py`
- `ui/player_stats.py`
- `ui/roster.py`
- `ui/settings.py`
- `ui/wheel_room.py`
- `docs/SOURCE_FILES.md` (this generated index)

## File implementations

### random-franchise/.github/workflows/tests.yml

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements-dev.txt
      - run: python -m pytest -q

```

### random-franchise/.gitignore

```text
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
*.db
*.db-*
*.sqlite*
.streamlit/secrets.toml
.env
.DS_Store

```

### random-franchise/.streamlit/config.toml

```toml
[theme]
base = "dark"
primaryColor = "#42E2AE"
backgroundColor = "#0A1421"
secondaryBackgroundColor = "#152638"
textColor = "#F1F5F9"
font = "sans serif"
[server]
headless = true
[client]
showErrorDetails = "full"

```

### random-franchise/.streamlit/secrets.toml.example

```text
# Copy to secrets.toml locally or paste into Streamlit Cloud Secrets.
# Choose your own password. Never commit secrets.toml.
app_password = "replace-with-your-own-private-password"

```

### random-franchise/LICENSE

```text
MIT License

Copyright (c) 2026 Random Franchise contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

```

### random-franchise/README.md

````markdown
# ⚾ Random Franchise

A private Streamlit companion for a custom MLB The Show 26 Diamond Dynasty Events challenge. Manually manage cards, record games and stats, spin auditable wheels, bank acquisitions, and rebuild between entries. It does not connect to the game, scrape card sites, or use copyrighted card art.

**Start here:** [START_HERE.md](START_HERE.md) explains uploading this folder into your existing GitHub repository and selecting the Streamlit deployment fields.

## Included in V1

- Home plus ten pages: Dashboard, Roster Manager, Game Entry, Wheel Room, Banked Moves, Offseason, Player Stats, Franchise History, Settings, and Creator OBS View.
- SQLite persistence, atomic workflows, schema versioning, immutable audits/snapshots, idempotent games and milestone awards.
- Two-loss entries by default: first loss requires Hot Seat, second loss ends entry. Mid-run changes are limited to arrangements of existing active cards.
- Sixteen config-driven wheels, weighted selection, optional animation landing on the saved backend result, nested routing, and dynamic bottom-three DFA targets.
- Three Franchise Tags by default, replacement/decline flow at the cap, temporary protection, creator-confirmed no-hitter/perfect-game tags, quantitative challenges, and manual evidence for situational feats.
- A fictional demo with 9 lineup hitters, 4 bench hitters, 5 starters, 8 relievers, 1 minor leaguer, a tag, a challenge, and an example banked signing.
- Roster CSV/JSON imports/exports, full SQLite backups, and restoration into an empty installation from Home.
- Optional password gate. This is one shared workspace, not a multi-user account system.

## Local setup: Python 3.11 or 3.12

Extract the ZIP and open a terminal **inside the folder containing `app.py`**.

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python manage_db.py init
python -m streamlit run app.py
```

If virtual-environment activation is blocked, use its interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python manage_db.py init
python -m streamlit run app.py
```

Open the localhost URL printed by Streamlit. Choose **Load Demo Franchise**, then **Open franchise dashboard**. The demo begins its first entry at 0–0. SQLite comes with Python. `requirements.txt` contains runtime dependencies; `requirements-dev.txt` adds pytest.

## The run skeleton

1. Create/import a roster or load the demo. Manually verify active cards as Event legal.
2. From Dashboard, validate and start an entry at **0–0**.
3. Enter a game, check participating players, enter stat lines, review, and confirm once.
4. After wins, complete any milestone wheel and its nested branch. Card acquisitions are banked.
5. After the first loss, spin Hot Seat. Apply arrangement consequences with existing cards using Roster Manager and in the game; acknowledge them before continuing.
6. After the second loss, confirm the final record and select MVP. Complete the MVP reward, elimination, and any configured 0–2 Meltdown.
7. Resolve consequences before acquisitions in Banked Moves. Enter qualifying external cards manually with notes. Trades save outgoing and incoming cards atomically.
8. Reconstruct your roster, settle manual challenges, validate, approve, and start the next entry at **0–0**.
9. Download a full backup in Settings after your session.

The workflow is persistent. Session state holds temporary navigation, form inputs, and review drafts only. Reloading does not grant another spin or resubmit a saved game.

## Roster and statistics

Use **Swap two assignments** for starter/bench substitutions and legal position/order swaps. Both destination positions must be legal. Individual arrangement edits can leave an incomplete roster temporarily while you edit, but another game or new run is blocked until assignments are valid.

Default composition: lineup positions `C, 1B, 2B, 3B, SS, LF, CF, RF, DH`; four bench hitters; five starters; eight relievers. Secondary positions are manually entered. Pitchers need SP/RP eligibility for the corresponding role. Two-way pitcher/DH cards await V2.

Hitter PA must account for AB, BB, HBP, and SF; rates derive from cumulative stat lines. Pitcher innings use **outs**, never decimal innings. Four outs display as `1.1` (1⅓ innings). Zero denominators display as zero. Profiles support individual-game, current-entry, and lifetime scopes.

## Settings and wheels

`config/default_settings.json` and `config/default_wheels.json` seed new franchises. Existing franchises keep their own settings/wheels in SQLite. Settings are edited between runs; each run stores its rules snapshot.

Milestones default to 2, 5, 7, 9, and 10 wins. Each threshold grants one award per run; configure further thresholds for additional rewards. `special_wheels=false` removes optional Premium/Tag follow-up wedges but leaves explicitly configured milestone wheels intact.

Event restrictions support team, series, primary position, batting hand, and throwing hand lists, plus manual legal/illegal/unknown status. Unknown/illegal active cards block validation. Dates and notes are stored for reference. The optional OVR check uses the arithmetic average of active cards; verify the actual game's Event formula yourself. Minor cooldown is stored for future use.

The JSON wheel editor validates IDs, weights, active flags, effects, quantities, and follow-up wheels. Bonus nesting is bounded at four levels. If an entire nested branch is impossible, the app records it and permits deferral without replacing its parent spin. Only an impossible child can be retried, and only after eligible choices exist. There is no arbitrary reroll button.

## Tags, challenges, and protection

Permanent tags exclude players from ordinary DFA, demotion, and elimination. At the cap, replace a tag holder or decline the new award in Banked Moves.

No-hitter/perfect-game flags require zero hits allowed and at least nine outs. The creator confirms the complete-game feat occurred. A pitcher earns the tag automatically unless the cap requires a decision.

Automatic survival metrics include hits, HR, RBI, runs, SB, strikeouts, saves, and holds. Tag challenges include next-run hits/HR/RBI/strikeouts/saves/outs. Situational feats require written evidence in offseason. Next-run challenges wait until the next entry starts.

MVP and ordinary temporary protection last through the current offseason elimination cycle, then expire at roster approval. A **Protect Player Next Run** award is banked and persists through the following entry and elimination cycle. Tags remain permanent unless replaced at the cap.

## Audit and corrections

Use **Settings → Administrative corrections** to replace a game's stat lines with a reason. Aggregates recalculate and stable reward keys prevent repeated awards. If a corrected stat invalidates an already granted challenge benefit, its reward is marked `correction_review` in History; V1 preserves the original protection/tag pending a recorded creator decision.

Outcome changes are limited to the **latest game in the current entry before dependent wheels are spun or offseason begins**. Pending milestone jobs can be retracted/recreated safely. Earlier outcome rewinds are rejected; stat edits remain available. Historical wheel audits and snapshots are never rewritten. A snapshot represents the roster when captured, even if a later correction changes derived results.

## Database and recovery

Launch initializes/migrates automatically. The default database is `data/random_franchise.db`; set `RANDOM_FRANCHISE_DB` for a different persistent path.

```bash
python manage_db.py init
```

Stop Streamlit before reset or disk restore. Both require explicit confirmation and retain a pre-change copy if a database existed:

```bash
python manage_db.py reset --confirm
python manage_db.py restore --backup /path/to/random_franchise_backup.db --confirm
```

The Settings backup uses SQLite's backup API and includes all franchises. Roster exports are not full backups. On a fresh hosted instance, use **Home → Restore a full backup** before creating/loading anything; it restores only into an empty installation and does not overwrite existing data.

## GitHub → Streamlit Community Cloud

1. Extract the ZIP. Upload the **contents** of `random-franchise/` to the root of your existing GitHub repository. `app.py` and `requirements.txt` should appear at the top level; preserve the subfolders.
2. Include `.streamlit/config.toml` for the theme and optionally `.github/workflows/tests.yml` for CI. Hidden folders may need adding through Git or GitHub's editor.
3. Commit to `main`, or use your actual branch.
4. At [Streamlit Community Cloud](https://share.streamlit.io/), choose **Create app → Yup, I have an app**. Select your repository, branch, and main file **`app.py`**.
5. Choose **Python 3.12** under Advanced settings. Add a private password in Secrets when the app is accessible to others:

```toml
app_password = "choose-your-own-long-private-password"
```

6. Deploy. The app receives a `streamlit.app` URL. Use host access controls or the password gate for private access. Never commit `.streamlit/secrets.toml` or your password.

**Community Cloud's local filesystem is not permanent franchise storage.** Local SQLite can be lost after platform restarts/redeployments. Download backups after each session; add a durable database adapter before relying on hosted storage as your sole record. A public deployment without access control exposes the shared workspace.

Official documentation: [deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy), [dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies), [SQLite persistence limitations](https://docs.streamlit.io/develop/concepts/connections/connecting-to-data).

## Architecture and future Postgres/Supabase

`pages/` contains thin entrypoints; `ui/` owns forms and rendering; `services/` owns domain rules; `models/domain.py` defines state, typed DTOs, errors, and validation results. `repositories/sqlite.py` implements `get/list/put/delete/transaction` with indexed JSON records and immutable-audit triggers.

Event definitions live in runs/settings; roster assignments live on player records; career stats are derived. This V1 document model avoids duplicated synchronization tables.

To migrate: implement the repository protocol against Postgres JSONB or normalized tables, preserve IDs/indexes/transactions and immutable audits, serialize per-franchise writes with row/advisory locks, migrate all records without changing IDs, then swap the repository factory in `ui/common.py`. Put credentials in host secrets and run the rule tests against the adapter. Add hosted backups and per-user authorization for multi-user use. A hosted adapter is not implemented in V1.

## Verification

```bash
python -m pytest -q
```

Tests cover roster locks/legal swaps, loss routing, banked moves, idempotency, tag caps, nested/dynamic wheels, impossible-child retries, immutable audits, Meltdown, rates/outs, corrections, Event legality, atomic imports, backup restore, a complete offseason, and Streamlit pages/workflow states. See [docs/ACCEPTANCE.md](docs/ACCEPTANCE.md) for manual checks.

## Known V1 boundaries and V2

- Real-card qualification and Hot Seat arrangements are creator-confirmed. The app records instructions/acknowledgements; next-game/rest-of-run durations are manually honored in the game.
- Generic review/fan-choice outcomes need manual roster edits and written notes. Advanced crisis combinations, opponent qualifications, fan votes, full minor-league contracts, two-way cards, deep Event rules, and all proposed challenge variations await V2.
- Worst hitter uses run OPS; worst pitcher uses run ERA, with OVR tie-breaking. Mixed hitter/pitcher ranking uses a simple heuristic.
- No external API integration or scraper. `services/import_export.py` exposes a future roster-provider interface.
- Shared-password access is not user accounts. OBS is read-only and updates on reload; live push overlays, audio, and richer animation await V2.
- Historical outcome rewind, automatic reversal of granted challenge benefits, hosted Postgres/Supabase, drag-and-drop, and a polished wheel editor remain V2 work.

````

### random-franchise/START_HERE.md

````markdown
# Put this app in your existing GitHub repository

You already have a GitHub repository and a Streamlit account. These files are the actual app code.

1. Download and extract `random-franchise.zip`.
2. Open the extracted `random-franchise` folder. You should see `app.py`, `requirements.txt`, `pages`, and `services`.
3. Open your existing repository on GitHub and choose **Add file → Upload files**.
4. Drag the folder's **contents** into the upload area, preserving subfolders. Upload the files, not the ZIP.
5. Enter a commit message such as `Add Random Franchise app` and choose **Commit changes**.
6. Confirm `app.py` and `requirements.txt` are at the repository's top level.
7. Open [Streamlit Community Cloud](https://share.streamlit.io/) and choose **Create app**, then the option for an app you already have.
8. Enter:

| Field | Value |
| --- | --- |
| Repository | Your GitHub username / repository name |
| Branch | `main`, or your actual branch |
| Main file path | `app.py` |
| Advanced settings → Python | `3.12` |

9. For password protection, add `app_password = "your-private-password"` to Streamlit's Secrets field. Choose your own password; keep it out of GitHub.
10. Click **Deploy**. Once the app opens, choose **Load Demo Franchise**, then **Open franchise dashboard**.

If you uploaded the enclosing folder, the main path is `random-franchise/app.py` instead. Uploading the contents directly is simpler.

Some browser uploads omit hidden folders. The app still runs without them, but to keep the theme, add `.streamlit/config.toml` through GitHub's **Add file → Create new file** and paste its contents from the ZIP. Add `.github/workflows/tests.yml` similarly for automated tests.

**Download a full backup from Settings after each session.** App data saves to SQLite, not back to GitHub. Streamlit Cloud's local files can disappear. If the app starts empty, restore your downloaded backup on Home before loading the demo. The README explains durable hosting and local recovery.

Local quick start after activating a Python virtual environment:

```bash
python -m pip install -r requirements-dev.txt
python -m streamlit run app.py
```

````

### random-franchise/app.py

```python
import streamlit as st
from ui.common import context
from services.franchise_service import create_franchise
from services.demo import load_demo
from models.domain import RuleError
from services.backup_service import restore_empty

repo,f=context('Home')
try:
    st.title('⚾ Random Franchise')
    st.markdown('Your Event challenge, one run at a time. Record games, spin wheels, bank upgrades, and rebuild after your second loss.')
    if f:
        st.page_link('pages/1_Dashboard.py',label='Open franchise dashboard',icon='▶️')
    with st.form('create'):
        st.subheader('Create a franchise')
        name=st.text_input('Franchise name')
        event=st.text_input('Event name',value='My Event')
        if st.form_submit_button('Create franchise'):
            fid=create_franchise(repo,name,event)
            st.session_state['selected_franchise']=fid
            st.rerun()
    if st.button('Load Demo Franchise',type='primary'):
        st.session_state['selected_franchise']=load_demo(repo)
        st.rerun()
    if not f:
        with st.expander('Restore a full backup into this empty installation'):
            backup = st.file_uploader('SQLite backup', type=['db'])
            confirmed = st.checkbox('Restore this backup into the empty installation.')
            if backup and confirmed and st.button('Restore complete backup'):
                restore_empty(repo, backup.getvalue())
                st.rerun()
    st.caption('The demo contains fictional cards. Set up or import your real roster manually. Export backups from Settings regularly.')
except RuleError as exc:
    st.error(str(exc))
finally:
    repo.close()

```

### random-franchise/config/default_settings.json

```json
{
  "max_losses": 2,
  "tag_cap": 3,
  "meltdown": "wheel",
  "milestones": {
    "2": "front_office",
    "5": "front_office",
    "7": "protection",
    "9": "premium",
    "10": "premium"
  },
  "bench_size": 4,
  "rotation_size": 5,
  "bullpen_size": 8,
  "ovr_cap": null,
  "minor_cooldown": 1,
  "special_wheels": true,
  "allowed_team": [],
  "disallowed_team": [],
  "allowed_series": [],
  "disallowed_series": [],
  "allowed_primary": [],
  "disallowed_primary": [],
  "allowed_bat": [],
  "disallowed_bat": [],
  "allowed_throw": [],
  "disallowed_throw": [],
  "event_start": null,
  "event_end": null,
  "event_notes": "",
  "reduced_motion": true,
  "sound": false
}

```

### random-franchise/config/default_wheels.json

```json
[
  {
    "wheel_id": "front_office",
    "display_name": "Front Office",
    "wedges": [
      {
        "id": "w0",
        "text": "Upgrade Position",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": "position",
        "eligibility": {},
        "description": "Upgrade Position"
      },
      {
        "id": "w1",
        "text": "Upgrade Worst Statistical Position",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Upgrade Worst Statistical Position"
      },
      {
        "id": "w2",
        "text": "Upgrade Lowest-OVR Position",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Upgrade Lowest-OVR Position"
      },
      {
        "id": "w3",
        "text": "Free Agent Signing",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Free Agent Signing"
      },
      {
        "id": "w4",
        "text": "MLB Team",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": "team",
        "eligibility": {},
        "description": "MLB Team"
      },
      {
        "id": "w5",
        "text": "Division",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": "division",
        "eligibility": {},
        "description": "Division"
      },
      {
        "id": "w6",
        "text": "Card Series",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": "series",
        "eligibility": {},
        "description": "Card Series"
      },
      {
        "id": "w7",
        "text": "Random Card",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Random Card"
      },
      {
        "id": "w8",
        "text": "Random Hitter",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Random Hitter"
      },
      {
        "id": "w9",
        "text": "Random Pitcher",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Random Pitcher"
      },
      {
        "id": "w10",
        "text": "Starting Pitcher Upgrade",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Starting Pitcher Upgrade"
      },
      {
        "id": "w11",
        "text": "Bullpen Upgrade",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Bullpen Upgrade"
      },
      {
        "id": "w12",
        "text": "Bench Upgrade",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Bench Upgrade"
      },
      {
        "id": "w13",
        "text": "Power Bat",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Power Bat"
      },
      {
        "id": "w14",
        "text": "Contact Bat",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Contact Bat"
      },
      {
        "id": "w15",
        "text": "Speedster",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Speedster"
      },
      {
        "id": "w16",
        "text": "Defensive Specialist",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Defensive Specialist"
      },
      {
        "id": "w17",
        "text": "Left-Handed Bat",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Left-Handed Bat"
      },
      {
        "id": "w18",
        "text": "Right-Handed Bat",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Right-Handed Bat"
      },
      {
        "id": "w19",
        "text": "Switch Hitter",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Switch Hitter"
      },
      {
        "id": "w20",
        "text": "Captain-Eligible Player",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Captain-Eligible Player"
      },
      {
        "id": "w21",
        "text": "Legend",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Legend"
      },
      {
        "id": "w22",
        "text": "Current MLB Player",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Current MLB Player"
      },
      {
        "id": "w23",
        "text": "Young Player",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Young Player"
      },
      {
        "id": "w24",
        "text": "Veteran",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Veteran"
      },
      {
        "id": "w25",
        "text": "Same-Player Upgrade",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Same-Player Upgrade"
      },
      {
        "id": "w26",
        "text": "Opponent Raid",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Opponent Raid"
      },
      {
        "id": "w27",
        "text": "Trade Opportunity",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "trade",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true
        },
        "description": "Trade Opportunity"
      },
      {
        "id": "w28",
        "text": "Call-Up Opportunity",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "call_up",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Promote one existing minor-league card during offseason, then validate roster composition."
      },
      {
        "id": "w29",
        "text": "Fan Vote Signing",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "review",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Fan Vote Signing"
      },
      {
        "id": "w30",
        "text": "Budget Signing",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Budget Signing"
      },
      {
        "id": "w31",
        "text": "Position Battle Next Run",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "review",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Position Battle Next Run"
      },
      {
        "id": "w32",
        "text": "Protect Player",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "protect",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {},
        "description": "Protect Player"
      },
      {
        "id": "w33",
        "text": "Franchise Tag Opportunity",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": "tag_hitter",
        "eligibility": {},
        "description": "Franchise Tag Opportunity"
      },
      {
        "id": "w34",
        "text": "Bank Another Spin",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "extra_spin",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {},
        "description": "Bank Another Spin",
        "quantity": 1
      },
      {
        "id": "w35",
        "text": "Double Front Office Spin",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "extra_spin",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {},
        "description": "Double Front Office Spin",
        "quantity": 2
      },
      {
        "id": "w36",
        "text": "Premium Wheel",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": "premium",
        "eligibility": {},
        "description": "Premium Wheel"
      },
      {
        "id": "w37",
        "text": "Jackpot Any Legal Card",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Jackpot Any Legal Card"
      }
    ]
  },
  {
    "wheel_id": "position",
    "display_name": "Position",
    "wedges": [
      {
        "id": "w0",
        "text": "C",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "C"
      },
      {
        "id": "w1",
        "text": "1B",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "1B"
      },
      {
        "id": "w2",
        "text": "2B",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "2B"
      },
      {
        "id": "w3",
        "text": "3B",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "3B"
      },
      {
        "id": "w4",
        "text": "SS",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "SS"
      },
      {
        "id": "w5",
        "text": "LF",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "LF"
      },
      {
        "id": "w6",
        "text": "CF",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "CF"
      },
      {
        "id": "w7",
        "text": "RF",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "RF"
      },
      {
        "id": "w8",
        "text": "DH",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "DH"
      },
      {
        "id": "w9",
        "text": "SP",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "SP"
      },
      {
        "id": "w10",
        "text": "RP",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "RP"
      },
      {
        "id": "w11",
        "text": "Bench",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Bench"
      },
      {
        "id": "w12",
        "text": "Any Infielder",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Any Infielder"
      },
      {
        "id": "w13",
        "text": "Any Outfielder",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Any Outfielder"
      },
      {
        "id": "w14",
        "text": "Any Hitter",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Any Hitter"
      },
      {
        "id": "w15",
        "text": "Any Pitcher",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Any Pitcher"
      },
      {
        "id": "w16",
        "text": "Weakest OVR Position",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Weakest OVR Position"
      },
      {
        "id": "w17",
        "text": "Worst Statistical Position",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Worst Statistical Position"
      },
      {
        "id": "w18",
        "text": "Manager\u2019s Choice",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Manager\u2019s Choice"
      }
    ]
  },
  {
    "wheel_id": "hot_seat",
    "display_name": "First-Loss Hot Seat",
    "wedges": [
      {
        "id": "w0",
        "text": "No Punishment",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {},
        "description": "No Punishment"
      },
      {
        "id": "w1",
        "text": "Lucky Escape",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {},
        "description": "Lucky Escape"
      },
      {
        "id": "w2",
        "text": "Bench Worst Hitter Next Game",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "arrangement",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "kind": "hitter",
          "needs_bench": true
        },
        "description": "Bench Worst Hitter Next Game \u2014 apply using existing active cards, verify legal positions, and confirm before continuing.",
        "selector": "worst"
      },
      {
        "id": "w3",
        "text": "Bench Worst Hitter Rest of Run",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "arrangement",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "kind": "hitter",
          "needs_bench": true
        },
        "description": "Bench Worst Hitter Rest of Run \u2014 apply using existing active cards, verify legal positions, and confirm before continuing.",
        "selector": "worst"
      },
      {
        "id": "w4",
        "text": "Bench Random Starter",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "arrangement",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_bench": true
        },
        "description": "Bench Random Starter \u2014 apply using existing active cards, verify legal positions, and confirm before continuing."
      },
      {
        "id": "w5",
        "text": "Bench Player Must Start",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "arrangement",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_bench": true
        },
        "description": "Bench Player Must Start \u2014 apply using existing active cards, verify legal positions, and confirm before continuing."
      },
      {
        "id": "w6",
        "text": "Lowest-OVR Bench Player Must Start",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "arrangement",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_bench": true
        },
        "description": "Lowest-OVR Bench Player Must Start \u2014 apply using existing active cards, verify legal positions, and confirm before continuing.",
        "selector": "lowest"
      },
      {
        "id": "w7",
        "text": "Random Legal Position Swap",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "arrangement",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {},
        "description": "Random Legal Position Swap \u2014 apply using existing active cards, verify legal positions, and confirm before continuing."
      },
      {
        "id": "w8",
        "text": "Move Worst Hitter to 9th",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "arrangement",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "kind": "hitter"
        },
        "description": "Move Worst Hitter to 9th \u2014 apply using existing active cards, verify legal positions, and confirm before continuing.",
        "selector": "worst"
      },
      {
        "id": "w9",
        "text": "Worst Hitter Leads Off",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "arrangement",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "kind": "hitter"
        },
        "description": "Worst Hitter Leads Off \u2014 apply using existing active cards, verify legal positions, and confirm before continuing.",
        "selector": "worst"
      },
      {
        "id": "w10",
        "text": "Best Hitter Bats 9th",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "arrangement",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "kind": "hitter"
        },
        "description": "Best Hitter Bats 9th \u2014 apply using existing active cards, verify legal positions, and confirm before continuing."
      },
      {
        "id": "w11",
        "text": "Randomize Batting Order",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "arrangement",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {},
        "description": "Randomize Batting Order \u2014 apply using existing active cards, verify legal positions, and confirm before continuing."
      },
      {
        "id": "w12",
        "text": "Change DH",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "arrangement",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {},
        "description": "Change DH \u2014 apply using existing active cards, verify legal positions, and confirm before continuing."
      },
      {
        "id": "w13",
        "text": "Change Closer",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "arrangement",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {},
        "description": "Change Closer \u2014 apply using existing active cards, verify legal positions, and confirm before continuing."
      },
      {
        "id": "w14",
        "text": "Worst Reliever Loses Role",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "arrangement",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "kind": "pitcher"
        },
        "description": "Worst Reliever Loses Role \u2014 apply using existing active cards, verify legal positions, and confirm before continuing.",
        "selector": "worst"
      },
      {
        "id": "w15",
        "text": "Random Reliever Becomes Closer",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "arrangement",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "kind": "pitcher"
        },
        "description": "Random Reliever Becomes Closer \u2014 apply using existing active cards, verify legal positions, and confirm before continuing."
      },
      {
        "id": "w16",
        "text": "Lowest-OVR Reliever Gets Next Save Chance",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "arrangement",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "kind": "pitcher"
        },
        "description": "Lowest-OVR Reliever Gets Next Save Chance \u2014 apply using existing active cards, verify legal positions, and confirm before continuing.",
        "selector": "lowest"
      },
      {
        "id": "w17",
        "text": "Worst Hitter Hot Seat",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "hot_seat",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "hitter"
        },
        "description": "Worst Hitter Hot Seat",
        "selector": "worst"
      },
      {
        "id": "w18",
        "text": "Worst Pitcher Hot Seat",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "hot_seat",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "pitcher"
        },
        "description": "Worst Pitcher Hot Seat",
        "selector": "worst"
      },
      {
        "id": "w19",
        "text": "Random Starter Hot Seat",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "hot_seat",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true
        },
        "description": "Random Starter Hot Seat"
      },
      {
        "id": "w20",
        "text": "Three Players Hot Seat",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "hot_seat",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true
        },
        "description": "Three Players Hot Seat",
        "quantity": 3
      },
      {
        "id": "w21",
        "text": "Lose Temporary Protection",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "unprotect",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_protection": true
        },
        "description": "Lose Temporary Protection"
      },
      {
        "id": "w22",
        "text": "Future DFA Candidate",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "dfa",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true
        },
        "description": "Future DFA Candidate"
      },
      {
        "id": "w23",
        "text": "Future Trade Candidate",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "trade",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true
        },
        "description": "Future Trade Candidate"
      },
      {
        "id": "w24",
        "text": "Future Demotion Candidate",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "demote",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true
        },
        "description": "Future Demotion Candidate"
      },
      {
        "id": "w25",
        "text": "Must Complete Survival Challenge",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": "survival",
        "eligibility": {},
        "description": "Must Complete Survival Challenge"
      },
      {
        "id": "w26",
        "text": "Manager\u2019s Choice",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "arrangement",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {},
        "description": "Manager\u2019s Choice \u2014 apply using existing active cards, verify legal positions, and confirm before continuing."
      },
      {
        "id": "w27",
        "text": "Fan Vote",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "arrangement",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {},
        "description": "Fan Vote \u2014 apply using existing active cards, verify legal positions, and confirm before continuing."
      },
      {
        "id": "w28",
        "text": "Spin Twice",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "extra_spin",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {},
        "description": "Spin Twice",
        "quantity": 2
      }
    ]
  },
  {
    "wheel_id": "survival",
    "display_name": "Survival Challenge",
    "wedges": [
      {
        "id": "w0",
        "text": "Get a hit",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "challenge",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "hitter"
        },
        "description": "Get a hit",
        "metric": "h",
        "threshold": 1,
        "scope": "next_game",
        "reward": "protection"
      },
      {
        "id": "w1",
        "text": "Get 2 hits",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "challenge",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "hitter"
        },
        "description": "Get 2 hits",
        "metric": "h",
        "threshold": 2,
        "scope": "next_game",
        "reward": "protection"
      },
      {
        "id": "w2",
        "text": "Home run",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "challenge",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "hitter"
        },
        "description": "Home run",
        "metric": "hr",
        "threshold": 1,
        "scope": "next_game",
        "reward": "protection"
      },
      {
        "id": "w3",
        "text": "RBI",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "challenge",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "hitter"
        },
        "description": "RBI",
        "metric": "rbi",
        "threshold": 1,
        "scope": "next_game",
        "reward": "protection"
      },
      {
        "id": "w4",
        "text": "Score a run",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "challenge",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "hitter"
        },
        "description": "Score a run",
        "metric": "r",
        "threshold": 1,
        "scope": "next_game",
        "reward": "protection"
      },
      {
        "id": "w5",
        "text": "Steal a base",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "challenge",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "hitter"
        },
        "description": "Steal a base",
        "metric": "sb",
        "threshold": 1,
        "scope": "next_game",
        "reward": "protection"
      },
      {
        "id": "w6",
        "text": "2 strikeouts",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "challenge",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "pitcher"
        },
        "description": "2 strikeouts",
        "metric": "so",
        "threshold": 2,
        "scope": "next_game",
        "reward": "protection"
      },
      {
        "id": "w7",
        "text": "3 strikeouts",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "challenge",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "pitcher"
        },
        "description": "3 strikeouts",
        "metric": "so",
        "threshold": 3,
        "scope": "next_game",
        "reward": "protection"
      },
      {
        "id": "w8",
        "text": "Save",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "challenge",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "pitcher"
        },
        "description": "Save",
        "metric": "sv",
        "threshold": 1,
        "scope": "next_game",
        "reward": "protection"
      },
      {
        "id": "w9",
        "text": "Hold",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "challenge",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "pitcher"
        },
        "description": "Hold",
        "metric": "holds",
        "threshold": 1,
        "scope": "next_game",
        "reward": "protection"
      },
      {
        "id": "w10",
        "text": "Retire 3 straight",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "challenge",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "pitcher"
        },
        "description": "Retire 3 straight",
        "metric": null,
        "threshold": 1,
        "scope": "next_game",
        "reward": "protection"
      }
    ]
  },
  {
    "wheel_id": "elimination",
    "display_name": "Second-Loss Elimination",
    "wedges": [
      {
        "id": "w0",
        "text": "DFA Worst Hitter",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "dfa",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "hitter"
        },
        "description": "DFA Worst Hitter",
        "selector": "worst"
      },
      {
        "id": "w1",
        "text": "DFA Worst Pitcher",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "dfa",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "pitcher"
        },
        "description": "DFA Worst Pitcher",
        "selector": "worst"
      },
      {
        "id": "w2",
        "text": "DFA Worst Overall",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "dfa",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true
        },
        "description": "DFA Worst Overall",
        "selector": "worst"
      },
      {
        "id": "w3",
        "text": "DFA Random Unprotected",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "dfa",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true
        },
        "description": "DFA Random Unprotected"
      },
      {
        "id": "w4",
        "text": "DFA Lowest OVR",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "dfa",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true
        },
        "description": "DFA Lowest OVR",
        "selector": "lowest"
      },
      {
        "id": "w5",
        "text": "DFA Highest OVR Unprotected",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "dfa",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true
        },
        "description": "DFA Highest OVR Unprotected",
        "selector": "highest"
      },
      {
        "id": "w6",
        "text": "DFA Bottom-3 Spin",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": "dfa_target",
        "eligibility": {
          "needs_target": true
        },
        "description": "DFA Bottom-3 Spin",
        "selector": "bottom3"
      },
      {
        "id": "w7",
        "text": "DFA Hot Seat Player",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "dfa",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "hot_seat": true
        },
        "description": "DFA Hot Seat Player"
      },
      {
        "id": "w8",
        "text": "DFA Failed Challenge Player",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "dfa",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "failed_challenge": true
        },
        "description": "DFA Failed Challenge Player"
      },
      {
        "id": "w9",
        "text": "Demote Worst Hitter",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "demote",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "hitter"
        },
        "description": "Demote Worst Hitter",
        "selector": "worst"
      },
      {
        "id": "w10",
        "text": "Demote Worst Pitcher",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "demote",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "pitcher"
        },
        "description": "Demote Worst Pitcher",
        "selector": "worst"
      },
      {
        "id": "w11",
        "text": "Demote Random Starter",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "demote",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "area": "lineup"
        },
        "description": "Demote Random Starter"
      },
      {
        "id": "w12",
        "text": "Demote Two",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "demote",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true
        },
        "description": "Demote Two",
        "quantity": 2
      },
      {
        "id": "w13",
        "text": "Send Hot Seat Player to Minors",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "demote",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "hot_seat": true
        },
        "description": "Send Hot Seat Player to Minors"
      },
      {
        "id": "w14",
        "text": "Trade Worst Performer",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "trade",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true
        },
        "description": "Trade Worst Performer",
        "selector": "worst"
      },
      {
        "id": "w15",
        "text": "Trade Random Starter",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "trade",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "area": "lineup"
        },
        "description": "Trade Random Starter"
      },
      {
        "id": "w16",
        "text": "Trade Highest OVR Unprotected",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "trade",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true
        },
        "description": "Trade Highest OVR Unprotected",
        "selector": "highest"
      },
      {
        "id": "w17",
        "text": "Forced Trade",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "trade",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true
        },
        "description": "Forced Trade"
      },
      {
        "id": "w18",
        "text": "Replace Starting Position",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "review",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Replace Starting Position \u2014 resolve manually during reconstruction; record the chosen cards and action in notes."
      },
      {
        "id": "w19",
        "text": "Replace Bench Spot",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "review",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Replace Bench Spot \u2014 resolve manually during reconstruction; record the chosen cards and action in notes."
      },
      {
        "id": "w20",
        "text": "Replace Rotation Spot",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "review",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Replace Rotation Spot \u2014 resolve manually during reconstruction; record the chosen cards and action in notes."
      },
      {
        "id": "w21",
        "text": "Replace Bullpen Spot",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "review",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Replace Bullpen Spot \u2014 resolve manually during reconstruction; record the chosen cards and action in notes."
      },
      {
        "id": "w22",
        "text": "Re-randomize Position",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "review",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Re-randomize Position \u2014 resolve manually during reconstruction; record the chosen cards and action in notes."
      },
      {
        "id": "w23",
        "text": "Entire Bench Review",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "review",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Entire Bench Review \u2014 resolve manually during reconstruction; record the chosen cards and action in notes."
      },
      {
        "id": "w24",
        "text": "Rotation Review",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "review",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Rotation Review \u2014 resolve manually during reconstruction; record the chosen cards and action in notes."
      },
      {
        "id": "w25",
        "text": "Bullpen Review",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "review",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Bullpen Review \u2014 resolve manually during reconstruction; record the chosen cards and action in notes."
      },
      {
        "id": "w26",
        "text": "No Punishment",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {},
        "description": "No Punishment"
      },
      {
        "id": "w27",
        "text": "Run MVP Saves Team",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {},
        "description": "Run MVP Saves Team"
      },
      {
        "id": "w28",
        "text": "Fan Favorite Saves Player",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {},
        "description": "Fan Favorite Saves Player"
      },
      {
        "id": "w29",
        "text": "Call-Up Instead",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "call_up",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Promote one existing minor-league card during offseason, then validate roster composition."
      },
      {
        "id": "w30",
        "text": "Free Front Office Spin",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": "front_office",
        "eligibility": {},
        "description": "Free Front Office Spin"
      },
      {
        "id": "w31",
        "text": "Two DFAs",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "dfa",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true
        },
        "description": "Two DFAs",
        "quantity": 2
      },
      {
        "id": "w32",
        "text": "DFA + Demotion",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "review",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true
        },
        "description": "Apply one DFA and one demotion to unprotected players in Roster Manager, then record both targets here."
      },
      {
        "id": "w33",
        "text": "Spin Twice",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "extra_spin",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {},
        "description": "Spin Twice",
        "quantity": 2
      },
      {
        "id": "w34",
        "text": "Crisis Wheel",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": "meltdown",
        "eligibility": {},
        "description": "Crisis Wheel"
      }
    ]
  },
  {
    "wheel_id": "dfa_target",
    "display_name": "DFA Target (eligible bottom three)",
    "wedges": [
      {
        "id": "w0",
        "text": "Eligible player",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Eligible player"
      }
    ]
  },
  {
    "wheel_id": "mvp",
    "display_name": "Run MVP Reward",
    "wedges": [
      {
        "id": "w0",
        "text": "Temporary protection",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "protect",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {},
        "description": "Temporary protection"
      },
      {
        "id": "w1",
        "text": "Franchise Tag hitter challenge",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": "tag_hitter",
        "eligibility": {
          "kind": "hitter"
        },
        "description": "Franchise Tag hitter challenge"
      },
      {
        "id": "w2",
        "text": "Franchise Tag pitcher challenge",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": "tag_pitcher",
        "eligibility": {
          "kind": "pitcher"
        },
        "description": "Franchise Tag pitcher challenge"
      },
      {
        "id": "w3",
        "text": "Front Office reward",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": "front_office",
        "eligibility": {},
        "description": "Front Office reward"
      }
    ]
  },
  {
    "wheel_id": "tag_hitter",
    "display_name": "Franchise Tag Hitter Challenge",
    "wedges": [
      {
        "id": "w0",
        "text": "5 hits next run",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "challenge",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "hitter"
        },
        "description": "5 hits next run",
        "metric": "h",
        "threshold": 5,
        "scope": "next_run",
        "reward": "tag"
      },
      {
        "id": "w1",
        "text": "2 HR next run",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "challenge",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "hitter"
        },
        "description": "2 HR next run",
        "metric": "hr",
        "threshold": 2,
        "scope": "next_run",
        "reward": "tag"
      },
      {
        "id": "w2",
        "text": "5 RBI next run",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "challenge",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "hitter"
        },
        "description": "5 RBI next run",
        "metric": "rbi",
        "threshold": 5,
        "scope": "next_run",
        "reward": "tag"
      },
      {
        "id": "w3",
        "text": "Golden Ticket immediate tag",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "tag",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "hitter"
        },
        "description": "Golden Ticket immediate tag",
        "metric": null,
        "threshold": 1,
        "scope": "next_run",
        "reward": "tag"
      }
    ]
  },
  {
    "wheel_id": "tag_pitcher",
    "display_name": "Franchise Tag Pitcher Challenge",
    "wedges": [
      {
        "id": "w0",
        "text": "10 strikeouts next run",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "challenge",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "pitcher"
        },
        "description": "10 strikeouts next run",
        "metric": "so",
        "threshold": 10,
        "scope": "next_run",
        "reward": "tag"
      },
      {
        "id": "w1",
        "text": "2 saves next run",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "challenge",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "pitcher"
        },
        "description": "2 saves next run",
        "metric": "sv",
        "threshold": 2,
        "scope": "next_run",
        "reward": "tag"
      },
      {
        "id": "w2",
        "text": "15 outs next run",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "challenge",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "pitcher"
        },
        "description": "15 outs next run",
        "metric": "outs",
        "threshold": 15,
        "scope": "next_run",
        "reward": "tag"
      },
      {
        "id": "w3",
        "text": "Golden Ticket immediate tag",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "tag",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {
          "needs_target": true,
          "kind": "pitcher"
        },
        "description": "Golden Ticket immediate tag",
        "metric": null,
        "threshold": 1,
        "scope": "next_run",
        "reward": "tag"
      }
    ]
  },
  {
    "wheel_id": "premium",
    "display_name": "Premium Reward",
    "wedges": [
      {
        "id": "w0",
        "text": "Any Legal Player",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Any Legal Player"
      },
      {
        "id": "w1",
        "text": "Any 99",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Any 99"
      },
      {
        "id": "w2",
        "text": "Upgrade Any Position",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Upgrade Any Position"
      },
      {
        "id": "w3",
        "text": "Two Acquisitions",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Two Acquisitions",
        "quantity": 2
      },
      {
        "id": "w4",
        "text": "Two Front Office Spins",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": "front_office",
        "eligibility": {},
        "description": "Two Front Office Spins",
        "quantity": 2
      },
      {
        "id": "w5",
        "text": "Any Hitter",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Any Hitter"
      },
      {
        "id": "w6",
        "text": "Any Pitcher",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Any Pitcher"
      },
      {
        "id": "w7",
        "text": "Any Legend",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Any Legend"
      },
      {
        "id": "w8",
        "text": "Any Current Player",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Any Current Player"
      },
      {
        "id": "w9",
        "text": "Any Team",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": "team",
        "eligibility": {},
        "description": "Any Team"
      },
      {
        "id": "w10",
        "text": "Any Division",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": "division",
        "eligibility": {},
        "description": "Any Division"
      },
      {
        "id": "w11",
        "text": "Any Series",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": "series",
        "eligibility": {},
        "description": "Any Series"
      },
      {
        "id": "w12",
        "text": "Opponent\u2019s Best Player",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Opponent\u2019s Best Player"
      },
      {
        "id": "w13",
        "text": "Same-Player Upgrade",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Same-Player Upgrade"
      },
      {
        "id": "w14",
        "text": "Bring Back Minor Leaguer",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "call_up",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Promote one existing minor-league card during offseason, then validate roster composition."
      },
      {
        "id": "w15",
        "text": "Save Pending DFA",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "save_dfa",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Cancel one eligible pending consequence from this run; select the consequence during offseason."
      },
      {
        "id": "w16",
        "text": "Cancel Elimination Punishment",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "cancel_elimination",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Cancel one eligible pending consequence from this run; select the consequence during offseason."
      },
      {
        "id": "w17",
        "text": "Protect Player Next Run",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "protect",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Protect Player Next Run"
      },
      {
        "id": "w18",
        "text": "Franchise Tag Challenge",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": "tag_hitter",
        "eligibility": {},
        "description": "Franchise Tag Challenge"
      },
      {
        "id": "w19",
        "text": "Franchise Tag Progress",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "review",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Franchise Tag Progress \u2014 record the explicit administrative resolution; historical spins remain unchanged."
      },
      {
        "id": "w20",
        "text": "Free Trade",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "trade",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true
        },
        "description": "Free Trade"
      },
      {
        "id": "w21",
        "text": "Blockbuster Trade",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "trade",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true
        },
        "description": "Blockbuster Trade"
      },
      {
        "id": "w22",
        "text": "Fan Choice",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Fan Choice"
      },
      {
        "id": "w23",
        "text": "Bank Premium Reward",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "review",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Bank Premium Reward \u2014 record the explicit administrative resolution; historical spins remain unchanged."
      },
      {
        "id": "w24",
        "text": "Double Premium",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "extra_spin",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {},
        "description": "Double Premium",
        "quantity": 2
      },
      {
        "id": "w25",
        "text": "Jackpot Player + Protection",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Jackpot Player + Protection"
      }
    ]
  },
  {
    "wheel_id": "meltdown",
    "display_name": "0\u20132 Meltdown",
    "wedges": [
      {
        "id": "w0",
        "text": "DFA two unprotected",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "dfa",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true
        },
        "description": "DFA two unprotected",
        "quantity": 2
      },
      {
        "id": "w1",
        "text": "Demote two unprotected",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "demote",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {
          "needs_target": true
        },
        "description": "Demote two unprotected",
        "quantity": 2
      },
      {
        "id": "w2",
        "text": "Extra elimination",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": "elimination",
        "eligibility": {},
        "description": "Extra elimination"
      },
      {
        "id": "w3",
        "text": "Mercy: no additional punishment",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "none",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {},
        "description": "Mercy: no additional punishment"
      }
    ]
  },
  {
    "wheel_id": "protection",
    "display_name": "Protection",
    "wedges": [
      {
        "id": "w0",
        "text": "Protect lowest OVR",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "protect",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {},
        "description": "Protect lowest OVR",
        "selector": "lowest"
      },
      {
        "id": "w1",
        "text": "Protect random player",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "protect",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {},
        "description": "Protect random player",
        "selector": "random"
      },
      {
        "id": "w2",
        "text": "Protect worst performer",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "protect",
        "timing": "immediate",
        "follow_up": null,
        "eligibility": {},
        "description": "Protect worst performer",
        "selector": "worst"
      }
    ]
  },
  {
    "wheel_id": "team",
    "display_name": "MLB Team",
    "wedges": [
      {
        "id": "w0",
        "text": "Arizona",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Arizona"
      },
      {
        "id": "w1",
        "text": "Atlanta",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Atlanta"
      },
      {
        "id": "w2",
        "text": "Baltimore",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Baltimore"
      },
      {
        "id": "w3",
        "text": "Boston",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Boston"
      },
      {
        "id": "w4",
        "text": "Chicago AL",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Chicago AL"
      },
      {
        "id": "w5",
        "text": "Chicago NL",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Chicago NL"
      },
      {
        "id": "w6",
        "text": "Cincinnati",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Cincinnati"
      },
      {
        "id": "w7",
        "text": "Cleveland",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Cleveland"
      },
      {
        "id": "w8",
        "text": "Colorado",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Colorado"
      },
      {
        "id": "w9",
        "text": "Detroit",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Detroit"
      },
      {
        "id": "w10",
        "text": "Houston",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Houston"
      },
      {
        "id": "w11",
        "text": "Kansas City",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Kansas City"
      },
      {
        "id": "w12",
        "text": "Los Angeles AL",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Los Angeles AL"
      },
      {
        "id": "w13",
        "text": "Los Angeles NL",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Los Angeles NL"
      },
      {
        "id": "w14",
        "text": "Miami",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Miami"
      },
      {
        "id": "w15",
        "text": "Milwaukee",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Milwaukee"
      },
      {
        "id": "w16",
        "text": "Minnesota",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Minnesota"
      },
      {
        "id": "w17",
        "text": "New York AL",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "New York AL"
      },
      {
        "id": "w18",
        "text": "New York NL",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "New York NL"
      },
      {
        "id": "w19",
        "text": "Athletics",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Athletics"
      },
      {
        "id": "w20",
        "text": "Philadelphia",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Philadelphia"
      },
      {
        "id": "w21",
        "text": "Pittsburgh",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Pittsburgh"
      },
      {
        "id": "w22",
        "text": "San Diego",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "San Diego"
      },
      {
        "id": "w23",
        "text": "San Francisco",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "San Francisco"
      },
      {
        "id": "w24",
        "text": "Seattle",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Seattle"
      },
      {
        "id": "w25",
        "text": "St. Louis",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "St. Louis"
      },
      {
        "id": "w26",
        "text": "Tampa Bay",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Tampa Bay"
      },
      {
        "id": "w27",
        "text": "Texas",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Texas"
      },
      {
        "id": "w28",
        "text": "Toronto",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Toronto"
      },
      {
        "id": "w29",
        "text": "Washington",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Washington"
      }
    ]
  },
  {
    "wheel_id": "division",
    "display_name": "Division",
    "wedges": [
      {
        "id": "w0",
        "text": "AL East",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "AL East"
      },
      {
        "id": "w1",
        "text": "AL Central",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "AL Central"
      },
      {
        "id": "w2",
        "text": "AL West",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "AL West"
      },
      {
        "id": "w3",
        "text": "NL East",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "NL East"
      },
      {
        "id": "w4",
        "text": "NL Central",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "NL Central"
      },
      {
        "id": "w5",
        "text": "NL West",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "NL West"
      }
    ]
  },
  {
    "wheel_id": "series",
    "display_name": "Card Series",
    "wedges": [
      {
        "id": "w0",
        "text": "Live Series",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Live Series"
      },
      {
        "id": "w1",
        "text": "Legend",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Legend"
      },
      {
        "id": "w2",
        "text": "Flashback",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Flashback"
      },
      {
        "id": "w3",
        "text": "Captain",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Captain"
      },
      {
        "id": "w4",
        "text": "Any legal series",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Any legal series"
      }
    ]
  },
  {
    "wheel_id": "attribute",
    "display_name": "Player Archetype",
    "wedges": [
      {
        "id": "w0",
        "text": "Power",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Power"
      },
      {
        "id": "w1",
        "text": "Contact",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Contact"
      },
      {
        "id": "w2",
        "text": "Speed",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Speed"
      },
      {
        "id": "w3",
        "text": "Defense",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Defense"
      },
      {
        "id": "w4",
        "text": "Left-handed bat",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Left-handed bat"
      },
      {
        "id": "w5",
        "text": "Right-handed bat",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Right-handed bat"
      },
      {
        "id": "w6",
        "text": "Switch hitter",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Switch hitter"
      },
      {
        "id": "w7",
        "text": "Starting pitcher",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Starting pitcher"
      },
      {
        "id": "w8",
        "text": "Reliever",
        "weight": 1,
        "active": true,
        "category": "acquire",
        "effect": "acquire",
        "timing": "banked",
        "follow_up": null,
        "eligibility": {},
        "description": "Reliever"
      }
    ]
  }
]

```

### random-franchise/data/.gitkeep

```text

```

### random-franchise/docs/ACCEPTANCE.md

```markdown
# Manual acceptance checklist

- [ ] Load the demo and verify 0–0 with the expected roster sections.
- [ ] Swap an eligible bench hitter into the lineup. Try an illegal pitcher/hitter swap and verify no partial save.
- [ ] Confirm active-run card additions/removals/imports and minor-league call-ups are blocked.
- [ ] Enter a win with stats, review, and save. Refresh and verify only one new game exists.
- [ ] Earn a two-win milestone. Complete any nested wheel and verify acquisitions are banked without changing the roster.
- [ ] Record a first loss; confirm Hot Seat is required and the roster remains locked.
- [ ] Record a second loss; confirm the run ends and another game cannot be entered.
- [ ] Confirm MVP, process elimination, resolve consequences and acquisitions, reconstruct, validate, and start at 0–0.
- [ ] Use a separate 0–2 run to verify the configured Meltdown behavior.
- [ ] Confirm ordinary removals exclude tagged/protected cards and a fourth tag requires replacement/decline.
- [ ] Mark an active card illegal or unknown; verify next-run validation fails until fixed.
- [ ] Correct hits and pitcher outs; confirm rates recalculate without repeated awards or spins.
- [ ] Verify outcome changes after a dependent spin are rejected while stats remain editable.
- [ ] Enter eight pitcher outs; verify 2.2 innings, not 2.67 or 2.8.
- [ ] Download a complete backup, restore into an empty installation, and verify records, tags, and audits.
- [ ] Open Creator OBS View; capture 16:9 and verify it has no management buttons. Reload to update its display.

```

### random-franchise/docs/ARCHITECTURE.md

```markdown
# Persisted workflow

| Current state | Required action | Next state |
| --- | --- | --- |
| SETUP / READY_FOR_NEXT_RUN | Validate and start | RUN_ACTIVE |
| RUN_ACTIVE, ordinary win | Save game and stats | RUN_ACTIVE |
| RUN_ACTIVE, milestone win | Save once, queue earned wheel | AWAITING_WHEEL |
| RUN_ACTIVE, loss below limit | Save once, queue Hot Seat | AWAITING_WHEEL |
| RUN_ACTIVE, final loss | End entry and snapshot roster | RUN_ENDED |
| AWAITING_WHEEL | Spin, apply/confirm, Continue | Next queued wheel or saved return state |
| RUN_ENDED | Confirm record | SELECTING_RUN_MVP |
| SELECTING_RUN_MVP | Choose MVP and protect | MVP wheel, then PROCESSING_ELIMINATION |
| PROCESSING_ELIMINATION | Queue elimination | Wheel, then PROCESSING_MELTDOWN |
| PROCESSING_MELTDOWN | Check 0–2 rules | Optional wheel, then RESOLVING_BANKED_MOVES |
| RESOLVING_BANKED_MOVES | Settle critical tasks/manual challenges | ROSTER_RECONSTRUCTION |
| ROSTER_RECONSTRUCTION | Arrange and confirm | ROSTER_VALIDATION |
| ROSTER_VALIDATION | Validate and approve | READY_FOR_NEXT_RUN |

Queue jobs contain stable IDs, sources, game/target links, nesting depth, branch constraints, and parent-spin IDs. A spin's ID equals its job ID, preventing repeats. Continue consumes the job once. Impossible/retried child audits remain intact, and the parent is preserved.

SQLite `BEGIN IMMEDIATE` serializes writes and saves all related changes atomically. Repeated game IDs return the original save. Rewards use deterministic milestone/challenge keys. Temporary drafts are conveniences, not authority.

Run card IDs are frozen in `runs.roster_ids`. Roster and banked-move services enforce the active-entry personnel lock independently of the UI. Arrange actions are audited; new games validate the assembled active roster. Cards remain in storage with DFA/minors status so their historical stats survive removal.

Tables store indexed JSON documents. Event definitions live in franchise settings and run snapshots; assignments live on player cards; career stats derive from per-game lines. `Repository` defines the adapter boundary for a future hosted backend. No hosted adapter exists in V1.

```

### random-franchise/docs/VERIFICATION.md

```markdown
# Verification

- Python 3.12, Streamlit 1.50.0, pytest 8.4.2.
- `python -m pytest -q`: **51 passed**.
- Python compilation: passed.
- Streamlit server startup: passed.
- HTTP root and health endpoints: 200 OK.
- Backend and Streamlit AppTest flows verified; manual live-game/OBS capture checks remain in ACCEPTANCE.md.

```

### random-franchise/manage_db.py

```python
"""Explicit initialization, safe reset, and backup restore CLI."""
import argparse
import os
import shutil
import sqlite3
from pathlib import Path
from repositories.sqlite import SQLiteRepository, TABLES


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['init','reset','restore'])
    parser.add_argument('--path',default=os.environ.get('RANDOM_FRANCHISE_DB','data/random_franchise.db'))
    parser.add_argument('--backup')
    parser.add_argument('--confirm',action='store_true',help='Confirm destructive reset/restore')
    args=parser.parse_args();path=Path(args.path)
    if args.action in ['reset','restore'] and not args.confirm:parser.error('Stop Streamlit first, then add --confirm.')
    if args.action=='restore':
        if not args.backup:parser.error('--backup is required.')
        source=Path(args.backup)
        if source.resolve()==path.resolve():parser.error('Backup and destination must differ.')
        con=sqlite3.connect(f'{source.resolve().as_uri()}?mode=ro',uri=True)
        try:
            if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok':parser.error('Invalid database.')
            tables={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not set(TABLES)<=tables or con.execute('PRAGMA user_version').fetchone()[0]!=1:parser.error('Incompatible backup.')
        finally:con.close()
    if args.action in ['reset','restore']:
        if path.exists():shutil.copy2(path,path.with_suffix('.pre-change-backup.db'))
        for suffix in ['', '-wal', '-shm']:Path(str(path)+suffix).unlink(missing_ok=True)
    path.parent.mkdir(parents=True,exist_ok=True)
    if args.action=='restore':shutil.copy2(args.backup,path)
    repo=SQLiteRepository(path);repo.close()
    print(f'Database {args.action} complete: {path}')

if __name__=='__main__':main()

```

### random-franchise/models/__init__.py

```python

```

### random-franchise/models/domain.py

```python
"""Domain vocabulary; independent of Streamlit and SQLite."""
from enum import StrEnum
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

class State(StrEnum):
    SETUP = 'SETUP'
    READY = 'READY_FOR_NEXT_RUN'
    ACTIVE = 'RUN_ACTIVE'
    WHEEL = 'AWAITING_WHEEL'
    ENDED = 'RUN_ENDED'
    MVP = 'SELECTING_RUN_MVP'
    ELIMINATION = 'PROCESSING_ELIMINATION'
    MELTDOWN = 'PROCESSING_MELTDOWN'
    MOVES = 'RESOLVING_BANKED_MOVES'
    REBUILD = 'ROSTER_RECONSTRUCTION'
    VALIDATION = 'ROSTER_VALIDATION'

class RuleError(ValueError):
    """A rejected operation, safe to display to a user."""

@dataclass(frozen=True)
class ValidationResult:
    errors: tuple[str, ...]
    @property
    def valid(self) -> bool:
        return not self.errors

ACTIVE_AREAS = {'lineup', 'bench', 'rotation', 'bullpen'}
POSITIONS = ['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH', 'SP', 'RP']
AREAS = ['lineup', 'bench', 'rotation', 'bullpen', 'minors', 'dfa']

def uid() -> str:
    return str(uuid4())

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

# Typed service DTOs, separate from the repository's JSON encoding.
from typing import TypedDict, Literal, NotRequired

class PlayerCard(TypedDict):
    id: str
    franchise_id: str
    name: str
    version: str
    ovr: int
    primary: str
    secondary: list[str]
    kind: Literal['hitter', 'pitcher']
    area: str
    position: str
    order: int
    eligibility: Literal['legal', 'illegal', 'unknown']
    protected: bool
    hot_seat: bool
    acquired_at: str
    notes: str

class EventRun(TypedDict):
    id: str
    franchise_id: str
    number: int
    event: str
    wins: int
    losses: int
    max_losses: int
    roster_ids: list[str]
    started_at: str
    ended_at: str | None
    mvp: str | None
    settings: dict

class WheelJob(TypedDict):
    id: str
    wheel_id: str
    source: str
    game_id: str | None
    target: str | None
    depth: int
    parent_spin: NotRequired[str]
    constraints: NotRequired[list[str]]

```

### random-franchise/pages/10_Creator_OBS_View.py

```python
from ui.common import run_page
from ui.creator import render

run_page('Creator OBS View', render, obs=True)

```

### random-franchise/pages/1_Dashboard.py

```python
from ui.common import run_page
from ui.dashboard import render

run_page('Dashboard', render, obs=False)

```

### random-franchise/pages/2_Roster_Manager.py

```python
from ui.common import run_page
from ui.roster import render

run_page('Roster Manager', render, obs=False)

```

### random-franchise/pages/3_Game_Entry.py

```python
from ui.common import run_page
from ui.game_entry import render

run_page('Game Entry', render, obs=False)

```

### random-franchise/pages/4_Wheel_Room.py

```python
from ui.common import run_page
from ui.wheel_room import render

run_page('Wheel Room', render, obs=False)

```

### random-franchise/pages/5_Banked_Moves.py

```python
from ui.common import run_page
from ui.banked_moves import render

run_page('Banked Moves', render, obs=False)

```

### random-franchise/pages/6_Offseason.py

```python
from ui.common import run_page
from ui.offseason import render

run_page('Offseason', render, obs=False)

```

### random-franchise/pages/7_Player_Stats.py

```python
from ui.common import run_page
from ui.player_stats import render

run_page('Player Stats', render, obs=False)

```

### random-franchise/pages/8_Franchise_History.py

```python
from ui.common import run_page
from ui.history import render

run_page('Franchise History', render, obs=False)

```

### random-franchise/pages/9_Settings.py

```python
from ui.common import run_page
from ui.settings import render

run_page('Settings', render, obs=False)

```

### random-franchise/pyproject.toml

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]

```

### random-franchise/repositories/__init__.py

```python

```

### random-franchise/repositories/sqlite.py

```python
"""Document repository with indexed ownership, transactions, and immutable audits.

Domain services use get/list/put/delete only. A Postgres repository can implement
this small API without moving game rules into the UI or database adapter.
"""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Protocol

TABLES = ('franchises', 'runs', 'players', 'games', 'stats', 'spins', 'moves',
          'rewards', 'challenges', 'snapshots', 'corrections', 'tags', 'wheels', 'settings')
IMMUTABLE = {'spins', 'corrections', 'snapshots'}

class Repository(Protocol):
    def get(self, table: str, identifier: str) -> dict[str, Any] | None: ...
    def list(self, table: str, franchise_id: str | None = None, run_id: str | None = None) -> list[dict]: ...
    def put(self, table: str, value: dict) -> None: ...
    def delete(self, table: str, identifier: str) -> None: ...
    def transaction(self): ...

class SQLiteRepository:
    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('PRAGMA foreign_keys=ON')
        self.connection.execute('PRAGMA journal_mode=WAL')
        self.connection.execute('PRAGMA busy_timeout=30000')
        self._depth = 0
        self.migrate()

    def migrate(self) -> None:
        version = self.connection.execute('PRAGMA user_version').fetchone()[0]
        if version > 1:
            raise RuntimeError('Database is newer than this app; use the matching app version.')
        for table in TABLES:
            self.connection.execute(f'''CREATE TABLE IF NOT EXISTS {table} (
                id TEXT PRIMARY KEY, franchise_id TEXT, run_id TEXT, payload TEXT NOT NULL
                CHECK(json_valid(payload)))''')
            self.connection.execute(f'CREATE INDEX IF NOT EXISTS ix_{table}_owner ON {table}(franchise_id,run_id)')
        for table in IMMUTABLE:
            for action in ('UPDATE', 'DELETE'):
                self.connection.execute(f'''CREATE TRIGGER IF NOT EXISTS immutable_{table}_{action}
                    BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'Immutable audit record'); END''')
        self.connection.execute('PRAGMA user_version=1')

    @staticmethod
    def _table(table: str) -> str:
        if table not in TABLES:
            raise ValueError('Unknown table')
        return table

    @contextmanager
    def transaction(self):
        outer = self._depth == 0
        if outer:
            self.connection.execute('BEGIN IMMEDIATE')
        self._depth += 1
        try:
            yield self
        except BaseException:
            if outer:
                self.connection.execute('ROLLBACK')
            raise
        else:
            if outer:
                self.connection.execute('COMMIT')
        finally:
            self._depth -= 1

    def get(self, table: str, identifier: str) -> dict | None:
        row = self.connection.execute(f'SELECT payload FROM {self._table(table)} WHERE id=?', (identifier,)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, table: str, franchise_id=None, run_id=None) -> list[dict]:
        where, values = [], []
        for key, value in [('franchise_id', franchise_id), ('run_id', run_id)]:
            if value is not None:
                where.append(f'{key}=?')
                values.append(value)
        query = f'SELECT payload FROM {self._table(table)}'
        if where:
            query += ' WHERE ' + ' AND '.join(where)
        return [json.loads(row[0]) for row in self.connection.execute(query + ' ORDER BY rowid', values)]

    def put(self, table: str, value: dict) -> None:
        table = self._table(table)
        params = (value['id'], value.get('franchise_id'), value.get('run_id'), json.dumps(value, allow_nan=False))
        sql = f'INSERT INTO {table}(id,franchise_id,run_id,payload) VALUES (?,?,?,?)'
        if table not in IMMUTABLE:
            sql += ' ON CONFLICT(id) DO UPDATE SET franchise_id=excluded.franchise_id,run_id=excluded.run_id,payload=excluded.payload'
        self.connection.execute(sql, params)

    def delete(self, table: str, identifier: str):
        self.connection.execute(f'DELETE FROM {self._table(table)} WHERE id=?', (identifier,))

    def backup_bytes(self) -> bytes:
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'backup.db'
            destination = sqlite3.connect(path)
            self.connection.backup(destination)
            destination.close()
            return path.read_bytes()

    def close(self):
        self.connection.close()

```

### random-franchise/requirements-dev.txt

```text
-r requirements.txt
pytest==8.4.2

```

### random-franchise/requirements.txt

```text
streamlit==1.50.0
pandas>=2.2,<3

```

### random-franchise/services/__init__.py

```python

```

### random-franchise/services/backup_service.py

```python
"""Restore a validated database into a fresh installation without replacing live files."""
import json
import sqlite3
import tempfile
from pathlib import Path
from models.domain import RuleError
from repositories.sqlite import TABLES


def restore_empty(repo, data: bytes):
    if len(data) > 50 * 1024 * 1024 or not data.startswith(b'SQLite format 3\x00'):
        raise RuleError('Upload a SQLite backup under 50 MB.')
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'backup.db'
        path.write_bytes(data)
        source = sqlite3.connect(f'{path.as_uri()}?mode=ro', uri=True)
        try:
            if source.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuleError('Backup failed integrity checks.')
            if source.execute('PRAGMA user_version').fetchone()[0] != 1:
                raise RuleError('Unsupported backup schema.')
            rows = {}
            for table in TABLES:
                rows[table] = [json.loads(r[0]) for r in source.execute(f'SELECT payload FROM {table} ORDER BY rowid')]
                if any(not isinstance(r, dict) or not isinstance(r.get('id'), str) for r in rows[table]):
                    raise RuleError('Backup contains invalid records.')
            franchise_ids = {f['id'] for f in rows['franchises']}
            if any(r.get('franchise_id') not in franchise_ids for table in TABLES for r in rows[table]):
                raise RuleError('Backup contains orphaned records.')
            with repo.transaction():
                if any(repo.list(table) for table in TABLES):
                    raise RuleError('Restore is only allowed into an empty installation. Keep existing data or restore locally to a separate database.')
                for table in TABLES:
                    for row in rows[table]:
                        repo.put(table, row)
            return len(rows['franchises'])
        except (sqlite3.DatabaseError, ValueError, KeyError) as exc:
            raise RuleError(f'Backup could not be restored: {exc}') from exc
        finally:
            source.close()

```

### random-franchise/services/challenge_service.py

```python
from models.domain import RuleError, uid, now
from services.stat_engine import aggregate
from services.franchise_tag_service import grant

# Quantitative V1 challenges use stat fields. Situational feats require evidence.
def create(repo, fid, run_id, pid, description, metric=None, threshold=1, scope='next_game', reward='protection', game_id=None):
    if not repo.get('players', pid) or repo.get('players', pid)['franchise_id'] != fid:
        raise RuleError('Challenge target not in this franchise.')
    identifier = uid()
    repo.put('challenges', dict(id=identifier, franchise_id=fid, run_id=run_id, player_id=pid,
        description=description, metric=metric, threshold=threshold, scope=scope, reward=reward,
        source_game=game_id, created_at=now(), status='waiting_next_run' if scope == 'next_run' else 'active'))
    return identifier

def evaluate(repo, fid, run_id, game_id):
    game = repo.get('games', game_id)
    for c in repo.list('challenges', fid, run_id):
        if c['status'] not in ['active', 'passed', 'failed', 'awaiting_manual']:
            continue
        games = repo.list('games', fid, run_id)
        candidates = [g for g in games if not c.get('source_game') or g['number'] > repo.get('games', c['source_game'])['number']]
        if not candidates:
            continue
        if c['scope'] == 'next_game':
            relevant = candidates[0]
            if relevant['id'] != game_id:
                continue
            closed = True
        else:
            relevant = game
            closed = bool(repo.get('runs', run_id)['ended_at'])
        if c.get('metric'):
            p = repo.get('players', c['player_id'])
            totals = aggregate(repo, fid, p, run_id, relevant['id'] if c['scope'] == 'next_game' else None)
            passed = totals.get(c['metric'], 0) >= c['threshold']
            if passed or closed:
                c['status'] = 'passed' if passed else 'failed'
                repo.put('challenges', c)
                settle(repo, c, passed)
        elif closed:
            c['status'] = 'awaiting_manual'
            repo.put('challenges', c)

def settle(repo, c, passed):
    key = f"challenge:{c['id']}"
    previous = repo.get('rewards', key)
    # Re-evaluation does not repeat granted benefits. Corrections remain audited.
    if passed and not previous:
        if c['reward'] == 'tag':
            result = grant(repo, c['franchise_id'], c['player_id'], source=c['description'])
            if result == 'cap_decision_required':
                repo.put('moves', dict(id=key, franchise_id=c['franchise_id'], run_id=c['run_id'], game_id=None,
                    type='tag', target=c['player_id'], description='Tag cap decision: ' + c['description'],
                    constraints={}, status='pending', critical=True, created_at=now(), source='challenge'))
        else:
            p = repo.get('players', c['player_id'])
            p['protected'] = True
            repo.put('players', p)
        repo.put('rewards', dict(id=key, franchise_id=c['franchise_id'], run_id=c['run_id'],
                                type=c['reward'], player_id=c['player_id'], status='earned'))
    elif not passed and previous:
        previous['status'] = 'correction_review'
        repo.put('rewards', previous)


def confirm_manual(repo, fid, cid, passed, evidence):
    from services.franchise_service import audit
    with repo.transaction():
        c = repo.get('challenges', cid)
        if not c or c['franchise_id'] != fid or c['status'] != 'awaiting_manual' or not evidence.strip():
            raise RuleError('Select a pending manual challenge and provide evidence.')
        before = dict(c)
        c.update(status='passed' if passed else 'failed', evidence=evidence)
        repo.put('challenges', c)
        settle(repo, c, passed)
        audit(repo, fid, 'challenge_evidence', before, c, evidence, c['run_id'])

```

### random-franchise/services/demo.py

```python
from models.domain import now, uid
from services.franchise_service import create_franchise
from services.roster_service import add_player
from services.franchise_tag_service import grant
from services.game_engine import start_run
from services.challenge_service import create


def load_demo(repo):
    with repo.transaction():
        fid = create_franchise(repo, 'Cedar City Comets (Demo)', 'Open exhibition Event')
        positions = ['C','1B','2B','3B','SS','LF','CF','RF','DH']
        names = ['Alex Vale','River Stone','Jordan Pine','Casey Brook','Drew Summit','Morgan Lake','Taylor Reed','Riley Ash','Sam West']
        for i,(name,position) in enumerate(zip(names,positions),1):
            add_player(repo,fid,dict(name=name,ovr=79+i,primary=position,secondary=positions[:-1],kind='hitter',area='lineup',position=position,order=i,eligibility='legal'))
        for i in range(4):
            add_player(repo,fid,dict(name=f'Bench Prospect {i+1}',ovr=74+i,primary='CF',secondary=positions[:-1],kind='hitter',area='bench',position='CF',order=i+1,eligibility='legal'))
        for area,position,size in [('rotation','SP',5),('bullpen','RP',8)]:
            for i in range(size):
                add_player(repo,fid,dict(name=f'{area.title()} Ace {i+1}',ovr=78+i,primary=position,secondary=['SP','RP'],kind='pitcher',area=area,position=position,order=i+1,eligibility='legal'))
        add_player(repo,fid,dict(name='Jamie Orchard',primary='SS',secondary=['2B'],ovr=72,eligibility='legal'))
        first=repo.list('players',fid)[0]
        grant(repo,fid,first['id'],source='Demo franchise cornerstone')
        rid=start_run(repo,fid)
        create(repo,fid,rid,first['id'],'Get a hit in your next game','h',1)
        repo.put('moves',dict(id=uid(),franchise_id=fid,run_id=rid,game_id=None,type='acquire',source='demo',
            description='Demo: sign one legal free agent in offseason',constraints={'quantity':1},status='pending',critical=False,created_at=now()))
        return fid

```

### random-franchise/services/franchise_service.py

```python
import json
from pathlib import Path
from models.domain import State, RuleError, uid, now

ROOT = Path(__file__).resolve().parents[1]

def defaults(name: str):
    return json.loads((ROOT / 'config' / name).read_text(encoding='utf-8'))

def create_franchise(repo, name: str, event: str) -> str:
    if not name.strip() or not event.strip():
        raise RuleError('Franchise and Event names are required.')
    identifier = uid()
    with repo.transaction():
        repo.put('franchises', dict(id=identifier, franchise_id=identifier, name=name.strip(), event=event.strip(),
            state=State.SETUP, current_run=None, queue=[], return_state=State.ACTIVE, created_at=now()))
        repo.put('settings', dict(id=identifier, franchise_id=identifier, values=defaults('default_settings.json')))
        for wheel in defaults('default_wheels.json'):
            repo.put('wheels', dict(wheel, id=f"{identifier}:{wheel['wheel_id']}", franchise_id=identifier))
    return identifier

def settings(repo, fid):
    return repo.get('settings', fid)['values']

def audit(repo, fid, action, before, after, reason, run_id=None):
    repo.put('corrections', dict(id=uid(), franchise_id=fid, run_id=run_id, action=action,
                                before=before, after=after, reason=reason, created_at=now()))

def save_settings(repo, fid, values):
    with repo.transaction():
        f = repo.get('franchises', fid)
        if f['current_run'] and not repo.get('runs', f['current_run'])['ended_at']:
            raise RuleError('Change rules between runs so the current entry uses one consistent ruleset.')
        if not isinstance(values, dict):
            raise RuleError('Settings must be a JSON object.')
        values = {**defaults('default_settings.json'), **values}
        if not isinstance(values.get('milestones'), dict):
            raise RuleError('Milestones must be an object mapping win thresholds to wheel IDs.')
        for key in ['team', 'series', 'primary', 'bat', 'throw']:
            for prefix in ['allowed_', 'disallowed_']:
                items = values[prefix + key]
                if not isinstance(items, list) or any(not isinstance(x, str) for x in items):
                    raise RuleError(f'{prefix + key} must be a list of strings.')
        if values.get('ovr_cap') is not None and (not isinstance(values['ovr_cap'], (int, float)) or not 0 < values['ovr_cap'] <= 99):
            raise RuleError('OVR cap must be null or a number greater than zero and no more than 99.')
        if not isinstance(values.get('max_losses'), int) or not 1 <= values['max_losses'] <= 10:
            raise RuleError('Maximum losses must be an integer from 1 to 10.')
        if not isinstance(values.get('tag_cap'), int) or values['tag_cap'] < 1:
            raise RuleError('Tag cap must be a positive integer.')
        if len([t for t in repo.list('tags', fid) if t['active']]) > values['tag_cap']:
            raise RuleError('Remove tags before lowering the cap.')
        if values.get('meltdown') not in ['none', 'wheel', 'extra_elimination']:
            raise RuleError('Meltdown must be none, wheel, or extra_elimination.')
        valid_wheels = {w['wheel_id'] for w in repo.list('wheels', fid)}
        for key, wheel in values.get('milestones', {}).items():
            if not str(key).isdigit() or int(key) < 1 or wheel not in valid_wheels:
                raise RuleError('Milestones need positive win counts and existing wheel IDs.')
        for key in ['bench_size', 'rotation_size', 'bullpen_size']:
            if not isinstance(values.get(key), int) or not 0 <= values[key] <= 30:
                raise RuleError(f'{key} must be an integer from 0 to 30.')
        before = settings(repo, fid)
        repo.put('settings', dict(id=fid, franchise_id=fid, values=values))
        audit(repo, fid, 'settings', before, values, 'Settings editor')

```

### random-franchise/services/franchise_tag_service.py

```python
from models.domain import RuleError, uid, now
from services.franchise_service import settings, audit

def grant(repo, fid, pid, replace_id=None, source='manual'):
    with repo.transaction():
        p = repo.get('players', pid)
        if not p or p['franchise_id'] != fid:
            raise RuleError('Invalid tag player.')
        tags = [t for t in repo.list('tags', fid) if t['active']]
        if any(t['player_id'] == pid for t in tags):
            return 'already_tagged'
        if len(tags) >= settings(repo, fid)['tag_cap']:
            old = next((t for t in tags if t['player_id'] == replace_id), None)
            if not old:
                return 'cap_decision_required'
            old['active'] = False
            repo.put('tags', old)
            audit(repo, fid, 'replace_tag', old['player_id'], pid, source)
        repo.put('tags', dict(id=uid(), franchise_id=fid, player_id=pid, active=True, created_at=now(), source=source))
        audit(repo, fid, 'grant_tag', None, pid, source)
        return 'granted'

```

### random-franchise/services/game_engine.py

```python
from models.domain import State, RuleError, uid, now, ACTIVE_AREAS
from services.franchise_service import settings, audit
from services.roster_validator import validate
from services.stat_engine import validate_line
from services.challenge_service import evaluate
from services.franchise_tag_service import grant


def enqueue(franchise, wheel_id, source, game_id=None, target=None, depth=0):
    franchise['queue'].append(dict(id=uid(), wheel_id=wheel_id, source=source, game_id=game_id,
                                   target=target, depth=depth))


def start_run(repo, fid):
    with repo.transaction():
        f = repo.get('franchises', fid)
        if f['state'] not in [State.SETUP, State.READY, State.VALIDATION]:
            raise RuleError('Finish the current workflow before starting a run.')
        errors = validate(repo, fid).errors
        if errors:
            raise RuleError('\n'.join(errors))
        cfg = settings(repo, fid)
        rid = uid()
        active = [p['id'] for p in repo.list('players', fid) if p['area'] in ACTIVE_AREAS]
        repo.put('runs', dict(id=rid, franchise_id=fid, number=len(repo.list('runs', fid)) + 1,
            event=f['event'], wins=0, losses=0, max_losses=cfg['max_losses'], settings=cfg,
            roster_ids=active, started_at=now(), ended_at=None, mvp=None, offseason_step=None))
        f.update(current_run=rid, state=State.ACTIVE, queue=[], return_state=State.ACTIVE)
        repo.put('franchises', f)
        for c in repo.list('challenges', fid):
            if c['status'] == 'waiting_next_run':
                c.update(run_id=rid, status='active', source_game=None)
                repo.put('challenges', c)
        snapshot(repo, fid, rid, 'start')
        return rid


def snapshot(repo, fid, rid, phase):
    identifier = f'{rid}:{phase}'
    if not repo.get('snapshots', identifier):
        repo.put('snapshots', dict(id=identifier, franchise_id=fid, run_id=rid, phase=phase,
            created_at=now(), players=repo.list('players', fid)))


def milestone_sync(repo, f, run, game_id):
    for threshold, wheel in run['settings']['milestones'].items():
        key = f"milestone:{run['id']}:{threshold}"
        reward = repo.get('rewards', key)
        if run['wins'] >= int(threshold) and (not reward or reward['status'] == 'revoked'):
            repo.put('rewards', dict(id=key, franchise_id=f['id'], run_id=run['id'], game_id=game_id,
                                     type=wheel, threshold=int(threshold), status='earned'))
            enqueue(f, wheel, key, game_id)
        elif run['wins'] >= int(threshold) and reward and reward.get('game_id') == game_id:
            if not any(j['source'] == key for j in f['queue']) and not any(s['job']['source'] == key for s in repo.list('spins', f['id'])):
                enqueue(f, wheel, key, game_id)
        elif run['wins'] < int(threshold) and reward and reward['status'] == 'earned':
            reward['status'] = 'revoked'
            repo.put('rewards', reward)
            f['queue'] = [j for j in f['queue'] if j['source'] != key]


def _route(repo, f, run, game):
    if run['losses'] >= run['max_losses']:
        run['ended_at'] = run['ended_at'] or now()
        f['state'] = State.ENDED
        f['return_state'] = State.ENDED
        snapshot(repo, f['id'], run['id'], 'end')
    else:
        run['ended_at'] = None
        if game['result'] == 'L':
            enqueue(f, 'hot_seat', 'loss', game['id'])
        f['return_state'] = State.ACTIVE
        f['state'] = State.WHEEL if f['queue'] else State.ACTIVE
    repo.put('runs', run)
    repo.put('franchises', f)


def _save_lines(repo, fid, run, game, lines):
    seen = set()
    for item in lines:
        pid = item['player_id']
        p = repo.get('players', pid)
        if pid in seen or not p or p['franchise_id'] != fid or pid not in run['roster_ids']:
            raise RuleError('Stat lines must reference distinct players in the run roster.')
        seen.add(pid)
        line = validate_line(p['kind'], item['line'])
        flags = item.get('flags', {})
        if flags.get('no_hitter') or flags.get('perfect_game'):
            if p['kind'] != 'pitcher' or line['outs'] < 9 or line['ha'] != 0:
                raise RuleError('No-hitter/perfect game needs a pitcher with at least 9 outs and zero hits allowed.')
            if flags.get('perfect_game') and (line['bb'] or line['r']):
                raise RuleError('Perfect game requires zero walks and runs.')
        repo.put('stats', dict(id=f"{game['id']}:{pid}", franchise_id=fid, run_id=run['id'],
                              player_id=pid, game_id=game['id'], line=line, flags=flags))
        if flags.get('no_hitter') or flags.get('perfect_game'):
            status = grant(repo, fid, pid, source='Manually confirmed no-hitter/perfect game')
            key = f"auto_tag:{game['id']}:{pid}"
            if status == 'cap_decision_required' and not repo.get('moves', key):
                repo.put('moves', dict(id=key, franchise_id=fid, run_id=run['id'], game_id=game['id'],
                    target=pid, source='no_hitter', type='tag', constraints={}, description='Automatic pitcher tag: resolve cap decision',
                    status='pending', critical=True, created_at=now()))


def record_game(repo, fid, request_id, result, lines=None, opponent='', team_score=None, opponent_score=None, date=None, notes=''):
    with repo.transaction():
        previous = repo.get('games', request_id)
        if previous:
            if previous['franchise_id'] != fid:
                raise RuleError('Submission ID belongs to another franchise.')
            return previous['id']
        f = repo.get('franchises', fid)
        run = repo.get('runs', f['current_run']) if f['current_run'] else None
        if f['state'] != State.ACTIVE or not run or run['ended_at']:
            raise RuleError('Game entry is blocked until the required workflow is finished.')
        roster_check = validate(repo, fid, check_tasks=False)
        if not roster_check.valid:
            raise RuleError('Fix active roster arrangements before recording a game: ' + '; '.join(roster_check.errors))
        if result not in ['W', 'L']:
            raise RuleError('Choose W or L.')
        if team_score is not None or opponent_score is not None:
            if team_score is None or opponent_score is None or min(team_score, opponent_score) < 0:
                raise RuleError('Enter both nonnegative scores or leave both blank.')
            if team_score == opponent_score or (team_score > opponent_score) != (result == 'W'):
                raise RuleError('Score must agree with win/loss result.')
        game = dict(id=request_id, franchise_id=fid, run_id=run['id'], number=len(repo.list('games', fid, run['id'])) + 1,
            result=result, opponent=opponent, team_score=team_score, opponent_score=opponent_score,
            date=str(date or now()[:10]), notes=notes, created_at=now())
        repo.put('games', game)
        _save_lines(repo, fid, run, game, lines or [])
        run['wins' if result == 'W' else 'losses'] += 1
        milestone_sync(repo, f, run, request_id)
        _route(repo, f, run, game)
        evaluate(repo, fid, run['id'], request_id)
        return request_id


def correct_game(repo, fid, gid, lines, reason, result=None):
    """Stats can always be corrected. Outcome correction is limited to an unprocessed latest game.

    Historical wheel outcomes are never rewound. Dependent outcome edits require
    a new explicit administrative workflow in V2; refusing is safer than replaying spins.
    """
    with repo.transaction():
        game = repo.get('games', gid)
        if not game or game['franchise_id'] != fid or not reason.strip():
            raise RuleError('Valid game and correction reason required.')
        before = dict(game=game, stats=[s for s in repo.list('stats', fid, game['run_id']) if s['game_id'] == gid])
        run = repo.get('runs', game['run_id'])
        f = repo.get('franchises', fid)
        changed = result is not None and result != game['result']
        if changed:
            if result not in ['W', 'L']:
                raise RuleError('Choose W or L.')
            if f['current_run'] != run['id'] or repo.list('games', fid, run['id'])[-1]['id'] != gid:
                raise RuleError('Outcome corrections are limited to the latest game of the current run.')
            if any(s.get('game_id') == gid for s in repo.list('spins', fid)) or run.get('offseason_step'):
                raise RuleError('Dependent wheels/offseason already processed. Stats correction remains available; outcome rewind is unsupported in V1.')
            f['queue'] = [j for j in f['queue'] if j.get('game_id') != gid]
            run['wins' if game['result'] == 'W' else 'losses'] -= 1
            run['wins' if result == 'W' else 'losses'] += 1
            game.update(result=result, team_score=None, opponent_score=None)
            milestone_sync(repo, f, run, gid)
            _route(repo, f, run, game)
        repo.put('games', game)
        for row in before['stats']:
            repo.delete('stats', row['id'])
        _save_lines(repo, fid, run, game, lines)
        evaluate(repo, fid, run['id'], gid)
        audit(repo, fid, 'correct_game', before,
              dict(game=game, stats=[s for s in repo.list('stats', fid, run['id']) if s['game_id'] == gid]), reason, run['id'])

```

### random-franchise/services/import_export.py

```python
"""Manual roster interchange; external provider integration deliberately unimplemented."""
import csv
import io
import json
from typing import Protocol
from models.domain import RuleError
from services.roster_service import add_player, locked

class RosterProvider(Protocol):
    def fetch_roster(self, external_id: str) -> list[dict]: ...

class ExternalProviderPlaceholder:
    def fetch_roster(self, external_id: str) -> list[dict]:
        raise NotImplementedError('Configure a licensed provider adapter in V2. No scraping is performed.')

FIELDS = ['name','version','ovr','primary','secondary','kind','team','series','bat','throw','area','position','order','eligibility','notes']

def export_roster(repo, fid, fmt='json'):
    rows = [{key: p.get(key, '') for key in FIELDS} for p in repo.list('players', fid)]
    if fmt == 'json':
        return json.dumps(rows, indent=2)
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=FIELDS)
    writer.writeheader()
    for row in rows:
        row['secondary'] = '|'.join(row['secondary'])
        writer.writerow(row)
    return stream.getvalue()

def import_roster(repo, fid, content, fmt):
    if locked(repo, fid):
        raise RuleError('Roster imports are only available between runs.')
    try:
        rows = json.loads(content) if fmt == 'json' else list(csv.DictReader(io.StringIO(content)))
        if not isinstance(rows, list) or len(rows) > 500:
            raise ValueError('Expected a list of at most 500 cards.')
        with repo.transaction():
            ids = []
            for raw in rows:
                data = {key: value for key, value in raw.items() if key in FIELDS}
                for key in ['ovr', 'order']:
                    if key in data:
                        data[key] = int(data[key])
                if isinstance(data.get('secondary'), str):
                    data['secondary'] = [s.strip() for s in data['secondary'].split('|') if s.strip()]
                ids.append(add_player(repo, fid, data))
            return ids
    except (ValueError, TypeError, AttributeError) as exc:
        raise RuleError(f'Import rejected; no rows changed: {exc}') from exc

```

### random-franchise/services/offseason_service.py

```python
from models.domain import State, RuleError, now, uid
from services.game_engine import enqueue, snapshot
from services.roster_service import locked, remove_player, add_player, arrange, protected, target_pool
from services.franchise_tag_service import grant
from services.franchise_service import audit
from services.roster_validator import validate


def confirm_end(repo, fid):
    with repo.transaction():
        f = repo.get('franchises', fid)
        if f['state'] != State.ENDED:
            raise RuleError('No ended run to confirm.')
        r = repo.get('runs', f['current_run'])
        r['offseason_step'] = 'mvp'
        f['state'] = State.MVP
        repo.put('runs', r)
        repo.put('franchises', f)


def select_mvp(repo, fid, pid):
    with repo.transaction():
        f = repo.get('franchises', fid)
        r = repo.get('runs', f['current_run'])
        if f['state'] != State.MVP or pid not in r['roster_ids']:
            raise RuleError('Select a player from the ended run.')
        r.update(mvp=pid, offseason_step='elimination')
        p = repo.get('players', pid)
        p['protected'] = True
        repo.put('players', p)
        repo.put('runs', r)
        enqueue(f, 'mvp', 'run_mvp', target=pid)
        f.update(state=State.WHEEL, return_state=State.ELIMINATION)
        repo.put('franchises', f)


def progress(repo, fid):
    with repo.transaction():
        f = repo.get('franchises', fid)
        r = repo.get('runs', f['current_run'])
        if f['state'] == State.ELIMINATION:
            enqueue(f, 'elimination', 'run_end')
            f.update(state=State.WHEEL, return_state=State.MELTDOWN)
            r['offseason_step'] = 'meltdown'
        elif f['state'] == State.MELTDOWN:
            mode = r['settings']['meltdown']
            if r['wins'] == 0 and r['losses'] == 2 and mode != 'none':
                enqueue(f, 'meltdown' if mode == 'wheel' else 'elimination', '0–2 meltdown')
                f.update(state=State.WHEEL, return_state=State.MOVES)
            else:
                f['state'] = State.MOVES
            r['offseason_step'] = 'moves'
        elif f['state'] == State.MOVES:
            if any(m['status'] == 'pending' and m.get('critical') for m in repo.list('moves', fid)):
                raise RuleError('Resolve all critical obligations before reconstruction.')
            if any(c['status'] == 'awaiting_manual' for c in repo.list('challenges', fid)):
                raise RuleError('Confirm manual challenge evidence first.')
            f['state'] = State.REBUILD
            r['offseason_step'] = 'rebuild'
        elif f['state'] == State.REBUILD:
            f['state'] = State.VALIDATION
        else:
            raise RuleError('Complete the current action first.')
        repo.put('runs', r)
        repo.put('franchises', f)


def resolve_move(repo, fid, mid, action, notes, target_id=None, new_player=None, replace_tag=None, confirmed=False, cancel_move_id=None):
    with repo.transaction():
        m = repo.get('moves', mid)
        if not m or m['franchise_id'] != fid:
            raise RuleError('Invalid move.')
        if m['status'] not in ['pending', 'deferred']:
            return
        if locked(repo, fid):
            raise RuleError('Banked moves can only resolve after the run ends.')
        f = repo.get('franchises', fid)
        if f['state'] not in [State.MOVES, State.REBUILD, State.VALIDATION]:
            raise RuleError('Finish MVP and elimination before resolving moves.')
        if not notes.strip() or not confirmed:
            raise RuleError('Provide resolution notes and confirm the action.')
        before = dict(m)
        if action in ['deferred', 'canceled']:
            if m.get('critical') and m['type'] != 'tag':
                raise RuleError('Critical consequences must be applied; they cannot be skipped.')
            m.update(status=action, critical=False)
        elif action == 'resolved':
            pid = target_id or m.get('target')
            if m['type'] in ['dfa', 'demote', 'trade'] and m.get('target') and pid != m['target']:
                original = repo.get('players', m['target'])
                if original and original['area'] in ['lineup', 'bench', 'rotation', 'bullpen'] and not protected(repo, fid, original):
                    raise RuleError('Use the audited wheel target; retargeting is allowed only if it becomes ineligible.')
            quantity = m.get('constraints', {}).get('quantity', 1)
            if m['type'] in ['cancel_elimination', 'save_dfa']:
                other = repo.get('moves', cancel_move_id) if cancel_move_id else None
                allowed = ['dfa'] if m['type'] == 'save_dfa' else ['dfa', 'demote', 'trade']
                if not other or other['franchise_id'] != fid or other['run_id'] != m['run_id'] or other['status'] != 'pending' or other['type'] not in allowed:
                    raise RuleError('Select an eligible pending consequence from this run.')
                other.update(status='canceled', critical=False, resolved_at=now(), resolution_notes='Canceled by reward ' + mid + ': ' + notes)
                repo.put('moves', other)
                audit(repo, fid, 'awarded_cancellation', None, other, notes, m['run_id'])
            elif m['type'] == 'call_up':
                p = repo.get('players', pid) if pid else None
                if not p or p['franchise_id'] != fid or p['area'] != 'minors':
                    raise RuleError('Choose an existing minor-league player.')
                area = 'bench' if p['kind'] == 'hitter' else 'rotation' if p['primary'] == 'SP' else 'bullpen'
                arrange(repo, fid, pid, area, p['primary'], p['order'])
            elif m['type'] in ['dfa', 'demote', 'trade']:
                pool = target_pool(repo, fid)
                if not pid or pid not in {p['id'] for p in pool}:
                    if not pool:
                        m.update(status='invalid', critical=False, resolution_notes='No eligible unprotected target: ' + notes)
                        repo.put('moves', m)
                        audit(repo, fid, 'impossible_move', before, m, notes)
                        return
                    raise RuleError('Choose an eligible, unprotected active player.')
                targets = [pid] + [p['id'] for p in pool if p['id'] != pid][:quantity - 1]
                if len(targets) < quantity:
                    raise RuleError('Not enough eligible players for the required quantity.')
                for target in targets:
                    remove_player(repo, fid, target, 'minors' if m['type'] == 'demote' else 'dfa')
                if m['type'] == 'trade':
                    if not new_player:
                        raise RuleError('Enter the incoming trade card.')
                    add_player(repo, fid, new_player)
            elif m['type'] == 'tag':
                if not pid or grant(repo, fid, pid, replace_tag, source=m['description']) == 'cap_decision_required':
                    raise RuleError('Choose a tag holder to replace, or decline this new tag.')
            elif m['type'] == 'protect':
                p = repo.get('players', pid)
                if not p or p['franchise_id'] != fid:
                    raise RuleError('Select a protection target.')
                p['protected'] = True
                if 'Next Run' in m['description']:
                    p['protection_until_run'] = repo.get('runs', f['current_run'])['number'] + 1
                repo.put('players', p)
            elif m['type'] == 'extra_spin':
                enqueue(f, 'front_office', m['id'])
                f.update(state=State.WHEEL, return_state=State.MOVES)
                repo.put('franchises', f)
            elif m['type'] == 'acquire':
                incoming = new_player if isinstance(new_player, list) else [new_player] if new_player else []
                if len(incoming) != quantity:
                    raise RuleError(f'Provide {quantity} incoming card(s).')
                for card in incoming:
                    add_player(repo, fid, card)
            # Review/choice rewards are explicitly acknowledged with notes.
            m['status'] = 'resolved'
        else:
            raise RuleError('Unknown resolution action.')
        m.update(resolution_notes=notes, resolved_at=now())
        repo.put('moves', m)
        audit(repo, fid, 'resolve_move', before, m, notes, m.get('run_id'))


def finish_validation(repo, fid):
    with repo.transaction():
        f = repo.get('franchises', fid)
        if f['state'] != State.VALIDATION:
            raise RuleError('Proceed to roster validation first.')
        result = validate(repo, fid)
        if not result.valid:
            raise RuleError('\n'.join(result.errors))
        snapshot(repo, fid, f['current_run'], 'rebuilt')
        # MVP/temporary protection protects through this elimination cycle, then expires.
        current_number = repo.get('runs', f['current_run'])['number']
        for p in repo.list('players', fid):
            p.update(protected=bool(p.get('protection_until_run', 0) > current_number), hot_seat=False)
            repo.put('players', p)
        f['state'] = State.READY
        repo.put('franchises', f)

```

### random-franchise/services/roster_service.py

```python
from models.domain import RuleError, ACTIVE_AREAS, AREAS, POSITIONS, uid, now
from services.franchise_service import audit
from services.roster_validator import legal_positions

def locked(repo, fid):
    f = repo.get('franchises', fid)
    return bool(f['current_run'] and not repo.get('runs', f['current_run'])['ended_at'])

def protected(repo, fid, player):
    tagged = any(t['player_id'] == player['id'] and t['active'] for t in repo.list('tags', fid))
    return tagged or bool(player.get('protected'))

def target_pool(repo, fid, kind=None):
    return [p for p in repo.list('players', fid) if p['area'] in ACTIVE_AREAS and
            not protected(repo, fid, p) and (kind is None or p['kind'] == kind)]

def add_player(repo, fid, data):
    with repo.transaction():
        if locked(repo, fid):
            raise RuleError('Roster locked: new cards must wait until offseason.')
        if not isinstance(data, dict):
            raise RuleError('Incoming player must be a JSON object.')
        p = dict(id=uid(), franchise_id=fid, name='', version='Base', ovr=75, primary='C', secondary=[],
                 kind='hitter', team='', series='', bat='', throw='', area='minors', position='C', order=1,
                 eligibility='unknown', protected=False, hot_seat=False, notes='', acquired_at=now(),
                 acquisition_run=repo.get('franchises', fid).get('current_run'))
        p.update({key: value for key, value in data.items() if key not in ['id', 'franchise_id']})
        if not p['name'].strip() or not isinstance(p['ovr'], int) or not 0 <= p['ovr'] <= 99:
            raise RuleError('Player needs a name and integer OVR from 0 to 99.')
        if p['kind'] not in ['hitter', 'pitcher'] or p['area'] not in AREAS or p['primary'] not in POSITIONS:
            raise RuleError('Invalid player kind, area, or primary position.')
        if not isinstance(p['secondary'], list) or any(s not in POSITIONS for s in p['secondary']):
            raise RuleError('Secondary positions must be a list of position codes.')
        if p['eligibility'] not in ['legal', 'illegal', 'unknown']:
            raise RuleError('Invalid Event eligibility.')
        if not isinstance(p['order'], int) or p['order'] < 1:
            raise RuleError('Roster order must be a positive integer.')
        repo.put('players', p)
        audit(repo, fid, 'add_player', None, p, 'Manual acquisition')
        return p['id']

def remove_player(repo, fid, pid, area='dfa'):
    with repo.transaction():
        if locked(repo, fid):
            raise RuleError('Roster locked: removals/demotions must wait until offseason.')
        p = repo.get('players', pid)
        if not p or p['franchise_id'] != fid:
            raise RuleError('Player not in this franchise.')
        if area not in ['dfa', 'minors']:
            raise RuleError('Removal destination must be DFA or minors.')
        if protected(repo, fid, p):
            raise RuleError('Tagged/protected players are excluded from ordinary removals.')
        before = dict(p)
        p['area'] = area
        repo.put('players', p)
        audit(repo, fid, 'remove_player', before, p, f'Move to {area}')

def arrange(repo, fid, pid, area, position, order):
    with repo.transaction():
        p = repo.get('players', pid)
        if not p or p['franchise_id'] != fid:
            raise RuleError('Player not in this franchise.')
        if area not in AREAS or not isinstance(order, int) or order < 1:
            raise RuleError('Invalid area or order.')
        if area == 'dfa':
            raise RuleError('Use the confirmed removal action for DFA.')
        if locked(repo, fid) and (p['area'] not in ACTIVE_AREAS or area not in ACTIVE_AREAS):
            raise RuleError('No demotions or call-ups during an active run.')
        if p['area'] in ACTIVE_AREAS and area == 'minors' and protected(repo, fid, p):
            raise RuleError('Tagged/protected players cannot be demoted.')
        if area == 'lineup' and (p['kind'] != 'hitter' or position not in legal_positions(p) or not 1 <= order <= 9):
            raise RuleError('Choose a legal hitting position and batting order 1–9.')
        if area == 'bench' and p['kind'] != 'hitter':
            raise RuleError('Bench players must be hitters.')
        if area in ['rotation', 'bullpen']:
            required = 'SP' if area == 'rotation' else 'RP'
            if p['kind'] != 'pitcher' or position != required or required not in legal_positions(p):
                raise RuleError('Choose a legal pitching role.')
        before = dict(p)
        p.update(area=area, position=position, order=order)
        repo.put('players', p)
        audit(repo, fid, 'arrange', before, p, 'Roster arrangement')

def swap(repo, fid, first_id, second_id):
    with repo.transaction():
        first, second = repo.get('players', first_id), repo.get('players', second_id)
        if not first or not second or first_id == second_id:
            raise RuleError('Select two different players.')
        a, b = (first['area'], first['position'], first['order']), (second['area'], second['position'], second['order'])
        arrange(repo, fid, first_id, *b)
        arrange(repo, fid, second_id, *a)

```

### random-franchise/services/roster_validator.py

```python
from models.domain import ACTIVE_AREAS, ValidationResult
from services.franchise_service import settings

def legal_positions(player):
    if player['kind'] == 'pitcher':
        return {player['primary']} | set(player.get('secondary', []))
    return {player['primary'], 'DH'} | set(player.get('secondary', []))

def validate(repo, fid, check_tasks=True):
    cfg = settings(repo, fid)
    active = [p for p in repo.list('players', fid) if p['area'] in ACTIVE_AREAS]
    errors = []
    lineup = [p for p in active if p['area'] == 'lineup']
    required = {'C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH'}
    if len(lineup) != 9 or {p['position'] for p in lineup} != required:
        errors.append('Lineup must have one player in each of C, 1B, 2B, 3B, SS, LF, CF, RF, DH.')
    if sorted(p['order'] for p in lineup) != list(range(1, 10)):
        errors.append('Batting order must use 1–9 exactly once.')
    for area, key in [('bench', 'bench_size'), ('rotation', 'rotation_size'), ('bullpen', 'bullpen_size')]:
        if len([p for p in active if p['area'] == area]) != cfg[key]:
            errors.append(f'{area.title()} requires {cfg[key]} players.')
    for area in ['rotation', 'bullpen']:
        orders = [p['order'] for p in active if p['area'] == area]
        if len(orders) != len(set(orders)):
            errors.append(f'{area.title()} orders must be unique.')
    for p in active:
        if p['area'] == 'lineup' and (p['kind'] != 'hitter' or p['position'] not in legal_positions(p)):
            errors.append(f"{p['name']}: illegal lineup assignment.")
        if p['area'] == 'bench' and p['kind'] != 'hitter':
            errors.append(f"{p['name']}: bench requires a hitter.")
        if p['area'] in ['rotation', 'bullpen'] and (p['kind'] != 'pitcher' or p['position'] not in legal_positions(p)):
            errors.append(f"{p['name']}: illegal pitching assignment.")
        if p['area'] == 'rotation' and p['position'] != 'SP':
            errors.append(f"{p['name']}: rotation must be SP.")
        if p['area'] == 'bullpen' and p['position'] != 'RP':
            errors.append(f"{p['name']}: bullpen must be RP.")
        if p.get('eligibility') != 'legal':
            errors.append(f"{p['name']}: Event eligibility is {p.get('eligibility', 'unknown')}.")
        for field in ['team', 'series', 'primary', 'bat', 'throw']:
            value = p.get(field, '')
            allowed, denied = cfg.get(f'allowed_{field}', []), cfg.get(f'disallowed_{field}', [])
            if (allowed and value not in allowed) or value in denied:
                errors.append(f"{p['name']}: {field} does not meet Event restrictions.")
    if cfg.get('ovr_cap') and active and sum(p['ovr'] for p in active) / len(active) > cfg['ovr_cap']:
        errors.append('Average active-roster OVR exceeds the configured cap (manual in-game verification still required).')
    if check_tasks and any(m['status'] == 'pending' and m.get('critical', False) for m in repo.list('moves', fid)):
        errors.append('Resolve critical offseason obligations first.')
    if check_tasks and any(c['status'] == 'awaiting_manual' for c in repo.list('challenges', fid)):
        errors.append('Confirm challenges requiring manual evidence first.')
    return ValidationResult(tuple(errors))

```

### random-franchise/services/stat_engine.py

```python
from models.domain import RuleError

HITTER = ['games', 'pa', 'ab', 'h', 'doubles', 'triples', 'hr', 'rbi', 'r', 'bb', 'so', 'sb', 'cs', 'hbp', 'sf']
PITCHER = ['games', 'starts', 'outs', 'ha', 'r', 'er', 'bb', 'so', 'hra', 'w', 'l', 'sv', 'holds']

def validate_line(kind: str, line: dict) -> dict:
    keys = HITTER if kind == 'hitter' else PITCHER
    values = {}
    for key in keys:
        value = line.get(key, 0)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 or int(value) != value:
            raise RuleError(f'{key} must be a nonnegative integer.')
        values[key] = int(value)
    if values['games'] > 1:
        raise RuleError('One stat line is for at most one game.')
    if kind == 'hitter':
        if values['h'] > values['ab'] or values['doubles'] + values['triples'] + values['hr'] > values['h']:
            raise RuleError('Hits and extra-base hits are inconsistent.')
        if values['pa'] < values['ab'] + values['bb'] + values['hbp'] + values['sf'] or values['so'] > values['ab']:
            raise RuleError('Plate appearances / strikeouts are inconsistent.')
    elif values['er'] > values['r'] or values['hra'] > values['ha']:
        raise RuleError('Earned runs / home runs allowed are inconsistent.')
    return values

def calculate(kind: str, totals: dict) -> dict:
    result = dict(totals)
    def ratio(numerator, denominator):
        return numerator / denominator if denominator else 0.0
    if kind == 'hitter':
        ab, h = totals.get('ab', 0), totals.get('h', 0)
        bb, hbp, sf = (totals.get(k, 0) for k in ['bb', 'hbp', 'sf'])
        tb = h + totals.get('doubles', 0) + 2 * totals.get('triples', 0) + 3 * totals.get('hr', 0)
        result.update(avg=ratio(h, ab), obp=ratio(h + bb + hbp, ab + bb + hbp + sf), slg=ratio(tb, ab), tb=tb)
        result['ops'] = result['obp'] + result['slg']
    else:
        outs = totals.get('outs', 0)
        result.update(ip=f'{outs // 3}.{outs % 3}', era=ratio(totals.get('er', 0) * 27, outs),
                      whip=ratio((totals.get('ha', 0) + totals.get('bb', 0)) * 3, outs))
    return result

def aggregate(repo, franchise_id: str, player: dict, run_id=None, game_id=None) -> dict:
    keys = HITTER if player['kind'] == 'hitter' else PITCHER
    totals = {key: 0 for key in keys}
    for row in repo.list('stats', franchise_id, run_id):
        if row['player_id'] == player['id'] and (game_id is None or row['game_id'] == game_id):
            for key in keys:
                totals[key] += row['line'].get(key, 0)
    return calculate(player['kind'], totals)

```

### random-franchise/services/wheel_engine.py

```python
import random
from models.domain import RuleError, State, now, uid
from services.game_engine import enqueue
from services.franchise_service import settings
from services.roster_service import target_pool, protected
from services.stat_engine import aggregate
from services.challenge_service import create


def current_job(repo, fid):
    f = repo.get('franchises', fid)
    return f['queue'][0] if f['queue'] else None


def _targets(repo, fid, wedge):
    eligibility = wedge.get('eligibility', {})
    pool = target_pool(repo, fid, eligibility.get('kind'))
    if wedge.get('effect') in ['hot_seat', 'protect', 'challenge', 'arrangement']:
        pool = [p for p in repo.list('players', fid) if p['area'] in ['lineup', 'bench', 'rotation', 'bullpen'] and (not eligibility.get('kind') or p['kind'] == eligibility['kind'])]
    if wedge.get('effect') == 'unprotect':
        pool = [p for p in repo.list('players', fid) if p.get('protected')]
    if eligibility.get('area'):
        pool = [p for p in pool if p['area'] == eligibility['area']]
    if eligibility.get('hot_seat'):
        pool = [p for p in pool if p.get('hot_seat')]
    if eligibility.get('failed_challenge'):
        failed = {c['player_id'] for c in repo.list('challenges', fid) if c['status'] == 'failed'}
        pool = [p for p in pool if p['id'] in failed]
    return pool


def _performance(repo, fid, p):
    f = repo.get('franchises', fid)
    t = aggregate(repo, fid, p, f['current_run'])
    return t.get('ops', 0) if p['kind'] == 'hitter' else -t.get('era', 0)


def available(repo, fid, job):
    wheel = repo.get('wheels', f"{fid}:{job['wheel_id']}")
    if not wheel:
        raise RuleError('Wheel configuration missing.')
    options = []
    if job['wheel_id'] == 'dfa_target':
        pool = sorted(target_pool(repo, fid), key=lambda p: (_performance(repo, fid, p), p['ovr']))[:3]
        return [dict(id=p['id'], text='DFA ' + p['name'], weight=1, active=True, effect='dfa',
                     selector='fixed', target_id=p['id'], eligibility={'needs_target': True}, description='Bottom-three eligible player') for p in pool]
    for w in wheel['wedges']:
        if not settings(repo, fid).get('special_wheels', True) and w.get('follow_up') in ['premium', 'tag_hitter', 'tag_pitcher']:
            continue
        if not w.get('active', True) or w.get('weight', 1) <= 0:
            continue
        if job.get('depth', 0) >= 4 and (w.get('follow_up') or w.get('effect') == 'extra_spin'):
            continue  # bounded recursive bonus chains
        e = w.get('eligibility', {})
        if e.get('kind') and job.get('target'):
            p = repo.get('players', job['target'])
            if p and p['kind'] != e['kind']:
                continue
        if e.get('needs_target') and len(_targets(repo, fid, w)) < w.get('quantity', 1):
            continue
        if e.get('needs_bench') and not any(p['area'] == 'bench' for p in repo.list('players', fid)):
            continue
        if e.get('needs_protection') and not any(p.get('protected') for p in repo.list('players', fid)):
            continue
        options.append(dict(w))
    return options


def _choose_target(repo, fid, wedge, job):
    pool = _targets(repo, fid, wedge)
    if wedge.get('target_id'):
        return next((p for p in pool if p['id'] == wedge['target_id']), None)
    if job.get('target'):
        target = repo.get('players', job['target'])
        if target and (wedge.get('effect') not in ['dfa', 'demote', 'trade'] or not protected(repo, fid, target)):
            return target
    if not pool:
        return None
    selector = wedge.get('selector', 'random')
    if selector == 'lowest':
        return min(pool, key=lambda p: p['ovr'])
    if selector == 'highest':
        return max(pool, key=lambda p: p['ovr'])
    if selector == 'worst':
        return min(pool, key=lambda p: (_performance(repo, fid, p), p['ovr']))
    if selector == 'bottom3':
        pool = sorted(pool, key=lambda p: (_performance(repo, fid, p), p['ovr']))[:3]
    return random.SystemRandom().choice(pool)


def _bank(repo, fid, job, spin, wedge, target):
    key = f"move:{spin['id']}"
    kind = wedge.get('effect', 'acquire')
    repo.put('moves', dict(id=key, franchise_id=fid, run_id=spin['run_id'], game_id=job.get('game_id'),
        created_at=now(), source=job['source'], spin_id=spin['id'], type=kind,
        target=target['id'] if target else None, description=wedge['text'],
        constraints={'instruction': wedge.get('description', wedge['text']), 'branch': list(job.get('constraints', [])),
                     'quantity': wedge.get('quantity', 1)}, status='pending',
        critical=kind in ['dfa', 'demote', 'trade', 'tag'], resolution_notes=''))


def spin(repo, fid, job_id):
    with repo.transaction():
        existing = repo.get('spins', job_id)
        if existing:
            if existing['franchise_id'] != fid:
                raise RuleError('Spin belongs to another franchise.')
            return existing
        f = repo.get('franchises', fid)
        job = current_job(repo, fid)
        if f['state'] != State.WHEEL or not job or job['id'] != job_id:
            raise RuleError('This spin is not the current required action.')
        options = available(repo, fid, job)
        # Impossible nested branch: preserve parent result and only void this child.
        if not options:
            outcome = dict(id='impossible', text='No eligible options — branch deferred', effect='deferred')
        else:
            outcome = random.SystemRandom().choices(options, weights=[w.get('weight', 1) for w in options], k=1)[0]
        target = _choose_target(repo, fid, outcome, job)
        record = dict(id=job_id, franchise_id=fid, run_id=f['current_run'], game_id=job.get('game_id'),
            wheel_id=job['wheel_id'], result=outcome, available=options, target=target['id'] if target else None,
            created_at=now(), reroll_reason='Impossible child only' if not options else job.get('reroll_reason'),
            admin_note='', job=dict(job), parent_spin=job.get('parent_spin'))
        repo.put('spins', record)
        return record


def continue_spin(repo, fid, job_id, acknowledged=False):
    with repo.transaction():
        f = repo.get('franchises', fid)
        job = current_job(repo, fid)
        if not job or job['id'] != job_id:
            return  # repeated Continue is harmless
        s = repo.get('spins', job_id)
        if not s:
            raise RuleError('Spin the wheel first.')
        w = s['result']
        effect = w.get('effect', 'acquire')
        if effect == 'arrangement' and not acknowledged:
            raise RuleError('Apply the legal arrangement in Roster Manager and confirm it before continuing.')
        f['queue'].pop(0)
        target = repo.get('players', s['target']) if s.get('target') else None
        follow = w.get('follow_up')
        if follow:
            children = w.get('quantity', 1)
            for _ in range(children):
                enqueue(f, follow, job['source'], job.get('game_id'), job.get('target'), job.get('depth', 0) + 1)
                f['queue'][-1]['constraints'] = job.get('constraints', []) + [w['text']]
                f['queue'][-1]['parent_spin'] = s['id']
            # Keep nested branch before unrelated milestone jobs.
            new = f['queue'][-children:]
            f['queue'] = new + f['queue'][:-children]
        elif effect == 'extra_spin':
            for _ in range(w.get('quantity', 1)):
                enqueue(f, job['wheel_id'], job['source'], job.get('game_id'), job.get('target'), job.get('depth', 0) + 1)
        elif effect == 'protect' and 'Next Run' in w['text']:
            _bank(repo, fid, job, s, w, target)
        elif effect in ['hot_seat', 'protect', 'unprotect']:
            if target:
                target['hot_seat' if effect == 'hot_seat' else 'protected'] = effect != 'unprotect'
                repo.put('players', target)
                if effect == 'hot_seat' and w.get('quantity', 1) > 1:
                    extra = [p for p in _targets(repo, fid, w) if p['id'] != target['id']][:w['quantity'] - 1]
                    for p in extra:
                        p['hot_seat'] = True
                        repo.put('players', p)
        elif effect == 'challenge' and target:
            create(repo, fid, f['current_run'], target['id'], w['text'], w.get('metric'), w.get('threshold', 1),
                   w.get('scope', 'next_game'), w.get('reward', 'protection'), job.get('game_id'))
        elif effect == 'tag' and target:
            from services.franchise_tag_service import grant
            if grant(repo, fid, target['id'], source=w['text']) == 'cap_decision_required':
                _bank(repo, fid, job, s, w, target)
        elif effect == 'arrangement':
            from services.franchise_service import audit
            audit(repo, fid, 'manual_wheel_arrangement', None, w, 'Creator confirms legal in-game arrangement', f['current_run'])
        elif effect not in ['none', 'challenge']:
            _bank(repo, fid, job, s, w, target)
            if effect == 'deferred':
                m = repo.get('moves', f"move:{s['id']}")
                m.update(status='deferred', critical=False)
                repo.put('moves', m)
        f['state'] = State.WHEEL if f['queue'] else f['return_state']
        repo.put('franchises', f)


def retry_impossible_branch(repo, fid, job_id):
    """Only an impossible nested child may be retried, and only once eligible options exist."""
    with repo.transaction():
        f = repo.get('franchises', fid)
        job = current_job(repo, fid)
        original = repo.get('spins', job_id)
        if not job or job['id'] != job_id or not original or original['result']['id'] != 'impossible' or not job.get('parent_spin'):
            raise RuleError('Only an impossible nested branch has retry permission.')
        if not available(repo, fid, job):
            raise RuleError('This branch still has no eligible options. Defer it instead.')
        replacement = dict(job, id=uid(), reroll_reason='Retry of impossible nested branch', retried_spin=job_id)
        f['queue'][0] = replacement
        repo.put('franchises', f)
        return replacement['id']

```

### random-franchise/tests/conftest.py

```python
import pytest
from repositories.sqlite import SQLiteRepository
from services.demo import load_demo

@pytest.fixture
def repo(tmp_path):
    r=SQLiteRepository(tmp_path/'test.db')
    yield r
    r.close()

@pytest.fixture
def demo(repo):
    return repo,load_demo(repo)

```

### random-franchise/tests/test_rules.py

```python
import json
import sqlite3
import pytest
from models.domain import RuleError, State, uid
from services.game_engine import record_game,correct_game,start_run
from services.roster_service import add_player,remove_player,swap,arrange,target_pool,locked
from services.roster_validator import validate
from services.franchise_service import create_franchise,settings,save_settings
from services.franchise_tag_service import grant
from services.wheel_engine import spin,continue_spin,available,current_job
from services.offseason_service import confirm_end,select_mvp,progress,resolve_move,finish_validation
from services.stat_engine import calculate,aggregate
from services.import_export import export_roster,import_roster
from services.challenge_service import create


def one_wedge(repo,fid,wid,**changes):
    w=repo.get('wheels',f'{fid}:{wid}')
    wedge=dict(id='fixed',text='Fixed result',weight=1,active=True,effect='none',eligibility={})
    wedge.update(changes);w['wedges']=[wedge];repo.put('wheels',w)


def drain(repo,fid):
    for _ in range(30):
        job=current_job(repo,fid)
        if not job:return
        spin(repo,fid,job['id']);continue_spin(repo,fid,job['id'],True)
    raise AssertionError('Queue did not finish')


def lose_twice(repo,fid):
    one_wedge(repo,fid,'hot_seat')
    record_game(repo,fid,uid(),'L');drain(repo,fid);record_game(repo,fid,uid(),'L')


def test_active_personnel_lock(demo):
    repo,fid=demo;p=repo.list('players',fid)[1]
    with pytest.raises(RuleError):add_player(repo,fid,{'name':'External'})
    with pytest.raises(RuleError):remove_player(repo,fid,p['id'])
    with pytest.raises(RuleError):arrange(repo,fid,p['id'],'minors',p['position'],1)
    minors=next(p for p in repo.list('players',fid) if p['area']=='minors')
    with pytest.raises(RuleError):arrange(repo,fid,minors['id'],'bench','SS',1)


def test_legal_starter_bench_and_position_swaps(demo):
    repo,fid=demo;players=repo.list('players',fid)
    starter=next(p for p in players if p['area']=='lineup' and p['position']=='CF')
    bench=next(p for p in players if p['area']=='bench')
    swap(repo,fid,starter['id'],bench['id'])
    assert repo.get('players',bench['id'])['area']=='lineup'
    assert validate(repo,fid,False).valid
    left=next(p for p in players if p['position']=='LF' and p['area']=='lineup')
    right=next(p for p in players if p['position']=='RF' and p['area']=='lineup')
    swap(repo,fid,left['id'],right['id'])
    assert repo.get('players',left['id'])['position']=='RF'


def test_illegal_swap_rolls_back(demo):
    repo,fid=demo;players=repo.list('players',fid)
    pitcher=next(p for p in players if p['kind']=='pitcher');hitter=players[0]
    before=repo.get('players',pitcher['id'])
    with pytest.raises(RuleError):swap(repo,fid,pitcher['id'],hitter['id'])
    assert repo.get('players',pitcher['id'])==before


def test_first_loss_and_second_loss(demo):
    repo,fid=demo;one_wedge(repo,fid,'hot_seat')
    record_game(repo,fid,uid(),'L')
    assert repo.get('franchises',fid)['state']==State.WHEEL
    assert current_job(repo,fid)['wheel_id']=='hot_seat'
    assert locked(repo,fid)
    with pytest.raises(RuleError):record_game(repo,fid,uid(),'W')
    drain(repo,fid);record_game(repo,fid,uid(),'L')
    assert repo.get('franchises',fid)['state']==State.ENDED
    assert not locked(repo,fid)
    with pytest.raises(RuleError):record_game(repo,fid,uid(),'W')
    assert len(repo.list('snapshots',fid))==2


def test_move_cannot_resolve_during_run(demo):
    repo,fid=demo;m=repo.list('moves',fid)[0]
    with pytest.raises(RuleError):resolve_move(repo,fid,m['id'],'resolved','Confirmed',new_player={'name':'A'},confirmed=True)
    assert repo.get('moves',m['id'])['status']=='pending'


def test_game_duplicate_and_milestone_idempotent(demo):
    repo,fid=demo;record_game(repo,fid,uid(),'W')
    gid=uid();record_game(repo,fid,gid,'W');record_game(repo,fid,gid,'W')
    assert len(repo.list('games',fid))==2
    assert len([r for r in repo.list('rewards',fid) if r['id'].startswith('milestone:')])==1
    assert len(repo.get('franchises',fid)['queue'])==1


def test_tags_excluded_and_fourth_tag_decision(demo):
    repo,fid=demo;players=repo.list('players',fid)
    assert players[0]['id'] not in {p['id'] for p in target_pool(repo,fid)}
    assert grant(repo,fid,players[1]['id'])=='granted'
    assert grant(repo,fid,players[2]['id'])=='granted'
    assert grant(repo,fid,players[3]['id'])=='cap_decision_required'
    assert grant(repo,fid,players[3]['id'],players[0]['id'])=='granted'
    assert players[3]['id'] not in {p['id'] for p in target_pool(repo,fid)}
    assert players[0]['id'] in {p['id'] for p in target_pool(repo,fid)}


def test_nested_wheel_and_immutable_spins(demo):
    repo,fid=demo;one_wedge(repo,fid,'front_office',follow_up='position');one_wedge(repo,fid,'position',effect='acquire')
    record_game(repo,fid,uid(),'W');record_game(repo,fid,uid(),'W')
    job=current_job(repo,fid);first=spin(repo,fid,job['id'])
    assert spin(repo,fid,job['id'])==first
    continue_spin(repo,fid,job['id'])
    assert current_job(repo,fid)['wheel_id']=='position'
    drain(repo,fid)
    assert len(repo.list('spins',fid))==2
    assert repo.list('moves',fid)[-1]['constraints']['branch']==['Fixed result']
    with pytest.raises(sqlite3.IntegrityError):repo.delete('spins',first['id'])
    with pytest.raises(sqlite3.IntegrityError):repo.put('spins',first)


def test_impossible_nested_branch_preserves_parent(demo):
    repo,fid=demo;one_wedge(repo,fid,'front_office',follow_up='position');one_wedge(repo,fid,'position',active=False)
    record_game(repo,fid,uid(),'W');record_game(repo,fid,uid(),'W')
    parent=current_job(repo,fid);original=spin(repo,fid,parent['id']);continue_spin(repo,fid,parent['id'])
    child=current_job(repo,fid);result=spin(repo,fid,child['id']);continue_spin(repo,fid,child['id'])
    assert result['result']['id']=='impossible'
    assert repo.get('spins',parent['id'])==original
    assert len(repo.list('spins',fid))==2
    assert repo.list('moves',fid)[-1]['status']=='deferred'


def test_zero_two_meltdown(demo):
    repo,fid=demo;lose_twice(repo,fid)
    confirm_end(repo,fid);select_mvp(repo,fid,repo.list('players',fid)[0]['id'])
    one_wedge(repo,fid,'mvp');drain(repo,fid);progress(repo,fid)
    one_wedge(repo,fid,'elimination');drain(repo,fid);progress(repo,fid)
    assert current_job(repo,fid)['wheel_id']=='meltdown'


def test_hitting_and_pitching_rates():
    h=calculate('hitter',dict(ab=10,h=4,doubles=1,triples=0,hr=1,bb=2,hbp=1,sf=1))
    assert h['avg']==.4 and h['slg']==.8 and h['obp']==.5 and h['ops']==1.3
    p=calculate('pitcher',dict(outs=8,er=2,ha=3,bb=1))
    assert p['ip']=='2.2' and p['era']==6.75 and p['whip']==1.5
    assert calculate('pitcher',{'outs':1})['ip']=='0.1'
    assert calculate('pitcher',{'outs':2})['ip']=='0.2'
    assert calculate('pitcher',{'outs':0})['era']==0


def test_stat_corrections_no_duplicate_rewards(demo):
    repo,fid=demo;p=repo.list('players',fid)[0]
    gid=uid();record_game(repo,fid,gid,'W',[dict(player_id=p['id'],line=dict(games=1,pa=3,ab=3,h=1))])
    line=[dict(player_id=p['id'],line=dict(games=1,pa=3,ab=3,h=2))]
    correct_game(repo,fid,gid,line,'Fix a missed hit');correct_game(repo,fid,gid,line,'Verify')
    assert aggregate(repo,fid,p)['h']==2
    assert len(repo.list('games',fid))==1
    assert len(repo.list('rewards',fid))==1
    assert len([c for c in repo.list('corrections',fid) if c['action']=='correct_game'])==2


def test_outcome_correction_retracts_unspun_milestone(demo):
    repo,fid=demo;record_game(repo,fid,uid(),'W');gid=uid();record_game(repo,fid,gid,'W')
    correct_game(repo,fid,gid,[],'It was a loss','L')
    rewards=[r for r in repo.list('rewards',fid) if r['id'].startswith('milestone:')]
    assert rewards[0]['status']=='revoked'
    assert current_job(repo,fid)['wheel_id']=='hot_seat'
    correct_game(repo,fid,gid,[],'Actually a win','W')
    assert len(repo.list('rewards',fid))==1
    assert current_job(repo,fid)['wheel_id']=='front_office'


def test_outcome_edit_after_spin_rejected(demo):
    repo,fid=demo;gid=uid();record_game(repo,fid,gid,'L');job=current_job(repo,fid);spin(repo,fid,job['id'])
    with pytest.raises(RuleError):correct_game(repo,fid,gid,[],'Change result','W')
    correct_game(repo,fid,gid,[],'Stats only')


def test_validation_blocks_illegal_next_run(demo):
    repo,fid=demo;lose_twice(repo,fid)
    f=repo.get('franchises',fid);f['state']=State.READY;repo.put('franchises',f)
    p=repo.list('players',fid)[0];p['eligibility']='illegal';repo.put('players',p)
    with pytest.raises(RuleError):start_run(repo,fid)


def test_invalid_stat_transaction_has_no_partial_game(demo):
    repo,fid=demo;p=repo.list('players',fid)[0];gid=uid()
    with pytest.raises(RuleError):record_game(repo,fid,gid,'W',[dict(player_id=p['id'],line=dict(games=1,ab=1,pa=1,h=2))])
    assert repo.get('games',gid) is None
    assert repo.get('runs',repo.get('franchises',fid)['current_run'])['wins']==0


def test_import_export_atomic(repo):
    fid=create_franchise(repo,'Test','Event')
    raw=json.dumps([dict(name='One',ovr=80),dict(name='',ovr=80)])
    with pytest.raises(RuleError):import_roster(repo,fid,raw,'json')
    assert repo.list('players',fid)==[]
    import_roster(repo,fid,json.dumps([dict(name='One',ovr=80,secondary=['CF'])]),'json')
    another=create_franchise(repo,'Other','Event');import_roster(repo,another,export_roster(repo,fid,'csv'),'csv')
    assert repo.list('players',another)[0]['secondary']==['CF']


def test_dfa_target_is_dynamic_bottom_three(demo):
    repo,fid=demo;options=available(repo,fid,dict(wheel_id='dfa_target',depth=1))
    assert len(options)==3
    assert repo.list('tags',fid)[0]['player_id'] not in {w['target_id'] for w in options}


def test_settings_cannot_change_mid_run(demo):
    repo,fid=demo
    with pytest.raises(RuleError):save_settings(repo,fid,settings(repo,fid))


def test_no_hitter_auto_tag_idempotent(demo):
    repo,fid=demo;p=next(p for p in repo.list('players',fid) if p['kind']=='pitcher')
    line=dict(player_id=p['id'],line={'games':1,'outs':9},flags={'no_hitter':True})
    gid=uid();record_game(repo,fid,gid,'W',[line]);correct_game(repo,fid,gid,[line],'Verify')
    assert len([t for t in repo.list('tags',fid) if t['player_id']==p['id'] and t['active']])==1


def test_next_run_challenge_binds_to_next_entry(demo):
    repo,fid=demo;lose_twice(repo,fid);f=repo.get('franchises',fid);p=repo.list('players',fid)[0]
    cid=create(repo,fid,f['current_run'],p['id'],'5 hits next run','h',5,'next_run','tag')
    assert repo.get('challenges',cid)['status']=='waiting_next_run'
    f['state']=State.READY;repo.put('franchises',f);rid=start_run(repo,fid)
    assert repo.get('challenges',cid)['run_id']==rid
    assert repo.get('challenges',cid)['status']=='active'


def test_sqlite_backup_contains_committed_data(demo,tmp_path):
    repo,fid=demo;path=tmp_path/'backup.db';path.write_bytes(repo.backup_bytes())
    con=sqlite3.connect(path)
    assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert con.execute('SELECT count(*) FROM players').fetchone()[0]==27
    con.close()


def test_retry_only_impossible_child_keeps_parent(demo):
    from services.wheel_engine import retry_impossible_branch
    repo,fid=demo;one_wedge(repo,fid,'front_office',follow_up='position');one_wedge(repo,fid,'position',active=False)
    record_game(repo,fid,uid(),'W');record_game(repo,fid,uid(),'W')
    parent=current_job(repo,fid);parent_result=spin(repo,fid,parent['id'])
    with pytest.raises(RuleError):retry_impossible_branch(repo,fid,parent['id'])
    continue_spin(repo,fid,parent['id']);child=current_job(repo,fid);spin(repo,fid,child['id'])
    with pytest.raises(RuleError):retry_impossible_branch(repo,fid,child['id'])
    one_wedge(repo,fid,'position',effect='acquire')
    next_id=retry_impossible_branch(repo,fid,child['id']);spin(repo,fid,next_id);continue_spin(repo,fid,next_id)
    assert repo.get('spins',parent['id'])==parent_result
    assert len(repo.list('spins',fid))==3
    assert repo.get('spins',next_id)['parent_spin']==parent['id']


def test_complete_offseason_and_next_run(demo):
    repo,fid=demo;lose_twice(repo,fid)
    confirm_end(repo,fid);select_mvp(repo,fid,repo.list('players',fid)[0]['id'])
    one_wedge(repo,fid,'mvp');drain(repo,fid);progress(repo,fid)
    one_wedge(repo,fid,'elimination');drain(repo,fid);progress(repo,fid)
    one_wedge(repo,fid,'meltdown');drain(repo,fid)
    assert repo.get('franchises',fid)['state']==State.MOVES
    progress(repo,fid);progress(repo,fid);finish_validation(repo,fid)
    rid=start_run(repo,fid);r=repo.get('runs',rid)
    assert r['number']==2 and r['wins']==0 and r['losses']==0


def test_full_backup_restore_only_into_empty(demo,tmp_path):
    from services.backup_service import restore_empty
    from repositories.sqlite import SQLiteRepository
    repo,fid=demo;record_game(repo,fid,uid(),'W');data=repo.backup_bytes()
    destination=SQLiteRepository(tmp_path/'restored.db')
    assert restore_empty(destination,data)==1
    assert destination.get('franchises',fid)==repo.get('franchises',fid)
    assert destination.list('games',fid)==repo.list('games',fid)
    with pytest.raises(RuleError):restore_empty(destination,data)
    destination.close()


def test_pending_removal_can_be_canceled_only_with_award(demo):
    repo,fid=demo;lose_twice(repo,fid)
    f=repo.get('franchises',fid);f['state']=State.MOVES;repo.put('franchises',f)
    target=target_pool(repo,fid)[0]
    removal=dict(id=uid(),franchise_id=fid,run_id=f['current_run'],type='dfa',target=target['id'],status='pending',critical=True,description='DFA target',source='elimination',constraints={})
    reward=dict(id=uid(),franchise_id=fid,run_id=f['current_run'],type='save_dfa',status='pending',critical=False,description='Save Pending DFA',source='premium',constraints={})
    repo.put('moves',removal);repo.put('moves',reward)
    with pytest.raises(RuleError):resolve_move(repo,fid,removal['id'],'canceled','I just want to skip it',confirmed=True)
    resolve_move(repo,fid,reward['id'],'resolved','Use earned save',confirmed=True,cancel_move_id=removal['id'])
    assert repo.get('moves',removal['id'])['status']=='canceled'
    assert repo.get('players',target['id'])['area']==target['area']


def test_audited_target_cannot_be_arbitrarily_changed(demo):
    repo,fid=demo;lose_twice(repo,fid)
    f=repo.get('franchises',fid);f['state']=State.MOVES;repo.put('franchises',f)
    pool=target_pool(repo,fid)
    m=dict(id=uid(),franchise_id=fid,run_id=f['current_run'],type='dfa',target=pool[0]['id'],status='pending',critical=True,description='DFA selected player',source='elimination',constraints={})
    repo.put('moves',m)
    with pytest.raises(RuleError):resolve_move(repo,fid,m['id'],'resolved','Different player',target_id=pool[1]['id'],confirmed=True)
    resolve_move(repo,fid,m['id'],'resolved','Apply audited target',confirmed=True)
    assert repo.get('players',pool[0]['id'])['area']=='dfa'


def test_trade_is_atomic_when_incoming_card_invalid(demo):
    repo,fid=demo;lose_twice(repo,fid)
    f=repo.get('franchises',fid);f['state']=State.MOVES;repo.put('franchises',f)
    target=target_pool(repo,fid)[0]
    m=dict(id=uid(),franchise_id=fid,run_id=f['current_run'],type='trade',target=target['id'],status='pending',critical=True,description='Trade',source='wheel',constraints={})
    repo.put('moves',m)
    with pytest.raises(RuleError):resolve_move(repo,fid,m['id'],'resolved','Bad incoming card',new_player={'name':''},confirmed=True)
    assert repo.get('players',target['id'])['area']==target['area']
    assert repo.get('moves',m['id'])['status']=='pending'

```

### random-franchise/tests/test_ui.py

```python
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from repositories.sqlite import SQLiteRepository
from services.demo import load_demo

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('page',['app.py']+[str(p.relative_to(ROOT)) for p in sorted((ROOT/'pages').glob('*.py'))])
def test_pages_load_without_exception(tmp_path,monkeypatch,page):
    path=tmp_path/'ui.db';monkeypatch.setenv('RANDOM_FRANCHISE_DB',str(path))
    repo=SQLiteRepository(path);load_demo(repo);repo.close()
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=15).run()
    if page != 'app.py':
        app.switch_page(page).run()
    assert not app.exception,[x.message for x in app.exception]


def test_home_can_create_demo(tmp_path,monkeypatch):
    monkeypatch.setenv('RANDOM_FRANCHISE_DB',str(tmp_path/'ui.db'))
    app=AppTest.from_file(str(ROOT/'app.py')).run()
    next(b for b in app.button if b.label=='Load Demo Franchise').click().run()
    assert not app.exception
    repo=SQLiteRepository(tmp_path/'ui.db')
    assert len(repo.list('franchises'))==1
    assert len(repo.list('players'))==27
    repo.close()

@pytest.mark.parametrize('state',['SETUP','AWAITING_WHEEL','RUN_ENDED','SELECTING_RUN_MVP','PROCESSING_ELIMINATION','PROCESSING_MELTDOWN','RESOLVING_BANKED_MOVES','ROSTER_RECONSTRUCTION','ROSTER_VALIDATION','READY_FOR_NEXT_RUN'])
def test_workflow_pages_for_each_state(tmp_path,monkeypatch,state):
    from services.game_engine import enqueue
    path=tmp_path/'states.db';monkeypatch.setenv('RANDOM_FRANCHISE_DB',str(path))
    repo=SQLiteRepository(path);fid=load_demo(repo);f=repo.get('franchises',fid)
    f['state']=state
    if state not in ['SETUP','AWAITING_WHEEL']:
        run=repo.get('runs',f['current_run']);run.update(wins=0,losses=2,ended_at='2026-10-08T00:00:00Z');repo.put('runs',run)
    if state=='AWAITING_WHEEL':enqueue(f,'front_office','ui test')
    repo.put('franchises',f);repo.close()
    app=AppTest.from_file(str(ROOT/'app.py')).run()
    for page in ['pages/1_Dashboard.py','pages/4_Wheel_Room.py','pages/5_Banked_Moves.py','pages/6_Offseason.py','pages/9_Settings.py']:
        app.switch_page(page).run()
        assert not app.exception,[x.message for x in app.exception]


def test_review_save_and_hot_seat_ui(tmp_path,monkeypatch):
    path=tmp_path/'flow.db';monkeypatch.setenv('RANDOM_FRANCHISE_DB',str(path))
    repo=SQLiteRepository(path);load_demo(repo);repo.close()
    app=AppTest.from_file(str(ROOT/'app.py')).run().switch_page('pages/3_Game_Entry.py').run()
    next(s for s in app.selectbox if s.label=='Result').select('L')
    next(b for b in app.button if b.label=='Review game').click().run()
    next(b for b in app.button if b.label=='Confirm and save once').click().run()
    assert not app.exception
    repo=SQLiteRepository(path);fid=repo.list('franchises')[0]['id']
    assert len(repo.list('games',fid))==1
    repo.close()
    app.switch_page('pages/4_Wheel_Room.py').run()
    next(b for b in app.button if b.label=='Spin required wheel').click().run()
    assert not app.exception

```

### random-franchise/ui/__init__.py

```python

```

### random-franchise/ui/banked_moves.py

```python
import json
import streamlit as st
from services.offseason_service import resolve_move
from services.roster_service import locked
from models.domain import State
from ui.common import table,navigate

def render(repo,f):
    moves=repo.list('moves',f['id'])
    table([{'ID':m['id'],'Source':m['source'],'Run':repo.get('runs',m['run_id'])['number'] if m.get('run_id') else '',
        'Game':repo.get('games',m['game_id'])['number'] if m.get('game_id') else '',
        'Type':m['type'],'Description':m['description'],'Constraints':json.dumps(m.get('constraints',{})),
        'Status':m['status'],'Critical':m.get('critical',False),'Timing':'Offseason only'} for m in moves])
    if locked(repo,f['id']):st.info('Moves are banked until the run ends.');return
    if f['state'] not in [State.MOVES,State.REBUILD,State.VALIDATION]:
        st.info('Confirm Run MVP and complete required offseason wheels first.');navigate('Continue offseason','Offseason');return
    pending=[m for m in moves if m['status'] in ['pending','deferred']]
    if not pending:return
    mid=st.selectbox('Move to resolve',[m['id'] for m in pending],format_func=lambda i:next(m['description'] for m in pending if m['id']==i))
    m=repo.get('moves',mid)
    players=repo.list('players',f['id']);ids=[p['id'] for p in players]
    labels={p['id']:p['name']+' · '+p['area'] for p in players}
    st.info(json.dumps(m.get('constraints',{}),indent=2))
    with st.form('resolve:'+mid):
        action=st.selectbox('Resolution',['resolved','deferred','canceled'])
        target=st.selectbox('Target / replacement / tag recipient (if needed)',[None]+ids,
                            index=(ids.index(m['target'])+1) if m.get('target') in ids else 0,
                            format_func=lambda i:labels.get(i,'Use original target / no target'))
        replacement=st.selectbox('Replace existing tag holder (only at tag cap)',[None]+ids,format_func=lambda i:labels.get(i,'No replacement'))
        cancel_id=None
        if m['type'] in ['cancel_elimination', 'save_dfa']:
            eligible=[x for x in moves if x['run_id']==m['run_id'] and x['status']=='pending' and x['type'] in (['dfa'] if m['type']=='save_dfa' else ['dfa','demote','trade'])]
            cancel_id=st.selectbox('Consequence to cancel',[None]+[x['id'] for x in eligible],format_func=lambda i:next((x['description'] for x in eligible if x['id']==i),'Choose a consequence'))
        new=None
        if m['type'] in ['acquire','trade']:
            st.caption('Enter incoming cards as JSON. Confirm the wheel’s external constraints yourself. Cards default to minors until arranged.')
            template=[dict(name='New Card',version='Base',ovr=80,primary='CF',secondary=['LF','RF'],kind='hitter',area='minors',position='CF',order=1,eligibility='legal')]
            incoming=st.text_area('Incoming card(s) JSON',value=json.dumps(template,indent=2),height=230)
        notes=st.text_area('Resolution notes / external-constraint verification')
        confirm=st.checkbox('I confirm the selected action, targets, and qualifying incoming cards.')
        if st.form_submit_button('Apply offseason resolution',type='primary'):
            if m['type'] in ['acquire','trade'] and action=='resolved':
                try:
                    parsed=json.loads(incoming)
                    new=parsed[0] if m['type']=='trade' and isinstance(parsed,list) and len(parsed)==1 else parsed
                except (ValueError,IndexError):
                    st.error('Incoming JSON is invalid.');return
            resolve_move(repo,f['id'],mid,action,notes,target,new,replacement,confirm,cancel_id);st.rerun()

```

### random-franchise/ui/common.py

```python
import hmac
import os
from pathlib import Path
import streamlit as st
from models.domain import RuleError, State
from repositories.sqlite import SQLiteRepository
from services.roster_service import locked

ROOT = Path(__file__).resolve().parents[1]
PAGE_PATHS = {'Dashboard':'pages/1_Dashboard.py','Roster Manager':'pages/2_Roster_Manager.py',
    'Game Entry':'pages/3_Game_Entry.py','Wheel Room':'pages/4_Wheel_Room.py','Banked Moves':'pages/5_Banked_Moves.py',
    'Offseason':'pages/6_Offseason.py','Player Stats':'pages/7_Player_Stats.py','Franchise History':'pages/8_Franchise_History.py',
    'Settings':'pages/9_Settings.py','Creator OBS View':'pages/10_Creator_OBS_View.py'}

def repo_path():
    return os.environ.get('RANDOM_FRANCHISE_DB', str(ROOT/'data'/'random_franchise.db'))

def authorize():
    password = os.environ.get('RANDOM_FRANCHISE_PASSWORD', '')
    try:
        password = st.secrets.get('app_password', password)
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        pass
    if password and not st.session_state.get('authenticated'):
        typed = st.text_input('App password', type='password')
        if st.button('Unlock'):
            if hmac.compare_digest(typed, password):
                st.session_state['authenticated'] = True
                st.rerun()
            st.error('Incorrect password.')
        st.stop()

def context(title, obs=False):
    st.set_page_config(page_title='Random Franchise · '+title,page_icon='⚾',layout='wide')
    authorize()
    repo = SQLiteRepository(repo_path())
    rows = repo.list('franchises')
    if not obs:
        st.sidebar.title('⚾ Random Franchise')
    if not rows:
        return repo, None
    ids = [r['id'] for r in rows]
    if st.session_state.get('selected_franchise') not in ids:
        st.session_state['selected_franchise'] = ids[0]
    chosen = st.sidebar.selectbox('Franchise',ids,format_func=lambda i:next(r['name'] for r in rows if r['id']==i),key='selected_franchise')
    f = repo.get('franchises',chosen)
    if not obs:
        st.title(title)
        run=repo.get('runs',f['current_run']) if f['current_run'] else None
        st.caption(f"{f['name']} · {f['event']} · {f['state']} · {'🔒 Roster locked' if locked(repo,chosen) else 'Roster unlocked'}")
        if run:
            st.markdown(f"**Run {run['number']} · {run['wins']}–{run['losses']}**")
    return repo,f

def run_page(title, renderer, obs=False):
    repo,f=context(title,obs)
    try:
        if f:
            renderer(repo,f)
        else:
            st.info('Create a franchise or load the demo on the Home page.')
            st.page_link('app.py',label='Open Home')
    except RuleError as exc:
        st.error(str(exc))
    finally:
        repo.close()

def navigate(label,key):
    st.page_link(PAGE_PATHS[key],label=label)

def table(rows):
    if rows:
        st.dataframe(rows,hide_index=True,width='stretch')
    else:
        st.caption('No entries yet.')

def badges(repo,fid,p):
    parts=[]
    if any(t['player_id']==p['id'] and t['active'] for t in repo.list('tags',fid)):parts.append('🔒 Franchise Tag')
    if p.get('protected'):parts.append('🛡 Protected')
    if p.get('hot_seat'):parts.append('⚠️ Hot Seat')
    if p['area']=='minors':parts.append('⬇️ Minors')
    if p['area']=='dfa':parts.append('❌ DFA')
    if any(c['player_id']==p['id'] and c['status']=='active' for c in repo.list('challenges',fid)):parts.append('🎯 Active Challenge')
    return ' · '.join(parts)

```

### random-franchise/ui/creator.py

```python
import html
import streamlit as st
from services.wheel_engine import current_job

def render(repo,f):
    st.markdown('<style>[data-testid="stSidebar"],header,footer{display:none}.block-container{padding:1rem;max-width:1600px}</style>',unsafe_allow_html=True)
    fid=f['id'];run=repo.get('runs',f['current_run']) if f['current_run'] else None
    games=repo.list('games',fid);spins=repo.list('spins',fid);job=current_job(repo,fid)
    tags={t['player_id'] for t in repo.list('tags',fid) if t['active']}
    players=repo.list('players',fid)
    esc=html.escape
    values=[('EVENT RUN',f"{run['wins']} — {run['losses']}" if run else 'READY'),
      ('FRANCHISE',f"{sum(g['result']=='W' for g in games)} — {sum(g['result']=='L' for g in games)}"),
      ('CURRENT WHEEL',repo.get('wheels',f"{fid}:{job['wheel_id']}")['display_name'] if job else 'No wheel due'),
      ('LATEST RESULT',spins[-1]['result']['text'] if spins else '—'),
      ('HOT SEAT',', '.join(p['name'] for p in players if p.get('hot_seat')) or 'None'),
      ('FRANCHISE TAGS',', '.join(p['name'] for p in players if p['id'] in tags) or 'None'),
      ('ACTIVE CHALLENGE',' · '.join(c['description'] for c in repo.list('challenges',fid) if c['status']=='active') or 'None'),
      ('BANKED MOVES',str(sum(m['status'] in ['pending','deferred'] for m in repo.list('moves',fid))))]
    cells=''.join(f'<div class="tile"><div class="label">{esc(label)}</div><div class="value">{esc(value)}</div></div>' for label,value in values)
    st.markdown(f'''<style>.capture{{aspect-ratio:16/9;background:#0a1421;padding:30px;border:2px solid #42e2ae;border-radius:20px;box-sizing:border-box;overflow:hidden}}.capture h1{{font-size:38px;color:#42e2ae}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}.tile{{background:#152638;padding:18px;border-radius:12px}}.label{{color:#42e2ae;font-size:14px;letter-spacing:2px}}.value{{font-size:27px;font-weight:bold;overflow-wrap:anywhere}}</style><section class="capture"><h1>⚾ {esc(f['name'])}</h1><div class="grid">{cells}</div></section>''',unsafe_allow_html=True)
    # Refreshing reads persistent data; no management operations exist on this page.

```

### random-franchise/ui/dashboard.py

```python
import streamlit as st
from models.domain import State
from services.game_engine import start_run
from services.franchise_service import settings
from ui.common import navigate,table,badges

def render(repo,f):
    fid=f['id'];run=repo.get('runs',f['current_run']) if f['current_run'] else None
    games=repo.list('games',fid)
    a,b,c,d=st.columns(4)
    a.metric('Run record',f"{run['wins']}–{run['losses']}" if run else 'Not started')
    b.metric('Franchise record',f"{sum(g['result']=='W' for g in games)}–{sum(g['result']=='L' for g in games)}")
    pending=[m for m in repo.list('moves',fid) if m['status'] in ['pending','deferred']]
    c.metric('📦 Next-run moves',len(pending))
    threshold=next((n for n in sorted(int(x) for x in settings(repo,fid)['milestones']) if not run or n>run['wins']),None)
    d.metric('Next milestone',f'{threshold} wins' if threshold else 'All earned')
    if f['state']==State.ACTIVE:navigate('▶ Enter Next Game','Game Entry')
    elif f['state']==State.WHEEL:navigate('🎡 Spin required wheel','Wheel Room')
    elif f['state'] in [State.SETUP,State.READY]:
        navigate('Build / inspect roster','Roster Manager')
        if st.button('Validate and start next run',type='primary'):
            start_run(repo,fid);st.rerun()
    else:navigate('Continue offseason','Offseason')
    st.subheader('Franchise status')
    table([{'Player':p['name'],'Status':badges(repo,fid,p)} for p in repo.list('players',fid) if badges(repo,fid,p)])
    st.subheader('Active challenges')
    table([{'Player':repo.get('players',c['player_id'])['name'],'Challenge':c['description'],'Status':c['status']} for c in repo.list('challenges',fid) if c['status'] in ['active','awaiting_manual']])
    st.subheader('📦 Next Run Moves')
    table([{'Move':m['description'],'Type':m['type'],'Status':m['status']} for m in pending[:8]])
    spins=repo.list('spins',fid)
    if spins:st.info('Latest wheel: '+spins[-1]['result']['text'])

```

### random-franchise/ui/forms.py

```python
import pandas as pd
import streamlit as st
from models.domain import POSITIONS, AREAS
from services.stat_engine import HITTER, PITCHER


def player_fields(prefix='',area_default='minors'):
    a,b,c=st.columns(3)
    name=a.text_input('Player name',key=prefix+'name')
    version=b.text_input('Card/version',value='Base',key=prefix+'version')
    ovr=c.number_input('OVR',0,99,75,key=prefix+'ovr')
    a,b,c=st.columns(3)
    kind=a.selectbox('Type',['hitter','pitcher'],key=prefix+'kind')
    primary=b.selectbox('Primary position',POSITIONS,key=prefix+'primary')
    secondary=c.multiselect('Secondary positions',POSITIONS,key=prefix+'secondary')
    a,b,c=st.columns(3)
    area=a.selectbox('Roster area',AREAS,index=AREAS.index(area_default),key=prefix+'area')
    position=b.selectbox('Assigned position',POSITIONS,key=prefix+'position')
    order=c.number_input('Order / role priority',1,30,1,key=prefix+'order')
    a,b,c=st.columns(3)
    team=a.text_input('Team (optional)',key=prefix+'team')
    series=b.text_input('Series (optional)',key=prefix+'series')
    eligibility=c.selectbox('Event eligibility',['unknown','legal','illegal'],key=prefix+'eligibility')
    a,b=st.columns(2)
    bat=a.selectbox('Bats',['','L','R','S'],key=prefix+'bat')
    throw=b.selectbox('Throws',['','L','R'],key=prefix+'throw')
    notes=st.text_area('Notes',key=prefix+'notes')
    return dict(name=name,version=version,ovr=int(ovr),kind=kind,primary=primary,secondary=secondary,area=area,
                position=position,order=int(order),team=team,series=series,eligibility=eligibility,bat=bat,throw=throw,notes=notes)


def stat_fields(repo, fid, roster_ids, prefix, existing=None):
    old={s['player_id']:s for s in (existing or [])}
    output=[]
    for kind,keys in [('hitter',HITTER),('pitcher',PITCHER)]:
        players=[repo.get('players',pid) for pid in roster_ids]
        players=[p for p in players if p and p['kind']==kind]
        rows=[]
        for p in players:
            prior=old.get(p['id'],{})
            row={'player_id':p['id'],'Player':p['name'],'Played':bool(prior)}
            row.update({key:prior.get('line',{}).get(key,1 if key=='games' else 0) for key in keys})
            if kind=='pitcher':
                row.update(no_hitter=prior.get('flags',{}).get('no_hitter',False),perfect_game=prior.get('flags',{}).get('perfect_game',False))
            rows.append(row)
        st.subheader(kind.title()+' stat lines')
        st.caption('Check Played for participants. PA includes AB + BB + HBP + SF. Pitcher innings use outs: 1 inning = 3 outs.')
        if rows:
            edited=st.data_editor(pd.DataFrame(rows),key=prefix+kind,hide_index=True,width='stretch',disabled=['Player','player_id'],
                column_config={'player_id':None,**{key:st.column_config.NumberColumn(key,min_value=0,step=1) for key in keys}})
            for row in edited.to_dict('records'):
                if row['Played']:
                    output.append(dict(player_id=row['player_id'],line={key:int(row[key]) for key in keys},
                        flags={flag:bool(row.get(flag,False)) for flag in ['no_hitter','perfect_game']}))
    st.caption('No-hitter / perfect-game flags are creator-confirmed complete-game feats; verify all in-game requirements before checking them.')
    return output

```

### random-franchise/ui/game_entry.py

```python
from datetime import date
import streamlit as st
from models.domain import State,uid
from services.game_engine import record_game,correct_game
from ui.forms import stat_fields
from ui.common import navigate

def render(repo,f):
    fid=f['id'];run=repo.get('runs',f['current_run']) if f['current_run'] else None
    if f['state']!=State.ACTIVE or not run:
        st.info('Game entry is locked. Finish the current wheel or offseason action.')
        navigate('Open required wheel','Wheel Room') if f['state']==State.WHEEL else navigate('Open offseason','Offseason')
        return
    key='draft:'+run['id']
    if key not in st.session_state:
        with st.form('game_entry'):
            a,b,c=st.columns(3)
            result=a.selectbox('Result',['W','L'])
            opponent=b.text_input('Opponent (optional)')
            played=c.date_input('Game date',value=date.today())
            include=st.checkbox('Include scores')
            a,b=st.columns(2)
            own=a.number_input('Your score',0,99,0)
            opp=b.number_input('Opponent score',0,99,0)
            notes=st.text_area('Game notes')
            lines=stat_fields(repo,fid,run['roster_ids'],'entry:'+run['id'])
            if st.form_submit_button('Review game',type='primary'):
                st.session_state[key]=dict(request_id=uid(),result=result,opponent=opponent,date=str(played),
                    team_score=int(own) if include else None,opponent_score=int(opp) if include else None,notes=notes,lines=lines)
                st.rerun()
    else:
        draft=st.session_state[key]
        st.subheader('Review before saving')
        st.write({k:v for k,v in draft.items() if k not in ['request_id','lines']})
        st.write(f"{len(draft['lines'])} player stat lines")
        for row in draft['lines']:
            st.write(repo.get('players',row['player_id'])['name'],row['line'])
        a,b=st.columns(2)
        if a.button('Confirm and save once',type='primary'):
            record_game(repo,fid,**draft)
            del st.session_state[key]
            st.session_state['last_saved_game']=draft['request_id']
            st.rerun()
        if b.button('Discard draft'):
            del st.session_state[key];st.rerun()
    if st.session_state.get('last_saved_game'):
        st.success('Game saved. Your record and stats have been updated.')
        navigate('Return to dashboard','Dashboard')


def correction(repo,f):
    games=repo.list('games',f['id'])
    if not games:return
    st.subheader('Administrative game / stats correction')
    labels={g['id']:f"Run {repo.get('runs',g['run_id'])['number']} · Game {g['number']} · {g['result']}" for g in games}
    gid=st.selectbox('Game',list(labels),format_func=labels.get)
    game=repo.get('games',gid);run=repo.get('runs',game['run_id'])
    st.caption('Stats corrections are always audited. Outcome edits are allowed only for the latest current-run game before dependent wheels or offseason actions.')
    with st.form('correct:'+gid):
        outcome=st.selectbox('Corrected result',['W','L'],index=0 if game['result']=='W' else 1)
        lines=stat_fields(repo,f['id'],run['roster_ids'],'correct:'+gid,[s for s in repo.list('stats',f['id'],run['id']) if s['game_id']==gid])
        reason=st.text_input('Correction reason (required)')
        confirmed=st.checkbox('I confirm replacement of this game’s stat lines.')
        if st.form_submit_button('Apply audited correction') and confirmed:
            correct_game(repo,f['id'],gid,lines,reason,outcome);st.rerun()

```

### random-franchise/ui/history.py

```python
import streamlit as st
from services.stat_engine import aggregate
from ui.common import table

def render(repo,f):
    fid=f['id'];runs=repo.list('runs',fid);games=repo.list('games',fid);players=repo.list('players',fid)
    ended=[r for r in runs if r['ended_at']]
    a,b,c=st.columns(3)
    rank=lambda r:(r['wins'],-r['losses'])
    a.metric('Best run',f"{max(ended,key=rank)['wins']}–{max(ended,key=rank)['losses']}" if ended else '—')
    b.metric('Worst run',f"{min(ended,key=rank)['wins']}–{min(ended,key=rank)['losses']}" if ended else '—')
    streak=best=0
    for g in games:
        streak=streak+1 if g['result']=='W' else 0;best=max(best,streak)
    c.metric('Longest win streak',best)
    st.subheader('Event runs')
    table([{'Run':r['number'],'Event':r['event'],'W':r['wins'],'L':r['losses'],'Start':r['started_at'],'End':r['ended_at'],
            'MVP':repo.get('players',r['mvp'])['name'] if r['mvp'] else ''} for r in runs])
    st.subheader('Franchise leaders')
    hitter=sorted([{'Player':p['name'],**aggregate(repo,fid,p)} for p in players if p['kind']=='hitter'],key=lambda p:p['h'],reverse=True)
    pitcher=sorted([{'Player':p['name'],**aggregate(repo,fid,p)} for p in players if p['kind']=='pitcher'],key=lambda p:p['so'],reverse=True)
    table(hitter[:5]);table(pitcher[:5])
    st.subheader('Longest-tenured cards')
    table([{'Player':p['name'],'Acquired':p['acquired_at'],'Status':p['area']} for p in sorted(players,key=lambda p:p['acquired_at'])[:10]])
    for title,key in [('Games','games'),('Rewards and milestones','rewards'),('Roster changes and corrections','corrections'),
                      ('Banked rewards and punishments','moves'),('Franchise Tags','tags'),('Immutable wheel audit','spins'),('Roster snapshots','snapshots')]:
        with st.expander(title):
            for row in repo.list(key,fid):st.json(row,expanded=False)

```

### random-franchise/ui/offseason.py

```python
import streamlit as st
from models.domain import State
from services.offseason_service import confirm_end,select_mvp,progress,finish_validation
from services.game_engine import start_run
from services.roster_validator import validate
from services.challenge_service import confirm_manual
from ui.common import navigate,table

def render(repo,f):
    fid=f['id'];state=f['state']
    if state==State.ACTIVE:st.info('Your Event entry is still active. Offseason begins only when the loss limit is reached.');return
    if state==State.WHEEL:navigate('Spin the required wheel','Wheel Room');return
    if state==State.ENDED:
        run=repo.get('runs',f['current_run'])
        st.write(f"Final record: **{run['wins']}–{run['losses']}**")
        if st.button('Confirm ended run and select MVP',type='primary'):confirm_end(repo,fid);st.rerun()
    elif state==State.MVP:
        run=repo.get('runs',f['current_run']);ids=run['roster_ids']
        labels={i:repo.get('players',i)['name'] for i in ids}
        pid=st.selectbox('Run MVP',ids,format_func=labels.get)
        st.caption('MVP receives temporary protection through this offseason’s elimination cycle.')
        if st.button('Confirm MVP and spin reward',type='primary'):select_mvp(repo,fid,pid);st.rerun()
    elif state in [State.ELIMINATION,State.MELTDOWN]:
        st.write('Next: elimination' if state==State.ELIMINATION else 'Next: check configured 0–2 Meltdown')
        if st.button('Continue offseason',type='primary'):progress(repo,fid);st.rerun()
    elif state==State.MOVES:
        st.write('Resolve consequences first, then rewards. Optional acquisitions can remain deferred for a later Event.')
        navigate('Resolve banked moves','Banked Moves')
        manual=[c for c in repo.list('challenges',fid) if c['status']=='awaiting_manual']
        for c in manual:
            with st.form('challenge:'+c['id']):
                st.write(repo.get('players',c['player_id'])['name']+' — '+c['description'])
                passed=st.checkbox('Challenge passed')
                evidence=st.text_input('Evidence / what happened')
                if st.form_submit_button('Confirm challenge result'):confirm_manual(repo,fid,c['id'],passed,evidence);st.rerun()
        if st.button('Proceed to roster reconstruction',type='primary'):progress(repo,fid);st.rerun()
    elif state==State.REBUILD:
        navigate('Rebuild roster','Roster Manager')
        if st.button('Proceed to validation',type='primary'):progress(repo,fid);st.rerun()
    elif state==State.VALIDATION:
        result=validate(repo,fid)
        if result.valid:
            st.success('Roster checks pass. Confirm in-game Event eligibility as well.')
            if st.button('Approve roster for next run',type='primary'):finish_validation(repo,fid);st.rerun()
        else:
            for error in result.errors:st.warning(error)
            navigate('Fix roster assignments','Roster Manager')
            navigate('Resolve outstanding moves','Banked Moves')
    elif state in [State.SETUP,State.READY]:
        navigate('Review roster','Roster Manager')
        if st.button('Start next Event run at 0–0',type='primary'):start_run(repo,fid);st.rerun()

```

### random-franchise/ui/player_stats.py

```python
import streamlit as st
from services.stat_engine import aggregate
from ui.common import table,badges

def render(repo,f):
    players=repo.list('players',f['id'])
    if not players:st.info('Add players first.');return
    runs=repo.list('runs',f['id'])
    scope=st.selectbox('Statistics scope',['Franchise lifetime','Current Event run','Individual game'])
    rid=f.get('current_run') if scope=='Current Event run' else None
    gid=None
    games=repo.list('games',f['id'])
    if scope=='Individual game':
        if not games:st.info('No games entered.');return
        labels={g['id']:f"Run {repo.get('runs',g['run_id'])['number']} · Game {g['number']}" for g in games}
        gid=st.selectbox('Game',list(labels),format_func=labels.get)
    for kind in ['hitter','pitcher']:
        st.subheader(kind.title()+'s')
        table([{'Player':p['name'],**aggregate(repo,f['id'],p,rid,gid)} for p in players if p['kind']==kind])
    st.subheader('Player profile')
    labels={p['id']:p['name'] for p in players}
    pid=st.selectbox('Player',list(labels),format_func=labels.get)
    p=repo.get('players',pid)
    st.write(badges(repo,f['id'],p));st.json(p)

```

### random-franchise/ui/roster.py

```python
import streamlit as st
from models.domain import AREAS,POSITIONS
from services.roster_service import locked,add_player,arrange,swap,remove_player
from services.import_export import export_roster,import_roster
from services.roster_validator import validate
from services.franchise_service import audit
from ui.common import table,badges
from ui.forms import player_fields

def render(repo,f):
    fid=f['id'];players=repo.list('players',fid)
    is_locked=locked(repo,fid)
    if is_locked:st.info('Active run: lineup, bench, positions, rotation, and bullpen arrangements are available. New cards, call-ups, and removals wait until offseason.')
    for area in AREAS:
        with st.expander(area.title(),expanded=area in ['lineup','bench']):
            table([{'Player':p['name'],'Card':p['version'],'OVR':p['ovr'],'Position':p['position'],'Order':p['order'],
                    'Eligibility':p['eligibility'],'Status':badges(repo,fid,p)} for p in sorted(players,key=lambda p:p['order']) if p['area']==area])
    if players:
        ids=[p['id'] for p in players];labels={p['id']:p['name']+' · '+p['area'] for p in players}
        with st.form('arrange'):
            st.subheader('Arrange one player')
            pid=st.selectbox('Player',ids,format_func=labels.get)
            a,b,c=st.columns(3)
            area=a.selectbox('Destination area',AREAS[:-1])
            pos=b.selectbox('Assigned position',POSITIONS)
            order=c.number_input('Batting order / role priority',1,30,1)
            if st.form_submit_button('Save arrangement'):
                arrange(repo,fid,pid,area,pos,int(order));st.rerun()
        with st.form('swap'):
            st.subheader('Swap two assignments')
            first=st.selectbox('First player',ids,format_func=labels.get)
            second=st.selectbox('Second player',ids,format_func=labels.get)
            st.caption('Both destination positions must be legal. Use this for starter/bench swaps and order changes.')
            if st.form_submit_button('Swap assignments'):
                swap(repo,fid,first,second);st.rerun()
        with st.form('eligibility'):
            st.subheader('Update Event eligibility and notes')
            pid=st.selectbox('Card to verify',ids,format_func=labels.get)
            value=st.selectbox('Eligibility',['legal','illegal','unknown'])
            note=st.text_input('Verification note')
            if st.form_submit_button('Update eligibility'):
                with repo.transaction():
                    p=repo.get('players',pid);before=dict(p);p.update(eligibility=value,notes=note)
                    repo.put('players',p);audit(repo,fid,'eligibility',before,p,note or 'Manual eligibility check')
                st.rerun()
    if not is_locked:
        with st.expander('Add a card'):
            with st.form('new_player'):
                data=player_fields('new_')
                if st.form_submit_button('Add card'):
                    add_player(repo,fid,data);st.rerun()
        if players:
            with st.form('remove'):
                st.subheader('DFA / demote')
                pid=st.selectbox('Removal target',ids,format_func=labels.get)
                destination=st.selectbox('Destination',['dfa','minors'])
                confirm=st.checkbox('I confirm this offseason removal.')
                if st.form_submit_button('Apply removal') and confirm:
                    remove_player(repo,fid,pid,destination);st.rerun()
        upload=st.file_uploader('Import additional cards (CSV / JSON)',type=['csv','json'])
        confirmed=st.checkbox('Import appends cards; I have checked for duplicates.')
        if upload and confirmed and st.button('Import cards'):
            import_roster(repo,fid,upload.getvalue().decode('utf-8-sig'),upload.name.rsplit('.',1)[-1]);st.rerun()
    a,b=st.columns(2)
    a.download_button('Export roster JSON',export_roster(repo,fid),'roster.json','application/json')
    b.download_button('Export roster CSV',export_roster(repo,fid,'csv'),'roster.csv','text/csv')
    st.subheader('Roster check')
    result=validate(repo,fid)
    if result.valid:st.success('Roster composition and configured eligibility checks pass.')
    else:
        for error in result.errors:st.warning(error)

```

### random-franchise/ui/settings.py

```python
import json
import math
import streamlit as st
from services.franchise_service import settings,save_settings,audit
from services.roster_service import locked
from models.domain import RuleError
from ui.game_entry import correction

def render(repo,f):
    fid=f['id'];cfg=settings(repo,fid)
    st.subheader('Back up your complete app data')
    st.caption('This backup contains all franchises, games, stats, wheels, and audits. Local cloud disk is temporary. Download after each session; restore with the documented database command.')
    st.download_button('Download full SQLite backup',repo.backup_bytes(),'random_franchise_backup.db','application/octet-stream')
    if locked(repo,fid):st.info('Rules and wheel settings are editable between runs. Game/stat corrections remain available below.')
    else:
        with st.form('settings'):
            st.subheader('Challenge and Event rules')
            st.caption('Edit the JSON fields: loss limit, milestones, tag cap, meltdown, roster sizes, optional average OVR cap, Event restrictions, dates, cooldown, and special wheel availability.')
            text=st.text_area('Settings JSON',value=json.dumps(cfg,indent=2),height=420)
            if st.form_submit_button('Save rules'):
                try:values=json.loads(text)
                except ValueError:raise RuleError('Invalid settings JSON.')
                save_settings(repo,fid,values);st.rerun()
        wheels=repo.list('wheels',fid)
        labels={w['id']:w['display_name'] for w in wheels}
        wid=st.selectbox('Wheel to edit',list(labels),format_func=labels.get)
        wheel=repo.get('wheels',wid)
        with st.form('wheel:'+wid):
            text=st.text_area('Wedges JSON (weights, active flags, effects, eligibility, follow-up wheel)',value=json.dumps(wheel['wedges'],indent=2),height=420)
            if st.form_submit_button('Save wheel configuration'):
                try:wedges=json.loads(text)
                except ValueError:raise RuleError('Invalid wheel JSON.')
                if not isinstance(wedges,list) or not wedges or len({w.get('id') for w in wedges})!=len(wedges):
                    raise RuleError('Wedges need distinct IDs and a nonempty list.')
                valid_wheels={w['wheel_id'] for w in wheels}
                effects={'acquire','dfa','demote','trade','review','none','protect','unprotect','hot_seat','arrangement','challenge','tag','extra_spin','call_up','cancel_elimination','save_dfa'}
                for w in wedges:
                    if not isinstance(w.get('text'),str) or not isinstance(w.get('weight'),(int,float)) or not math.isfinite(w['weight']) or w['weight']<0 or w.get('effect') not in effects:
                        raise RuleError('Every wedge needs text, a nonnegative numeric weight, and a supported effect.')
                    if w.get('follow_up') and w['follow_up'] not in valid_wheels:raise RuleError('Unknown follow-up wheel.')
                    if not isinstance(w.get('quantity',1),int) or not 1<=w.get('quantity',1)<=4:raise RuleError('Quantity must be an integer 1–4.')
                if not any(w.get('active',True) and w['weight']>0 for w in wedges):raise RuleError('Keep at least one active weighted wedge.')
                with repo.transaction():
                    before=dict(wheel);wheel['wedges']=wedges;repo.put('wheels',wheel)
                    audit(repo,fid,'wheel_configuration',before,wheel,'Wheel editor')
                st.rerun()
    with st.expander('Administrative corrections'):correction(repo,f)

```

### random-franchise/ui/wheel_room.py

```python
import html
import math
import streamlit as st
import streamlit.components.v1 as components
from services.wheel_engine import current_job,available,spin,continue_spin,retry_impossible_branch
from services.franchise_service import settings
from ui.common import navigate

def visual(result,reduced):
    options=result['available']
    if not options:return
    count=len(options);angle=360/count
    selected=next((i for i,w in enumerate(options) if w['id']==result['result']['id']),0)
    pieces=[]
    colors=['#42e2ae','#277da1','#f9c74f','#f9844a','#9b5de5']
    for i,w in enumerate(options):
        a,b=math.radians(i*angle-90),math.radians((i+1)*angle-90)
        x1,y1=180+155*math.cos(a),180+155*math.sin(a)
        x2,y2=180+155*math.cos(b),180+155*math.sin(b)
        if count==1:pieces.append('<circle cx="180" cy="180" r="155" fill="#42e2ae"/>')
        else:pieces.append(f'<path d="M180 180 L{x1} {y1} A155 155 0 {int(angle>180)} 1 {x2} {y2} Z" fill="{colors[i%5]}" stroke="#0a1421"/>')
        mid=math.radians((i+.5)*angle-90);x,y=180+110*math.cos(mid),180+110*math.sin(mid)
        pieces.append(f'<text x="{x}" y="{y}" fill="#07111e" text-anchor="middle" font-size="12">{i+1}</text>')
    rotation=-(selected+.5)*angle+1440
    animation='' if reduced else 'animation:land 3s cubic-bezier(.14,.62,.19,1) forwards;'
    svg=''.join(pieces)
    components.html(f'''<style>body{{background:#0a1421;color:white;text-align:center;font-family:sans-serif}}svg{{width:340px;transform:rotate({rotation}deg);{animation}}}@keyframes land{{from{{transform:rotate(0deg)}}to{{transform:rotate({rotation}deg)}}}}@media(prefers-reduced-motion:reduce){{svg{{animation:none!important}}}}</style><div style="font-size:28px">▼</div><svg viewBox="0 0 360 360">{svg}</svg><div>Selected wedge {selected+1}: {html.escape(result['result']['text'])}</div>''',height=420)


def render(repo,f):
    job=current_job(repo,f['id'])
    if not job:
        st.info('No wheel is due right now.');navigate('Next step on dashboard','Dashboard');return
    wheel=repo.get('wheels',f"{f['id']}:{job['wheel_id']}")
    st.subheader(wheel['display_name'])
    st.caption('Source: '+job['source'])
    if job.get('constraints'):st.info('Branch constraints: '+' → '.join(job['constraints']))
    cfg=settings(repo,f['id'])
    reduced=st.checkbox('Reduced motion / simple fallback',value=cfg['reduced_motion'])
    st.checkbox('Sound (placeholder; V1 has no audio)',value=False,disabled=True)
    result=repo.get('spins',job['id'])
    if not result:
        options=available(repo,f['id'],job)
        with st.expander('Eligible wedges and weights'):
            st.dataframe([{'Wedge':w['text'],'Weight':w['weight']} for w in options],hide_index=True)
        if st.button('Spin required wheel',type='primary'):
            spin(repo,f['id'],job['id']);st.rerun()
    else:
        if not reduced:visual(result,reduced)
        st.success('Result: '+result['result']['text'])
        if result.get('target'):st.write('Target: '+repo.get('players',result['target'])['name'])
        acknowledged=False
        if result['result']['effect']=='arrangement':
            st.info(result['result']['description'])
            navigate('Apply arrangement in Roster Manager','Roster Manager')
            acknowledged=st.checkbox('I applied this arrangement using existing cards and verified it is legal.')
        if result['result']['id'] == 'impossible' and job.get('parent_spin'):
            if st.button('Retry impossible child only (requires eligible options)'):
                retry_impossible_branch(repo, f['id'], job['id']); st.rerun()
        if st.button('Continue with this result',type='primary'):
            continue_spin(repo,f['id'],job['id'],acknowledged);st.rerun()
        st.caption('Result is persisted before display. Refreshing does not grant another spin.')

```

## Copy to GitHub and run

Follow START_HERE.md. After setting up a virtual environment:

```bash
python -m pip install -r requirements-dev.txt
python -m streamlit run app.py
```

Manual tests: docs/ACCEPTANCE.md.
