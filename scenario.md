# Scenario — testdata voor MortarCalc

Consistent oefenscenario voor het invoeren in de app. Alle azimuts en drachten
zijn berekend met de solver van de app (UTM-zone 31U, MGRS-square DS).

## Stelling — stukken

| Naam | MGRS | Hoogte |
|---|---|---|
| **A** (basisstuk) | `31UDS1234067890` | 80 m |
| **B** | `31UDS1238067910` | 81 m |
| **C** | `31UDS1232067860` | 80 m |
| **D** | `31UDS1236067840` | 79 m |

Stukken liggen 30-90 m uit elkaar (normale sectie-stelling).

## FO-posities

| Naam | MGRS | Hoogte |
|---|---|---|
| **OP1** — vooruit O | `31UDS1450069500` | 105 m |
| **OP2** — vooruit NO | `31UDS1380071200` | 120 m |
| **OP3** — flank Z | `31UDS1280064500` | 95 m |

## Doelen — haalbaar binnen 81 mm (elementen vanaf basisstuk A)

| Doel | MGRS | h | Dracht | Az (str) | Δh | Vuurelement A |
|---|---|---|---|---|---|---|
| T01 'troops in open' | `31UDS1450069500` | 90 | 3175 m | **1500** | +10 m | lading 3, elev 956 str, TOF 35.5 s |
| T02 'mortar position' | `31UDS1620071500` | 110 | 5285 m | **834** | +30 m | lading 6, elev 1122 str, TOF 48.5 s |
| T03 'truck convoy' | `31UDS1400072500` | 130 | 4900 m | **352** | +50 m | lading 6, elev 1160 str, TOF 47.1 s |
| T04 'hardened bunker' | `31UDS1700070000` | 100 | 5115 m | **1167** | +20 m | lading 6, elev 1139 str, TOF 47.9 s |
| T05 'infantry squad' | `31UDS1250071800` | 85 | 3913 m | **42** | +5 m | lading 6, elev 1259 str, TOF 43.2 s |

## Azimuts vanaf elke FO (voor 'Polair vanaf FO' target-methode)

| Doel | OP1 az / dracht | OP2 az / dracht | OP3 az / dracht |
|---|---|---|---|
| T01 | 2532 str / 1640 m | 2675 str / 3448 m |  642 str / 4580 m |
| T02 |  718 str / 2625 m | 1473 str / 2419 m |  461 str / 7782 m |
| T03 | 6232 str / 3041 m |  155 str / 1315 m |  152 str / 8089 m |
| T04 | 1399 str / 2550 m | 1965 str / 3418 m |  664 str / 6920 m |
| T05 | 5671 str / 3048 m | 5240 str / 1432 m | 6358 str / 7306 m |

Δhoogte voor "Polair vanaf FO" = doel-hoogte − FO-hoogte:

| Doel | Δh vanaf OP1 | Δh vanaf OP2 | Δh vanaf OP3 |
|---|---|---|---|
| T01 | −15 m | −30 m |  −5 m |
| T02 |  +5 m | −10 m | +15 m |
| T03 | +25 m | +10 m | +35 m |
| T04 |  −5 m | −20 m |  +5 m |
| T05 | −20 m | −35 m | −10 m |

## Suggestie groep-verdeling en PDF

- **Groep "Noord"** — stukken A + B, PDF rond **800 str** (NO) → goede dekking voor T03, T05, T02
- **Groep "Zuid"** — stukken C + D, PDF rond **1500 str** (O-OZO) → goede dekking voor T01, T04

PDF is een tactische keuze; grote azimut-shifts t.o.v. PDF zijn traag, dus
kies PDF in de richting waar vuur verwacht wordt.

## Voorbeeld vuuropdrachten om mee te oefenen

### FM01 — via 'Polair vanaf FO'
- FO: **OP1** (`31UDS1450069500`, h=105)
- Doel-methode: **Polair vanaf FO**
- Azimut: **2532 str**, dracht: **1640 m**, Δh: **−15 m**
- Beschrijving: *troops in open*
- Toewijzen aan: **Groep Noord** (A+B)
- Verwacht voor stuk A: lading 3, elev ~956 str, az ~1500 str
- Test correctie: `right +50, add −100, up 0` → herrekenen

### FM02 — via 'Grid (MGRS)'
- FO: **OP2** (`31UDS1380071200`, h=120)
- Doel-methode: **Grid (MGRS)**
- Doel: `31UDS1620071500`, h=110 (T02 'mortar position')
- Toewijzen aan: **Groep Zuid** (C+D)
- Verwacht voor stuk C/D: lading 6, elev ~1100-1140 str
- Test gelijktijdig met FM01 actief

### FM03 — via 'Shift vanaf merkpunt'
- Voeg eerst merkpunt toe: **RP_KERK** op `31UDS1550068200`, h=90 (= T01 positie)
- FO: **OP1** (`31UDS1450069500`, h=105)
- Doel-methode: **Shift vanaf merkpunt**
- Merkpunt: **RP_KERK**, right: **+200 m**, add: **+150 m**, up: **+20 m**
- Beschrijving: *vehicle cluster*
- Toewijzen aan: **Groep Noord** (A+B) — let op: groep Noord moet eerst End of Mission krijgen als FM01 nog loopt
