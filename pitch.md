# MortarCalc — Pitch

*Vuurleidings-calculator voor 81 mm mortier — voor opleiding, oefening en
veldgebruik door de FDC van een mortierpeloton.*

---

## De situatie

Een mortierpeloton (FDC, 1–4 stukken, 1–4 waakgroepen) moet onder druk:

* een Call-For-Fire van een waarnemer (FO) **binnen 30–60 seconden**
  vertalen in lading, elevatie en richting per stuk;
* munitievoorraad bijhouden per stuk en per natuur;
* een fire plan beheren met FPF-doelen en getimede opdrachten;
* OT-correcties verwerken en bijhouden in welke fase de opdracht zit;
* per opdracht een traceerbare fiche kunnen overhandigen.

Vandaag gebeurt dit met **papieren tabellen, schietregels en kaarten** — snel
en betrouwbaar voor wie er dagelijks mee werkt, maar foutgevoelig onder
stress, traag bij meerdere gelijktijdige opdrachten en moeilijk te delen
tussen secties.

## De oplossing — MortarCalc

Een **desktop-applicatie** (Python + PySide6, draait op macOS, Linux en
Windows) die de volledige FDC-workflow ondersteunt:

* Peloton, secties en waarnemers configureren via modale dialogen.
* Vuurtafels per munitie laden (HE / SMOKE / ILLUM / WP / …).
* Fire Plan met preplotted targets, H-hour en automatische countdowns.
* Volledige NATO Call-For-Fire dialoog met 10-fase mission timeline.
* MTO-tekst en stuk-per-stuk vuurbevelen automatisch gegenereerd.
* FO-correcties in OT-frame → herrekenen in één klik.
* Ammunitie-boekhouding per stuk, per munitie, live bijgewerkt.
* Tactische **Leaflet-kaart** met dracht-enveloppen per sectie × munitie,
  online of offline (MBTiles).
* PDF-export per opdracht voor het after-action report.
* Autosave elke 5 s, archivering met tijdstempel, crash-recovery.

## Doelpubliek

| Wie | Wat MortarCalc oplevert |
| --- | --- |
| **Opleidings­instituten** (mortar gunnery course) | Studenten kunnen zelfstandig de volledige FDC-loop oefenen met visuele feedback. |
| **Pelotons in oefenfase** | Snel scenario's opzetten, doelen vooraf uitwerken, oefen-FM's loggen. |
| **R&D / doctrine** | Sandbox om sheaf-strategieën, correctie-modellen of nieuwe munities snel uit te proberen. |
| **Veteranen­instructeurs** | Eén gedeeld datamodel i.p.v. losse Excel-bestanden. |

> **Niet** als operationele schiet­computer zonder gevalideerde vuurtafels.
> De bundeling bevat **placeholders** en is bedoeld voor het testen van de
> pipeline, niet voor scherp schieten.

## Waarom MortarCalc

| | Papier | Generieke artillerie-software | **MortarCalc** |
| --- | --- | --- | --- |
| Aangepast aan 81 mm BE/NL doctrine | ✅ | ⚠️ algemeen | ✅ |
| Per stuk + per sectie elementen | ⚠️ handwerk | ✅ | ✅ |
| Live OT-correctie | ⚠️ traag | ✅ | ✅ |
| Munitievoorraad per stuk × natuur | ❌ | ⚠️ vaak alles-in-één | ✅ |
| Offline kaart (MBTiles) | n.v.t. | ⚠️ vaak online-only | ✅ |
| Open broncode, eigen vuurtafels | n.v.t. | ❌ vendor-lock | ✅ |
| Auto-archief + crash recovery | ❌ | ⚠️ wisselend | ✅ |
| Run-cost | nul | hoog (licenties) | nul (open source) |

## Sleutel-features (demo punten)

1. **Modale CRUD overal** — stukken, merkpunten, FO's, secties, planned
   targets en fire missions in aparte dialogen → de hoofdpanelen zijn
   altijd leesbaar, geen overvolle inline formulieren.
2. **Per-sectie max-range cap** — voor situaties waar de toegelaten dracht
   beperkt is (veiligheid, terrein). Visueel zichtbaar in diagram en kaart.
3. **Range-filter op de kaart** — kies sectie × munitie onafhankelijk;
   "Alle secties met SMOKE" of "alleen Noord met HE en ILLUM" — twee klikken.
4. **Live FDC-tijdlijn** — 10 fases, comms-knoppen voor "Shot, over",
   "Splash, over", "Rounds complete" — elke klik logt in de fiche.
5. **Strategy-patroon onder de motorkap** — nieuwe sheaf-types (open/area,
   converged, linear, of een nieuwe doctrine-variant) toevoegen door één
   klasse te schrijven en te registreren.
6. **PDF-fiche** in één klik — voor evaluatie of debrief.

## Status

* **129 unit tests** dekken geo, ballistiek, missie-FSM, persistence,
  sheafs, fire plan, autosave en archief.
* **CI-klare** code (`uv sync && uv run pytest`).
* **Drie tabbladen** zijn al user-validated tegen scenario-oefeningen.
* **Architectuur** documenteert de SOLID-keuzes (Strategy, Repository, DI,
  polymorfe target-specs) zodat externe bijdragen ingebouwd kunnen worden.

## Roadmap (volgende stappen)

* **Echte vuurtafels** importeren (publiek beschikbare of door de gebruiker
  ingevoerd uit het handboek).
* **Multi-platoon / multi-FDC** scenario's (oefening op compagnie-niveau).
* **Replay & after-action review**: scenario's herafspelen vanaf history.
* **Train-the-trainer dashboard**: instructeur ziet meerdere FDC's tegelijk.
* **Mobile companion** voor de FO (call-for-fire vanuit het veld).
* **Validatie & certificatie-traject** met een operationele eenheid.

## Vraag

Een **pilot in opleidingscontext** — een mortier-instructeur die de
applicatie 1 cursus lang gebruikt naast de bestaande methodes en feedback
geeft. Geen budget nodig (open source, gratis); we vragen tijd en
expertise.

---

### Eén regel

> **MortarCalc neemt de papier-en-tabellen workflow van de FDC en maakt er
> een interactieve, foutbestendige en deelbare omgeving van — voor
> opleiding, training en (eens gevalideerd) inzet.**

---

### Presenter notes

* **30 sec hook** — "Een mortierpeloton moet onder druk een Call-For-Fire
  in 30 seconden vertalen in een lading per stuk. Vandaag op papier. Wij
  doen dat live." (open de Fire Missions tab met een lopend scenario)
* **2 min demo** — Platoon & Lay → Fire Plan → Engage → CFF → Compute →
  MTO → Fire → Correction → EOM → History → PDF.
* **1 min onder de motorkap** — Strategy-pattern, 129 tests, geen Qt in
  het domein-model, opensource.
* **30 sec ask** — "Een instructeur die het tijdens een cursus naast de
  papieren methode uitprobeert."
