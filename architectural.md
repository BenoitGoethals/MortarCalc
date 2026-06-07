# MortarCalc — Architecture

This document describes the structure of the application as code. It is
aimed at contributors and reviewers, not end users (see
[`user_manual.md`](user_manual.md) for that).

## 1. Layered overview

```
┌───────────────────────────────────────────────────────────────────┐
│                          gui/  (PySide6)                          │
│  MainWindow → 7 tabs + modal dialogs + Leaflet map (WebEngine)    │
└───────────────────────────────────────────────────────────────────┘
                              ▲
                              │ pure-Python calls only — no Qt below
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│   firemission/           battery/            ballistics/          │
│   FireMission FSM        Piece, Group,       FireTable, Library,  │
│   Observer, Targets      Peloton, lay,       solver, repository   │
│   Sheaf strategies       shells, fire plan                        │
│   FO correction          (the domain model)                       │
└───────────────────────────────────────────────────────────────────┘
                              ▲
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│   geo/         units.py       persistence.py    state.py          │
│   MGRS↔UTM     mils/deg       Peloton JSON      autosave +        │
│   polar        helpers        round-trip        archives          │
└───────────────────────────────────────────────────────────────────┘
```

**Rule:** anything under `gui/` may import from any of the inner layers,
but the inner layers must never import from `gui/` (no Qt outside `gui/`,
no panel attributes referenced from the domain). This is what lets the
test suite exercise the entire ballistic / mission / persistence pipeline
without needing a `QApplication`.

## 2. Module catalogue

### `app.py`

Entry point. Creates `QApplication`, loads the firing-table repository
+ library, offers crash recovery from the autosave file, then opens
`MainWindow`. Registered as the `mortarcalc` console script.

### `units.py`

Pure conversions: mils ↔ radians ↔ degrees, normalisation modulo 6400.

### `geo/`

* `coords.py` — `Position` dataclass (UTM, zone-local) plus
  `mgrs_to_utm` / `utm_to_mgrs` / `latlon_to_utm` / `utm_to_latlon` and
  MGRS validation/normalisation helpers.
* `polar.py` — `polar(p1, p2)` returns `(range_m, azimuth_mils)`;
  `offset(p, azimuth, distance)` returns a new `Position`.
* `current_location.py` — macOS CoreLocation wrapper that returns a
  `Position` (or raises `LocationUnavailable`).

UTM is the internal frame for all arithmetic; MGRS is the user-facing
format.

### `ballistics/`

* `firetable.py` — `FireTable` (per-charge tables of range → elevation /
  TOF / drift) with pydantic schema, JSON loader, lookup with **linear
  interpolation** between rows.
* `library.py` — `FireTableLibrary` maps a shell name (`HE`, `SMOKE`,
  …) to a `FireTable`, with a default-shell fallback.
* `solver.py` — `solve(table, range_m, Δh_m, prefer_charge)` returns
  a `FiringSolution` (charge, elevation, TOF, drift). Δh is folded into
  an *equivalent range* before the table lookup.
* `store.py` — `FireTableRepository` persists the library to disk
  (one JSON per shell + a `default.json` pointer). The library is
  *global* — independent of any platoon file — so tables are uploaded
  once per workstation.

### `battery/`

* `piece.py` — `Piece(name, position, is_base)`.
* `peloton.py` — `Peloton` (FDC level), `Group` (waakgroep with PDF,
  sector limits, optional max-range cap), `AimingPoint`, `Observer`.
  Hosts the ammo book, the fire plan, H-hour, FM counter and CRUD for
  pieces / groups / APs / observers.
* `lay.py` — `lay_on_watch(peloton, group, aiming_point)` →
  per-piece `SightSetting` for parallel sights.
* `fireplan.py` — `PlannedTarget` dataclass + helpers (`offset_label`,
  `scheduled_start`, `status_at`).
* `shells.py` — canonical shell registry (`KNOWN_SHELLS`,
  `SHELL_LABELS`, `DEFAULT_INITIAL_STOCK`, `normalise`, `label_for`).

The model owns *invariants*: a piece belongs to at most one group;
adding a base unsets any existing base; setting limits with `left ==
right` means "unrestricted".

### `firemission/`

* `mission.py` — `FireMission` dataclass plus enums:
  `MissionState` (10-phase NATO FM 3-09 flow), `MethodOfFire`
  (AF / FFE / FPF), `Sheaf` (parallel / converged / linear),
  `TargetType` (point / area / linear), `Fuze`, `FireControl`.
* `observer.py` — `Observer` + a **polymorphic** `TargetSpec` hierarchy
  (`TargetByGrid`, `TargetByPolar`, `TargetByShift`). Each spec knows how
  to `.resolve(peloton, observer) → Position` without `isinstance`
  dispatch in callers.
* `sheaf_solver.py` — **Strategy pattern**: subclasses of `SheafSolver`
  implement per-sheaf logic; the dispatcher in `solution.py` looks up
  the right strategy via `SHEAF_SOLVERS[mission.sheaf]`. Add a sheaf by
  subclassing + registering — no other code changes.
* `solution.py` — `PieceSolution` dataclass; `solve_mission(fm, peloton,
  firetable)` returns one `PieceSolution` per piece in the section.
* `correction.py` — `Correction(right_m, add_m, up_m)` + `apply_correction`
  walks the FO frame back to UTM and updates the target position.
* `commands.py` — `format_mto(fm, sols)` and `format_all_fire_commands(fm,
  sols)` produce the display strings used in the mission panel and PDF.

### `persistence.py`

Pure functions that round-trip a `Peloton` plus active and historical
`FireMission`s to/from JSON. No Qt. Stable schema with explicit
defaults for forward compatibility.

### `state.py`

`StateRepository` is the *where and when* of disk I/O. It owns the
autosave path, atomic writes (write to `.tmp`, rename), the archive
directory under app-data, and timestamped archive snapshots. Knows
nothing about Qt; the panels call it via callbacks.

### `export.py`

Builds the mission card as an HTML string, renders through
`QTextDocument` → `QPrinter(QPrinter.PdfFormat)`. Used by the active /
history panels' *Export card → PDF* action.

### `simulator.py`

Builds a 3 × 2 demo scenario (pieces + APs + FOs + sections) for the
`Simulator` menu.

### `gui/` (Qt layer)

| file | role |
| --- | --- |
| `main_window.py` | `MainWindow` — tabs, menus, autosave timer, change cascade |
| `section_panel.py` | *Platoon & Lay* tab (modal CRUD + battery diagram) |
| `piece_dialog.py` | `AddPieceDialog`, `AddAimingPointDialog`, `AddObserverDialog` |
| `section_dialog.py` | `EditSectionDialog` (PDF, limits, max range, members, lay-on-watch) |
| `position_diagram.py` | `SectionDiagram` + `BatteryDiagram` (custom paint, range arcs, labels) |
| `shell_selector.py` | reusable per-shell visibility strip |
| `ammo_panel.py` | *Ammunition* tab (inline spinbox table) |
| `firetable_panel.py` | *Firing Tables* tab |
| `fireplan_panel.py` | *Fire Plan* tab (table + Engage row) |
| `planned_target_dialog.py` | modal CRUD for one `PlannedTarget` |
| `mission_panel.py` | *Fire Missions* tab — STANDBY summary + active FM control |
| `cff_dialog.py` | modal Call-For-Fire entry dialog |
| `history_panel.py` | *History* tab |
| `map_panel.py` | *Map* tab — payload builder for Leaflet |
| `assets/map.html` | Leaflet renderer + Range Filter control |
| `mbtiles_server.py` | local HTTP server that streams tiles out of an MBTiles file |
| `mgrs_field.py` | `MgrsLineEdit` with live validation |
| `coord_dialog.py` | manual lat/lon or MGRS dialog when GPS isn't available |
| `archive_dialog.py` | archive browser |
| `assets/__init__.py` | bundled icon helpers |
| `theme.py` | colour palette + dark-theme stylesheet |

## 3. Data flow

### Cold start

```
QApplication
    │
    └── FireTableRepository.load() → FireTableLibrary
    │
    ├── StateRepository.exists()
    │     ├── yes → ask user
    │     │         ├── restore → load_state → Peloton + history + active
    │     │         └── decline → fresh Peloton
    │     └── no  → fresh Peloton
    │
    └── MainWindow(peloton, library, autosave, firetable_repo).show()
```

### Mission lifecycle

```
                      ┌─────────────────────┐
                      │     FO call (CFF)   │
                      └─────────────────────┘
                                 │
                  CallForFireDialog (FireMissions tab)
                                 │
       Observer + TargetSpec → resolve → UTM Position
                                 │
              solve_mission ─────┴─────► PieceSolutions
                                 │
                       MissionState = COMPUTED
                                 │
   ─── Phase buttons ──── MTO_SENT, READY, SHOT, SPLASH, ROUNDS_COMPLETE
                                 │
   ─── Fire 1 / Fire For Effect ── consume_ammo + log
                                 │
   ─── Correction from FO ──── apply_correction → solve again, ADJUSTING
                                 │
                       End of Mission
                                 │
                    HistoryPanel.add(fm) + autosave
```

### Change cascade

The mission panel calls back to `MainWindow._on_changed`, which:

1. refreshes the mission, map, fire-plan and ammo panels;
2. triggers an autosave;
3. updates the status bar.

Refresh is recursive in the sense that any panel can call
`on_changed()`, but no panel calls `refresh()` on itself in response
(avoids loops).

## 4. Design patterns

* **Strategy** — `sheaf_solver.SheafSolver` subclasses + the
  `SHEAF_SOLVERS` registry. Adding a sheaf means writing a class and
  registering it; no `if/elif` dispatch in the solver.
* **Polymorphic targets** — `TargetSpec.resolve(peloton, observer)`
  replaces `isinstance` checks; `TargetByGrid`, `TargetByPolar`,
  `TargetByShift` each implement their own.
* **Repository** — `FireTableRepository` and `StateRepository` separate
  I/O concerns from the model.
* **Service / DI** — `MainWindow` is constructed with the dependencies
  it needs (`Peloton`, `FireTableLibrary`, `StateRepository`,
  `FireTableRepository`); nothing reaches out to module globals.
* **Modal CRUD** — every list view has matching `Add…` / `Edit…` modals
  (`AddPieceDialog`, `AddAimingPointDialog`, `AddObserverDialog`,
  `EditSectionDialog`, `PlannedTargetDialog`, `CallForFireDialog`).
  Inline forms have been removed everywhere they were used (Fire Plan,
  Platoon & Lay, Fire Missions).
* **Custom Leaflet control** — the Range Filter on the map is a
  `L.Control` subclass with section dropdown + per-shell checkboxes; it
  re-renders only the `rangeLayer` and never touches the user's view.

## 5. Persistence

The platoon JSON written by `persistence.save_state` has the shape:

```jsonc
{
  "pieces": [{ "name": "A", "easting": ..., "northing": ..., "zone": 31,
               "hemisphere": "U", "altitude_m": 50, "is_base": true }],
  "groups": [{ "name": "north", "pdf_mils": 800,
               "left_limit_mils": 0, "right_limit_mils": 1600,
               "max_range_m": 0, "member_names": ["A","B"] }],
  "aiming_points": [...],
  "observers": [...],
  "ammo":       { "A": {"HE": 30, "SMOKE": 8} },
  "low_ammo_threshold": 5,
  "fire_plan":  [PlannedTarget, ...],
  "h_hour":     "2026-06-07T08:30:00+02:00" | null,
  "next_fm_number": 7,

  "history": [FireMission, ...],
  "active":  [FireMission, ...]
}
```

Every field has a default in the loader so older saves keep working.

`StateRepository` writes through a `.tmp` file and atomically renames,
so a crash mid-write never leaves a half-written `autosave.json`.

## 6. Firing-table JSON schema

A firing table covers one weapon/munition pair across one or more
propellant charges:

```jsonc
{
  "shell": "M821 81mm HE",
  "charges": [
    { "charge": 0,
      "rows": [
        { "range_m": 75,   "elevation_mils": 1556, "tof_s": 13.2, "drift_mils": 1 },
        ...
        { "range_m": 1100, "elevation_mils": 800,  "tof_s": 22.0, "drift_mils": 3 }
      ]
    },
    { "charge": 1, "rows": [ ... ] },
    ...
  ],
  "altitude_correction_m_per_m": 0.8,
  "metadata": { "source": "...", "notes": "..." }
}
```

The solver walks every charge, computes the equivalent range
(real range minus Δh × `altitude_correction_m_per_m`), looks up the
row table with linear interpolation and picks the charge that best
matches the `prefer_charge` policy (`"lowest"` or `"highest"`). All
arithmetic is in mils and metres.

> The values in `data/firetables/m821_81mm_he.json` are **synthetic**.
> Replace before operational use.

## 7. Test layout

Pure-Python tests live under `tests/`:

* `test_units.py`, `test_geo.py` — conversions and polar math
* `test_ballistics.py` — interpolation, charge picking, Δh correction
* `test_firetable_library.py` — library + default fallback
* `test_battery.py` — `Peloton` / `Group` invariants
* `test_call_for_fire.py` — target spec resolution
* `test_firemission.py`, `test_fm_flow.py` — mission state machine and
  sheaf strategies
* `test_ammo_and_plan.py` — ammo book + fire plan
* `test_timings.py` — H-hour countdown / status
* `test_persistence.py`, `test_autosave_and_ids.py`, `test_archive.py`
  — round-trip JSON, autosave atomicity, archive listing
* `test_simulator.py` — demo scenario integrity

`conftest.py` builds a minimal `Peloton` + library for shared fixtures.
The full suite runs without instantiating Qt (only `gui/` files import
PySide6).

## 8. Adding features

A few rules-of-thumb for new contributions:

* **Domain logic goes in `battery/`, `firemission/` or `ballistics/`.**
  Never reach for a panel attribute from inside those modules.
* **Persistent fields need a default** in `peloton_from_dict` so older
  saves keep loading.
* **New shell types** are first-class — add to `battery/shells.py` and
  the rest of the application (Ammunition tab columns, dialog combos,
  range envelopes) picks them up automatically.
* **New sheafs** require only a `SheafSolver` subclass plus a registry
  entry — see `firemission/sheaf_solver.py`.
* **GUI cleanup** — when a refresh rebuilds a panel, replace the
  container widget (don't try to clean nested layouts in place). The
  mission and section panels use this pattern after a stale-widget bug
  caused by the old in-place cleanup.
* **Modal CRUD over inline forms** — every multi-field create/edit
  flow in the app is a dialog; inline forms have been removed.
