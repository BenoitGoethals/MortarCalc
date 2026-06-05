# MortarCalc

Vuurleidings-calculator voor 81 mm mortier (FDC-rol). Doel: peloton via GPS
inbrengen, verdelen in 1-4 waakgroepen elk met eigen PDF, fire missions van
een waarnemer (FO) behandelen per groep (max 1 actieve FM/groep, dus 0-4 FMs
tegelijk in FDC), en de vuurelementen per stuk berekenen incl. correcties.

## Datamodel

```
Peloton (FDC)
├── pieces[]         1-4 stukken (MGRS + hoogte, basisstuk-vlag)
├── groups[]         1-4 waakgroepen, elk met eigen PDF en eigen stukken
└── aiming_points[]  gedeelde merkpunten (voor op-waak én shift-targets)
```

Elke groep handelt max 1 FireMission tegelijk; stuk hoort in precies 1 groep.

## Structuur

```
src/mortarcalc/
├── units.py             streep ↔ graden/rad, normalisatie
├── geo/                 MGRS ↔ UTM, polair, current_location (CoreLocation)
├── ballistics/          vuurtafels (JSON) + solver (lading/elevatie/TOF)
├── battery/             Piece, Peloton, Group, "op waak brengen" per groep
├── firemission/         FireMission (gekoppeld aan groep), OT→GT correctie
├── gui/                 PySide6 — 2 tabs (Peloton, Fire Missions)
├── data/firetables/     JSON-vuurtafels (PLACEHOLDER — vervang door echte)
└── app.py               entry-point
```

## Installeren

```bash
uv sync          # of: pip install -e .
```

Python 3.12+ aanbevolen.

## Starten

```bash
mortarcalc       # of: python -m mortarcalc.app
```

## Belangrijk: vuurtafels

`src/mortarcalc/data/firetables/m821_81mm_he.json` bevat **fictieve waarden**
om de pipeline te testen. Vervang door werkelijke vuurtafel-data uit het
betreffende handboek voor je munitie/buis-combinatie vóór elk operationeel
gebruik.

## Conventies

- Hoeken in **streep** (NATO mils, 6400 per cirkel), grid-azimut vanaf noord.
- Afstanden in **meter**.
- Coordinaten intern UTM (zone-lokaal), I/O via **MGRS**.
- Correcties van FO in OT-frame: `right`/`add`/`up` (negatief = left/drop/down).
