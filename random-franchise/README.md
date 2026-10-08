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
