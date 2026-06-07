# MortarCalc

Fire-direction calculator for a **81 mm mortar platoon (FDC role)**, written
in Python + PySide6. Built around BE/NL doctrine: a platoon (peloton) of 1–4
mortars, split into 1–4 watch-groups (waakgroepen / sections), each with its
own Primary Direction of Fire (PDF) and sector of fire. The application
handles preplotted targets, live calls-for-fire from forward observers (FOs),
per-piece firing data and corrections, ammunition tracking, persistence and
a tactical map view.

> **Operational warning.** The bundled firing tables under
> `src/mortarcalc/data/firetables/` contain **placeholder ballistic values**
> intended only for end-to-end testing of the pipeline. Replace them with
> authoritative tables for your weapon/munition combination before any
> operational use.

## Quick reference

* **User manual** — see [`user_manual.md`](user_manual.md)
* **Architecture** — see [`architectural.md`](architectural.md)
* **Scenario walkthrough** — see [`scenario.md`](scenario.md)

## Install

Python 3.12 or newer. The project uses [uv](https://docs.astral.sh/uv/) for
dependency resolution; `pip install -e .` also works.

```bash
uv sync                 # or: pip install -e .
```

Runtime dependencies (declared in `pyproject.toml`):

| package | role |
| --- | --- |
| `PySide6 ≥ 6.7` | Qt for Python — GUI, web-engine map view, PDF export |
| `mgrs ≥ 1.4.6` | MGRS ↔ UTM conversion |
| `pyproj ≥ 3.6` | UTM ↔ lat/lon (for the Leaflet map and offline routines) |
| `numpy ≥ 2.0` | numerical helpers in the ballistic solver |
| `pydantic ≥ 2.7` | strict parsing of firing-table JSON |
| `pyobjc-framework-CoreLocation ≥ 10` | macOS GPS via CoreLocation (Darwin only) |

## Run

```bash
mortarcalc              # installed as a script entry point
# or
python -m mortarcalc.app
```

On first launch the application creates an autosave file under the
platform-appropriate app-data directory; subsequent launches offer to
restore the last session.

## Test

```bash
uv run pytest           # 129 tests covering geo, ballistics, firemission,
                        # persistence, battery, fire plan, autosave, archives
```

## Top-level layout

```
src/mortarcalc/
├── app.py              entry point — wires autosave + crash recovery + main window
├── units.py            mils ↔ deg/rad helpers
├── geo/                MGRS ↔ UTM, polar (range/azimuth), CoreLocation wrapper
├── ballistics/         FireTable (JSON), Library (per-shell), solver, repository
├── battery/            Piece, Group, Peloton, lay-on-watch, shells, fire plan
├── firemission/        FireMission state machine, observer, sheaf solvers,
│                       MTO + per-gun command formatting, FO correction
├── gui/                PySide6 tabs, modal dialogs, Leaflet map, custom widgets
├── data/firetables/    bundled placeholder firing tables (replace before use)
├── data/scenarios/     bundled demo platoon states
├── persistence.py      pure peloton ↔ JSON serialisation
├── state.py            StateRepository — autosave + archives
├── export.py           HTML → PDF FM-card via QTextDocument + QPrinter
└── simulator.py        scripted demo scenario for the Simulator menu
```

For the meaning of every module, the data flow, and the SOLID rationale for
the strategy patterns under `firemission/`, read [`architectural.md`](architectural.md).

## Tabs

The main window has seven tabs:

1. **Platoon && Lay** — pieces, aiming points, observers, sections (modals).
2. **Ammunition** — per-gun per-shell stock with inline editing + bulk resupply.
3. **Firing Tables** — upload JSON tables, link them to a shell, pick default.
4. **Fire Plan** — preplotted targets, H-hour, quick-engage to a section.
5. **Fire Missions** — section overview, full call-for-fire (modal), 10-phase
   mission timeline, MTO + per-gun fire commands, corrections, EOM → history.
6. **History** — completed missions, re-engage, PDF export.
7. **Map** — Leaflet view (online + MBTiles offline), live pieces / FOs / targets,
   sector wedges, per-shell range envelopes with a section/shell filter control.

A `Simulator` menu loads a bundled 3 × 2 scenario for demo purposes; an
`Archives` menu provides timestamped snapshots and restore.

## Conventions

* **Angles** in NATO mils (6400 / circle), grid-azimuth from grid-north.
* **Distances** in metres.
* **Coordinates** internally UTM (zone-local); I/O via MGRS.
* **FO corrections** in the OT (observer-target) frame: `right` / `add` / `up`
  (negatives = left / drop / down).

## License

Not yet specified — see the source tree.
