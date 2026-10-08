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
