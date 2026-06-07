# MortarCalc — User Manual

This manual walks through the application as the FDC chief would use it,
from cold start to end-of-mission. The order of the sections matches the
tab order in the main window.

> **Operational warning.** The bundled firing tables are **placeholders**.
> Replace them with authoritative tables for your weapon/munition before
> doing anything beyond software testing or training.

## Contents

1. [Starting up](#1-starting-up)
2. [Platoon & Lay](#2-platoon--lay)
3. [Ammunition](#3-ammunition)
4. [Firing Tables](#4-firing-tables)
5. [Fire Plan](#5-fire-plan)
6. [Fire Missions](#6-fire-missions)
7. [History](#7-history)
8. [Map](#8-map)
9. [Files, archives and autosave](#9-files-archives-and-autosave)
10. [Conventions and units](#10-conventions-and-units)

---

## 1. Starting up

* `mortarcalc` (installed entry point) or `python -m mortarcalc.app`.
* On first launch the application creates a platform-appropriate app-data
  folder and starts autosaving every 5 seconds.
* On subsequent launches it offers to restore the previous session. Decline
  to start clean.
* The `Simulator` menu loads a bundled demo scenario (3 sections × 2 mortars
  + FOs) — useful for training.
* The bottom **status bar** shows: piece / section / AP counts, number of
  loaded firing tables (with the current default shell), the open file (if
  any), and the time of the last autosave.

## 2. Platoon & Lay

This tab is where the platoon configuration lives: mortars (pieces), aiming
points, observers (FOs) and sections (watch-groups).

### Pieces (mortars)

* **Add piece…** — modal dialog. Required: name (A/B/1/2…), MGRS, altitude.
  Role: *Slave piece* (default) or *Base piece*. Initial ammunition is
  entered per shell type (HE / SMOKE / ILLUM / WP).
* **Edit selected…** — same modal, pre-populated with the row's current
  values. Double-click a row to open it directly.
* **Remove selected** — drops the piece from the platoon, the section
  membership and the ammo book.
* The pieces table column **Ammunition** shows a per-shell summary; HE
  appears in red when it falls below the low-ammo threshold (see
  [Ammunition](#3-ammunition)).

### Aiming Points

Aiming points are reference posts that are shared across every section,
used both for *lay on watch* and for the FO's *shift from a known point*
target call.

* **Add aiming point…** — modal: name + MGRS + altitude.
* **Reset all** — wipes the list.

### Observers (FOs)

* Forward Observers are first-class citizens — add them in advance instead
  of typing their location into every Fire Mission. The CFF and Engage
  dialogs pick up these positions automatically.

### Fire Sections

* **New section…** — modal with: name, Primary Direction of Fire (PDF),
  left/right sector limits (default ±800 mils around PDF, syncs as you
  change PDF until you touch a limit), and **Max range (optional cap)** —
  set to 0 to use the firing-table maximum.
* **Edit selected…** — re-opens the same modal with the values prefilled
  plus a live mini-diagram of the section, member-piece checkboxes, the
  "lay on watch" computation and a Delete button.
* **Battery diagram** below the section list always shows the whole platoon
  with PDF arrows; range envelopes are toggled with the **Show ranges**
  checkboxes (per-shell). Selecting a section highlights its arrows.

## 3. Ammunition

Per-gun ammunition stock with inline editing.

* **Top toolbar — Stock controls:**
  * `Low-ammo threshold` — global; cells go orange (`LOW`) or red (`EMPTY`)
    in real time as the value changes.
  * `Resupply <shell> for all pieces to <N> rnd  [Apply to all]` —
    bulk-set the chosen shell on every piece.
  * `Add shell type…` — type any custom name (e.g. `WP`, `DPICM`); appears
    as a new column with all pieces seeded to 0.
* **Table** — one row per piece, one editable spinbox column per shell.
  Base pieces show as "*A (base)*" in green. The right-most **Status**
  column summarises that piece's HE readiness (OK / LOW / EMPTY).
* **Footer** — running platoon totals per shell plus a warning for any
  piece below the low-ammo threshold.
* Changes write straight to the model and propagate (live mission view
  updates, autosave triggers, low-ammo warnings re-evaluated).

## 4. Firing Tables

The platoon fires several natures, each with its own ballistic table.

* **Upload table…** — picks a JSON firing-table file (see schema in
  `architectural.md`) and asks which shell name to link it to (`HE`,
  `SMOKE`, …).
* **Set default** — fallback used when a mission references an unknown
  shell. The status bar always shows the current default.
* **Remove link** — drops a shell ↔ table mapping.
* Tables are stored in a *global* repository (independent of the platoon
  file) so you only upload them once per workstation.

## 5. Fire Plan

Preplotted targets, including FPF (Final Protective Fire).

* **H-hour box** — reference time for all plan timings. Set explicitly,
  jump to **Now**, or **Clear**. Timed targets show countdowns in the
  Status column.
* **Toolbar — modal CRUD:**
  * **Add target…** — opens `PlannedTargetDialog` with all fields grouped
    into *Target details* / *LINEAR parameters* (only when target type or
    sheaf is `linear`) / *Timing* (On Call by default; offset and duration
    in minutes relative to H; FPF flag).
  * **Edit selected…** — same modal, pre-filled. Double-click a row for
    the same effect.
  * **Remove selected** / **Reset fire plan** — destructive actions ask
    for confirmation.
* **Table** is the main view of the tab: name, MGRS, altitude,
  description, type, munition/fuze, sheaf/rounds, FPF flag, timing,
  scheduled time, status (countdown / DUE NOW / ACTIVE / PAST). FPF rows
  are coloured red.
* **Engage box** — pick section, FO call-sign / MGRS / altitude, then
  **Engage selected target**: this builds a fire mission from the planned
  target and hands it to the Fire Missions tab.

## 6. Fire Missions

Active operations — the heart of the FDC role.

### Section list (left column)

Each section shows: name, PDF, piece count and status.

* **STANDBY** — no active FM. Click the section to see a summary card
  with the PDF, the assigned pieces, the per-shell ammo stock and a big
  green **▶ Start fire mission** button.
* **active FM** — shows the FM id, method of fire and rounds fired vs.
  planned.

### New fire mission flow

1. Click **▶ Start fire mission** (or **New fire mission** in the bottom
   toolbar — picks the first STANDBY section).
2. The `CallForFireDialog` opens with two columns:
   * **1. Observer (FO)** — call sign / MGRS / altitude. If a known FO is
     listed under Platoon & Lay, its position is reused.
   * **2. Target — location** — Grid (MGRS), Polar from FO, or Shift from
     a named aiming point.
   * **3. Target — description** — free text + target type.
   * **4. Method of Engagement** — munition, fuze, method of fire
     (AF / FFE / FPF), sheaf, rounds per piece, charge preference.
     Choosing `ILLUM` auto-selects the `ILLUM` fuze; choosing `SMOKE`
     resets to `QUICK`. A live readout shows the section's stock of the
     selected shell.
   * **5. Fire control** — When Ready / At My Command / TOT.
3. **Compute firing data** — solves per piece, attaches solutions and
   moves the mission into the active view.

### Active FM view

* Header: FM id, section, PDF + the current phase coloured badge.
* Brief: NATO call-for-fire summary read-back to the FO.
* **MTO** (Message To Observer) box — read this to the FO.
* **Firing data + ammunition** table — piece, charge, elevation,
  azimuth, deflection vs PDF, time of flight, rounds fired/remaining.
* **Fire commands to guns** — copy-paste-ready per-gun text.
* **Phase buttons** (Comms with FO):
  Send MTO → Guns ready → Shot, over → Splash, over → Rounds complete.
  Each click logs the event and advances the phase indicator.
* **Fire** — *Fire 1 round* (adjustment salvo) or *Fire For Effect*
  (consume the remaining rounds per piece). Both write to the ammo book
  and trigger the low-ammo warning.
* **Correction from FO** — `right` / `add` / `up` in metres (negatives
  = left / drop / down); applies the OT-frame correction, resolves a new
  target position and re-solves the mission. The phase drops back to
  ADJUSTING.
* **End of Mission** — closes the FM, writes it to the History tab and
  frees the section.
* **Export card → PDF** — printable HTML rendering of the mission card.

The 10 phases (NATO FM 3-09):
`RECEIVED → COMPUTED → MTO_SENT → READY → SHOT → SPLASH → ADJUSTING →
IN_EFFECT → ROUNDS_COMPLETE → END_OF_MISSION`.

## 7. History

Completed (End of Mission) fire missions.

* Select a row to see the final firing data, mission log and CFF brief.
* **Engage again** — creates a fresh FM reusing the target, observer,
  fuze and method on the *same* section if it's free.
* **Export card → PDF** — same renderer as in the active view.
* **Reset history** — wipes the log (after archiving).

## 8. Map

Live tactical view on a Leaflet map.

* **Base layers**: OpenStreetMap, Esri satellite, OpenTopoMap, or your
  own **MBTiles** file via the *Load MBTiles…* button (offline-friendly).
* **Markers** — pieces (mortar icon, base = red, slave = orange),
  aiming points (triangle), FOs (binoculars), targets per type.
* **Lines** — yellow dashed = section PDF; orange solid = GT (gun → target)
  lines per piece; magenta dashed = OT (FO → target) lines with azimuth /
  range label.
* **Sector of fire (limits)** — toggleable overlay. Coloured wedge fill +
  left/right limit lines per section.
* **Range envelopes** — driven by the **Range filter** control panel
  (top-right). Pick:
  * `Section` dropdown — *All sections* or any specific section.
  * `Munition` checkboxes — per-shell toggles colour-coded to match the
    arcs.
  * `All` / `None` shortcut buttons.
  * `Fit platoon` — re-centres on the platoon (pieces + APs + FOs +
    targets) with tight padding. The map only auto-fits on the very first
    render; after that your zoom is preserved.
* Each range arc is labelled with `SHELL  MAX m` at the sector
  mid-azimuth so you can read the distance without hovering.

## 9. Files, archives and autosave

* **Autosave** — every 5 seconds and after every change. The file path is
  shown in the status bar; restore is offered on next launch.
* **File menu**:
  * `New` — archive the current state and start clean.
  * `Open…` — load a saved platoon JSON.
  * `Save` / `Save As…` — write the current platoon to disk.
* **Archives menu**:
  * `Archive current state…` — manual snapshot with a label.
  * `Browse archives…` — pick a snapshot and restore it (current state is
    snapshotted first as `pre_restore`).
  * `Reset All (archive + clear)` — wipe pieces / APs / sections / fire
    plan / missions / history after an automatic archive.

The platoon JSON includes pieces, sections (with PDF + limits + max-range
cap), aiming points, observers, ammo, fire plan, H-hour, FM counter,
mission history and any active missions.

## 10. Conventions and units

* **Angles** — NATO mils (6400 / circle), grid-azimuth from grid-north.
* **Distances** — metres.
* **Coordinates** — internally UTM (zone-local); displayed as MGRS.
* **Time** — local timezone in the UI; timezone-aware UTC under the hood.
* **FO corrections** — OT (observer-target) frame:
  `right` / `add` / `up`; negatives = `left` / `drop` / `down`.

## Keyboard shortcuts (built-in)

* `Ctrl/Cmd + N` — File → New
* `Ctrl/Cmd + O` — File → Open
* `Ctrl/Cmd + S` — File → Save
* `Ctrl/Cmd + Shift + S` — File → Save As
* `Ctrl/Cmd + Q` — quit

Most modal dialogs accept **Enter** to confirm and **Esc** to cancel.

## Troubleshooting

* **No GPS on macOS** — the application uses CoreLocation (pyobjc).
  If location access is denied the *Current location* button falls back
  to a manual lat/lon dialog. On non-Darwin systems CoreLocation is
  unavailable; coordinates must be typed.
* **Map tiles black** — Qt WebEngine blocks remote URLs from local file
  pages by default; this is already worked around in the panel, but a
  firewall or proxy can still break Esri/OSM. Use MBTiles for offline.
* **Firing-table errors** — the JSON must validate against the schema in
  `architectural.md`. The status bar reports how many tables are loaded;
  0 means no missions can be solved.
