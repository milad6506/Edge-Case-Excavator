# Gap Analysis — Legacy Expectations & Taxonomy Corpus vs Edge-Case-Excavator v4

**Date:** 2026-10-16
**Compares:** the September 2026 corpus under `~/Documents/DriveLM/` (expectations JSONs, taxonomy v2/v2.1, meta-actions v1, coverage audit) against this repository's current contents (`behavioral_refinements-v2.txt`, `meta-actions-v2.txt`, `actors-factors-list-v4.txt`, `iso_edge_corner_missing_cases.md`).
**Verdict up front:** the expectations layer carried over losslessly (221→221, plus a new meta-action-sequence capability). The taxonomy layer was re-architected (gains in rigor) but **dropped ~20 actor sub-classes, ~15 named factor leaves, and — most importantly — the entire synthesis layer** (130 combined cases + 259 gap candidates) that motivated this project in the first place.

---

## 0. Inputs compared

**Old corpus (`~/Documents/DriveLM/`, Sep 2026):**

| Artifact | Content |
|---|---|
| `ADS expectations/ads_behavioral_expectations_v11.json` | 107 Vienna-grounded expectations |
| `ADS expectations/avsc_odd_behavioral_expectations_v3.json` | 11 ODD expectations (with `ODD_factors_addressed`, `expected_detection_capability`) |
| `ADS expectations/avsc_vru_behavioral_expectations_v3.json` | 17 VRU expectations (with `vru_classes`, `challenges_addressed`) |
| `ADS expectations/texas_traffic_law_behavioral_expectations_v5.json` | 70 Texas Transportation Code Ch. 545 expectations |
| `ADS expectations/vienna_convention_road_user_expectations.txt` | 160 KB source digest |
| `ads_unified_behavioral_expectations.json` | **221** unified expectations (111 Vienna + 70 Texas + 17 VRU + 11 ODD + 12 First-Responder) |
| `complete_exhaustive_factor_actor_taxonomy-v2.json` | audit-base taxonomy: 62 actor sub-classes, ~96 factor leaves, 10 combined classes |
| `exhaustive_factor_actor_taxonomy_v2.1.json` | restructured synthesis: **130 combined cases, 259 taxonomy_gap_candidates, 2 excluded expectations** |
| `meta-actions.txt` | 15 NHTSA meta-actions (ACT-01..15) |
| `taxonomy_coverage/FINDINGS.md` (+ reports, Desktop PDF) | dataset-coverage audit: 158 leaf verdicts vs DriveLM-nuScenes/CARLA — 79 categorically absent, 34 parametrically limited, 5/10 combined classes never co-occur |

**New (this repo):** `behavioral_refinements-v2.txt` · `meta-actions-v2.txt` · `actors-factors-list-v4.txt` · `iso_edge_corner_missing_cases.md`

---

## 1. Expectations layer — lossless carry-over, two regressions

Verified programmatically (full ID-set diff):

- **221 → 221, zero dropped, zero added.** All 94 (category, sub-category) pairs identical; every old `statutory_ref` string is present verbatim in the refined file.
- **New capability:** every entry now carries a `Required Meta-Action Sequence` (the old unified JSON had none). ACT-16 (Reverse/Back Up) appears in 7 sequences; all 16 meta-actions are exercised at least once — the header's "Fully Aligned Across All 16 Meta-Actions" claim checks out.

**Regression 1 — AVSC structured metadata dropped.** The 11 ODD entries lost `ODD_factors_addressed` (e.g., *Geofenced Area*, *Route Network*) and `expected_detection_capability`; the 17 VRU entries lost `vru_classes` and `challenges_addressed` (0 occurrences of any of these field names in the refined file). The prose survived; the machine-queryable handles did not.

**Regression 2 (QA) — sequence template reuse.** 18 duplicate sequence-signature groups exist; the top three templates cover **96 of 221 entries**:
- `(05→06→08→06)` yield/change-lane/pass/return — 40 entries, including ADS-REQ-001C, whose expectation text is about *being blocked and stopping to become a marked obstruction* — a stop-based sequence (03→04→15) is semantically required, not a passing maneuver.
- `(05→03→10→02)` — 31 entries; `(03→13→04→15)` — 25 entries.
- Thin-coverage actions: ACT-07 (1×), ACT-09 (1×), ACT-12 (3×), ACT-14 (3×) — aborts and MRC-handover are nearly absent from sequences, even though ACT-14/15 are the core of fallback behavior.

**Inherited (not new):** the ID scheme already mixes `ADS-REQ-TX-*` (43) and `ADS-REQ-Texas-*` (27) in the old unified JSON; the refined file preserved the inconsistency.

---

## 2. Meta-actions: 15 → 16

- **Added:** `[ACT-16] Reverse / Back Up` — grounded in Vienna Art. 14/25, Texas § 545.415, NHTSA pre-crash scenarios 8/15/33–35. This closes the backing/reversing hole the old corpus could only express as prose expectations.
- **Extended:** `[ACT-10] Turn` now declares left/right/U-turn parameterizations.
- Usage across the 221 sequences: ACT-03 (168), ACT-05 (149), ACT-06 (107), ACT-04 (92), ACT-02 (82) dominate; ACT-07/09/12/14 are near-absent (see §1).

---

## 3. Actor taxonomy: 62 sub-classes → 26 groups

**Architectural gains (v4):** universal 3-state compliance machine (`COMPLIANT | MISUSE | ABUSE`) replacing the old flat 9-state compliance list; per-category movement regimes; ~45 named misuse/abuse misbehaviors (vs 9 old compliance states); SI-quantified bounding boxes and kinematic bounds (incl. reverse velocity, lateral accel, jerk — all new); lighting & acoustic signaling state machines; static obstacles promoted to an actor category; vehicle cabin passengers as potential interfering actors.

**Granularity loss — old sub-classes with no explicit v4 home (20):**

| Dropped/unmapped | Old location | Note |
|---|---|---|
| `pickup_truck`, `convertible` | passenger_light_vehicles | v4 parenthetical lists sedans/coupe/hatchback/SUV/minivan only |
| `shuttle_van` | buses_and_mass_transit | — |
| `rescue_command_vehicle` | emergency_priority_vehicles | v4 lists police/fire/ambulance only |
| `passenger_commuter_train` | rail_borne_vehicles | v4 rail = freight + streetcar/tram/LRT |
| `motorcycle_with_sidecar` | specialized_and_slow_moving | — |
| `farm_tractor_agricultural`, `road_construction_sweeper`, `utility_repair_truck` | specialized_and_slow_moving | entire slow-moving/specialized class dissolved |
| `animal_drawn_carriage` | animals | — |
| `intoxicated_impaired_pedestrian` | pedestrians_adult | v4 misuse covers distraction, not impairment |
| `pedestrian_with_stroller_pram`, `bulky_object_carrier_or_pushing_cart`, `person_pushing_bicycle_moped` | pedestrians_special_role_or_mobility | reduced-mobility class narrowed to wheelchair/white-cane |
| `traffic_police_officer`, `roadway_maintenance_utility_worker`, `emergency_first_responder_fire_ems`, `tow_truck_operator` | pedestrians_official_and_workers | officials class dissolved; flaggers survive only as a workzone equipment token & VRU movement pattern |
| `recumbent_cyclist_low_profile`, `cargo_cyclist_wide_footprint` | cyclists_and_micromobility | — |
| `e_bike_rider_high_speed` | cyclists_and_micromobility | ambiguous fold into e-scooter/micro-mobility |

Moved, not dropped: moped riders → motor-vehicle category; rail-borne vehicles → own actor category; wildlife `boar` → `moose` in the v4 parenthetical.

> ⚠ These are not random losses: officials, special-role VRUs, animals, and slow-moving vehicles were exactly the **categorically-absent frontier** identified by the FINDINGS.md audit (§79-leaves). Removing them as named classes re-opens the blind spot the audit had mapped.

---

## 4. Factor taxonomy: ~96 leaves → 6-layer quantified catalog

**Parameter recalibrations (old v2 → v4):**

| Factor | Old | v4 | Consequence |
|---|---|---|---|
| Rain bands | 5 levels (incl. EXTREME 25.1–50 mm/hr) | 4 bands, Heavy = 10–50 | EXTREME tier merged away; boundaries shifted (moderate 2.6–7.6 → 2.5–10) |
| Friction states | 5 named states + `stopping_distance_multiplier` per state | 4 mu-ranges | `DAMP_SURFACE` dropped; hydroplaning no longer a named state (its μ=0.20 now numerically falls in *Packed Snow/Mud*); stopping-distance multipliers dropped |
| Illuminance | 6 point values (twilight = 10.8 lx) | 5 ranges | twilight re-banded to 100–1000 lx (38× jump); FULL_DAYLIGHT merged |
| Visibility | 3 levels (10–199 / 200–999 / 1000–5000 m) | 3 bands (1–20 / 20–200 / >10000 m) | boundaries recalibrated; **undefined hole: 200 m–10 km** |
| Wind | Beaufort forces 0–12 | 0–120 km/h continuous | equivalent, unit change |
| Kinematics | accel [−8,+4] m/s², TTC [0.5,10] s, headway in **seconds** | accel [−9,+4.5], TTC [0.2,>5], headway in **meters** (+ new: v_rev, a_lat, jerk, reaction time 0.3–3 s, traffic density 0–120 veh/km/lane) | headway unit change breaks old parametric references |

**Named factor leaves dropped:** `shoulder_width_m`; special structures `BRIDGE`, `VIADUCT`, `FLYOVER`, `CREST_OF_HILL`; signal state `GREEN_ARROW`; signs `CROSSBUCK_RAILROAD`, `DO_NOT_ENTER`, `ONE_WAY`; markings `MARKED_PEDESTRIAN_CROSSWALK`, `CYCLIST_CROSSING_LANE`, `STOP_LINE_TRANSVERSE` (v4 line-types list has no crosswalk/stop-line at all).

**Genuinely new in v4 (not in old):** the 7-item "Missing Lane & Junction Structures" Gap-A slice; marking conspicuity states (GOOD→SNOW_COVERED); 6 statutory distance buffers; traffic-signal *types* (ped countdown, rail flashers, ramp metering, bus priority); `DARK_POWER_FAILURE` signal state; `DASHED_YELLOW`; school-zone flashing & no-passing signs; emergency-incident-scene characteristics; **Layer 6 in full** (V2X status, HD-map freshness, GNSS quality classes, sensor glare/occlusion states, ADS fallback states). Layer 6 has no counterpart anywhere in the old corpus and directly overlaps noise-injector Layer-F/systemic territory.

**Semantic moves:** transient obstacles (fallen cargo, spilled oil, tree branch, accident debris) → actor Category 5; workzone `FLARE` → incident scenes; `VARIABLE_MESSAGE_SIGN` → statutory signs; `BARRICADE_TYPE_III` → `CONCRETE_JERSEY_BARRIERS`.

---

## 5. The biggest gap: the synthesis layer never made it into v4

- v2.1's `combined_case_taxonomy` — **130 combined cases, 259 taxonomy_gap_candidates, 2 excluded expectations** — the mined inventory of corner cases and specification gaps — has no counterpart in v4. Only a 7-item distilled slice ("Gap-A" structures, Layer 1.3) survived.
- v2's `combined_scenario_control_guard_classes` (10 COMB-CLASS seeds: adverse-weather-VRU, school-bus, rail-crossing, mountain-defile, reversing-blind-spot, …) are absent from v4.
- `iso_edge_corner_missing_cases.md` defines the *method* for excavating edge/corner/missing cases but the raw candidate inventory it would mine lives only in the old JSONs.

---

## 6. Prioritized recommendations

1. **Import the synthesis layer as data:** copy `exhaustive_factor_actor_taxonomy_v2.1.json`'s 130 cases + 259 gap candidates into this repo (e.g., `data/combined_cases.json`, `data/gap_candidates.json`), tag each with EDGE / CORNER / MISSING per the ISO doc, and de-duplicate against v4's Gap-A slice.
2. **Publish a v2→v4 crosswalk** instead of silently absorbing: for each of the 62 old actor sub-classes and ~96 factor leaves, map → v4 group / misbehavior token / "dropped". This makes the §3/§4 losses explicit and reversible.
3. **Patch `behavioral_refinements-v2.txt`:** restore AVSC metadata fields (`ODD_factors_addressed`, `expected_detection_capability`, `vru_classes`, `challenges_addressed`); audit the 18 duplicate-sequence groups (start with ADS-REQ-001C); unify `TX`/`Texas` IDs.
4. **Fill factor regressions:** re-add crosswalk/stop-line/cyclist markings, bridge/viaduct/flyover/crest structures, shoulder width, damp & hydroplaning friction states; define the 200 m–10 km visibility band; restore or explicitly document the EXTREME precipitation tier merge.
5. **Re-run the coverage audit** (`taxonomy_coverage/` tooling) against v4 leaf keys — FINDINGS.md verdicts are keyed to v2 names and now stale.
6. **Bridge to noise-injector:** v4's Layer 5/6 bands (rain mm/hr, illuminance lx, fog distance, V2X/GNSS states) map naturally onto injector sensor families (fog/glare/low_light already exist); the ~45 misbehavior tokens are the spec for a new Layer-B "compliance misbehavior" family; ACT-16 enables backing/reversing scenario generation.

---

## 7. Resolution status after taxonomy v5/v6 (2026-10-16 addendum)

The author iterated the taxonomy twice after this analysis (v5 "Fully Grounded" → v6, now `actors-factors-list-v6.txt`, replacing v4 in this repo). v6 additionally grounds every section in named standards (Waymo labeling spec, AVSC ODD/VRU/First-Responder sections, dot_38824_DS1 Fig 17, ISO 21448 Table A.5, Vienna Art. 23/26-bis, Texas § 545.058/545.060).

**Resolved by v5, retained in v6:** shoulder types + width (§1.5); highway structures incl. BRIDGE_VIADUCT/FLYOVER_RAMP/OVERPASS/HILL_CREST_BLIND_CURVE/TUNNEL/GUARDRAIL (§1.2); GREEN_ARROW + PROTECTED_ARROW signal type; TRANSVERSE_CROSSWALK_LINES / TRANSVERSE_STOP_BAR / GREEN_CYCLIST_LANE_PAINT markings; Damp/Wet band; Hydroplaning as named state; Snow/Slush as new surface state; full visibility chain (new Reduced/Mist 200–1000 m band); Extreme Torrential Downpour >50 mm/hr as 5th tier; Civil Twilight split (10–100 lx); dual headway metrics (time 0.5–4.0 s AND spatial 0.5–100 m); pickup trucks, farm/agricultural/construction equipment, animal-drawn carriages, stroller/bulky-object pedestrians, traffic police/flaggers, first responders, recumbent/cargo cyclists.

**Resolved by v6:** convertibles & cabriolets; shuttle vans; motorcycles with sidecars/tricycles; rescue command vehicles; passenger commuter & high-speed rail; intoxicated/impaired pedestrians; person pushing bicycle/e-scooter/handcart/stroller; roadway-maintenance workers & construction flaggers on foot; tow-truck operators & roadside mechanics on foot; named sign categories (REGULATORY_STOP, REGULATORY_YIELD, REGULATORY_DO_NOT_ENTER, REGULATORY_ONE_WAY, RAILROAD_CROSSBUCK); stopping_distance_multiplier restored per friction state (1.0× → 10×).

**Still open (tracked):**
- `curve_radius_m` (old v2: 15–1000 m) remains absent from Layer 1.4 geometry metrics.
- Signal types RAMP_METERING_SIGNAL and BUS_LANE_PRIORITY_SIGNAL (present in v4 Layer 2.1) dropped.
- Sign categories SCHOOL_ZONE_FLASHING and NO_PASSING_ZONE (present in v4) not restored — only WORKZONE_TEMPORARY survives as a related category.
- Lane-width lower bound 2.5 m (old v2 / v4) raised to 2.75 m; superelevation changed from ±6° to 1–6% (negative bank angles unrepresentable); NARROW_MOUNTAIN_SINGLE_LANE_PASS network type removed (only a lane-width note remains).
- Expectation-layer items from §1 are untouched by v5/v6 (AVSC metadata restore, sequence-template audit, TX/Texas IDs) — tracked in §6.3.
- Synthesis layer import (§6.1) and v2→v6 crosswalk (§6.2) remain open.

The assessor (next phase) should parse `actors-factors-list-v6.txt` as the authoritative reference and treat the "still open" list as known limitations of the reference model.
