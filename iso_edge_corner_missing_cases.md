# ISO Safety Standards Analysis: Edge Cases, Corner Cases, and Missing Cases in Automated Driving Systems

## Executive Summary
This document provides formal, standardized definitions for **Edge Cases**, **Corner Cases**, and **Missing Cases** in Automated Driving Systems (ADS), directly grounded in international safety standards: **ISO 21448:2022** (Safety of the Intended Functionality — SOTIF) and **ISO/DTS 5083:2023** (Design, Verification, and Validation of Automated Driving Systems). Furthermore, it details how the structured **Actors-Factors Taxonomy** (`actors-factors-list-v4.txt`) and **Meta-Actions Framework** (`meta-actions-v2.txt`) facilitate the systematic, automated discovery and resolution of these critical safety scenarios.

---

## 1. Formal Concepts & ISO Standard References

```
                                      ISO SCENARIO & HAZARD TAXONOMY
 +-------------------------------------------------------------------------------------------------------+
 |                                                                                                       |
 |   EDGE CASE (1-D Extreme Boundary)                                                                    |
 |   * Single operational/environmental parameter at limit (e.g., Rain = 50 mm/hr OR mu = 0.15)         |
 |   * ISO 21448 Cl. 6/7.3 | ISO TS 5083 Cl. 6.4                                                       |
 |                                                                                                       |
 |   CORNER CASE (Multi-D Confluence)                                                                    |
 |   * Multi-factor / multi-actor non-linear combination (e.g., Abusive Backing + Fog + Low Friction)   |
 |   * ISO 21448 Cl. 7.3, Annex B.3/C/F (Area 2/3 Triggering Conditions) | ISO TS 5083 Cl. 6.5 & Annex B    |
 |                                                                                                       |
 |   MISSING CASE (Specification Gap / Unanalyzed Blind Spot)                                           |
 |   * Omitted actor class, unmodeled misbehavior, or missing control sequence in system spec           |
 |   * ISO 21448 Cl. 7/8/9 (Area 3 Unknown Unsafe Reduction) | ISO TS 5083 Cl. 5 & Annex B                |
 |                                                                                                       |
 +-------------------------------------------------------------------------------------------------------+
```

### 1.1 Edge Case
* **Definition:** An operational scenario defined by an extreme, limit, or boundary value along a **single operational, environmental, or kinematic parameter dimension**.
* **ISO Standard Grounding:**
  * **ISO 21448:2022 (SOTIF), Clause 6 & Clause 7.3:** Defines single-variable performance limits and functional insufficiencies resulting from boundary environmental stressors—such as maximum rain precipitation rates (50.0 mm/hr), minimum road surface friction ($\mu = 0.15$), extreme ambient illuminance (100,000 lx solar glare), or peak deceleration demands ($-9.0\text{ m/s}^2$).
  * **ISO/DTS 5083:2023, Clause 6.4:** Classifies edge cases as single-parameter boundary conditions within the defined Operational Design Domain (ODD) that challenge sensor perception limits, Object and Event Detection and Response (OEDR) thresholds, or vehicle dynamic actuator saturation.

### 1.2 Corner Case
* **Definition:** A complex, high-risk scenario resulting from the **simultaneous confluence or non-linear combination of multiple parameter boundaries across multiple independent dimensions** (co-occurrence of multi-actor misbehaviors and multi-factor environmental/infrastructure stressors).
* **ISO Standard Grounding:**
  * **ISO 21448:2022 (SOTIF), Clause 7.3, Annex B.3, Annex C & Annex F:** Formally categorizes multi-factor **Triggering Conditions**. Corner cases represent conditions where individual parameters may lie within nominal operating bounds, but their joint occurrence induces a perception insufficiency, algorithm failure, or trajectory planning conflict. In the SOTIF 4-quadrant matrix, corner cases populate **Area 2 (Known Unsafe Scenarios)** or **Area 3 (Unknown Unsafe Scenarios)**.
  * **ISO/DTS 5083:2023, Clause 6.5 & Annex B:** Specifies multi-variable hazard scenarios resulting from simultaneous actor violations (e.g., an abusive wrong-way driver or sudden pedestrian dart-in) co-occurring under degraded environmental states (e.g., dense fog, road surface glare, or V2X/GNSS multipath interference).

### 1.3 Missing Case
* **Definition:** An unanalyzed, unidentified, or omitted scenario, actor class, misbehavior mode, or triggering condition that represents a **gap or blind spot in the system specification, ODD taxonomy, or hazard catalog**.
* **ISO Standard Grounding:**
  * **ISO 21448:2022 (SOTIF), Clauses 7, 8, 9 & Annex F:** Defines missing cases as specification gaps that place operational scenarios into **Area 3 (Unknown Unsafe Scenarios)**. Missing cases stem from unmodeled functional insufficiencies or unanalyzed OEDR triggers (e.g., failing to specify an ADS reaction for grouped troop columns, cabin passenger view obstructions, or abusive transit bus pull-outs). SOTIF mandates systematic scenario discovery to transition Area 3 scenarios into Area 2 (Known Unsafe, driving engineering redesign) or Area 1 (Known Safe).
  * **ISO/DTS 5083:2023, Clause 5 & Annex B:** Identifies missing cases as incomplete claims, missing evidence, or unaddressed scenario branches in the top-level **Safety Case argument**, requiring systematic hierarchical decomposition to verify that no functional or operational gaps remain.

---

## 2. Systematic Scenario Discovery Using Actors-Factors List & Meta-Actions

The structured **Actors-Factors Taxonomy** (`actors-factors-list-v4.txt`) and **Meta-Actions Framework** (`meta-actions-v2.txt`) provide a formal matrix structure that enables automated, systematic discovery of Edge Cases, Corner Cases, and Missing Cases.

```
                          SYSTEMATIC DISCOVERY MATRIX
 +-----------------------------------------------------------------------------------------------+
 |                                                                                               |
 |   ACTORS-FACTORS TAXONOMY                              META-ACTIONS FRAMEWORK                 |
 |   * 5 Actor Categories (26 Sub-classes)                * 16 Control Primitives ([ACT-01..16])   |
 |   * 3-State Compliance Engine [NONE|MISUSE|ABUSE]      * Structured Response Sequences        |
 |   * 6 ODD Factor Layers (SI Metrics)                   * Physical Kinematic Bounds            |
 |                                                                                               |
 |                                           ||                                                  |
 |                                           \/                                                  |
 |                                                                                               |
 |   1. EDGE CASE DISCOVERY   --> 1-D Parameter Boundary Sweeping                              |
 |   2. CORNER CASE DISCOVERY --> Cross-Layer Cartesian Product Generation                      |
 |   3. MISSING CASE DISCOVERY--> Specification Gap Matrix & Unanalyzed Cell Auditing            |
 |                                                                                               |
 +-----------------------------------------------------------------------------------------------+
```

### 2.1 Systematic Discovery of Edge Cases
* **Methodology: Single-Parameter Boundary Sweeping**
* **Mechanism:**
  1. Select a baseline scenario driven by a single Meta-Action primitive (e.g., `[ACT-03] Decelerate` or `[ACT-04] Stop`).
  2. Sweep a single quantitative metric in the **6-Layer ODD Factor Taxonomy** (Part III of `actors-factors-list-v4.txt`) to its absolute physical or statutory limit while keeping all other variables nominal.
* **Examples:**
  * *Layer 5.1 Sweeping:* Increasing precipitation rate from $0.0\text{ mm/hr}$ to the upper boundary of $50.0\text{ mm/hr}$ (Heavy Torrential Rain).
  * *Layer 1.2 Sweeping:* Decreasing road surface friction coefficient $\mu$ from $0.85$ (dry asphalt) to $0.15$ (glaze ice).
  * *Layer 4.1 Sweeping:* Decreasing Time-To-Collision (TTC) to the extreme safety threshold of $0.2\text{ s}$.

### 2.2 Systematic Discovery of Corner Cases
* **Methodology: Cross-Layer Combinatorial Cartesian Product Generation**
* **Mechanism:**
  1. Instantiate a multi-actor interaction using the **Universal 3-State Compliance Engine** (`compliance_state = NON_COMPLIANT`, `non_compliance_type = ABUSE`).
  2. Select an actor executing a high-energy violation from the **Misbehavior Regime** (e.g., `RUNNING_RED_LIGHT`, `UNLAWFUL_ABUSIVE_BACKING`, or `WRONG_WAY_DRIVING`).
  3. Inject simultaneous stress factors across multiple ODD layers from Part III of `actors-factors-list-v4.txt`:
     * **Layer 1:** Steep Grade ($> \pm 10\%$) + Narrow Carriageway ($< 3.5\text{ m}$).
     * **Layer 5:** Dense Fog ($1.0\text{–}20.0\text{ m}$ visibility) + Night Unlit ($0.0001\text{ lx}$).
     * **Layer 6:** Sensor Camera Glare + GNSS Denied Tunnel State.
  4. Evaluate the required ego response using a multi-primitive Meta-Action sequence (e.g., `[ACT-05] Yield` $\rightarrow$ `[ACT-03] Decelerate` $\rightarrow$ `[ACT-12] Shift Outside of Lane` $\rightarrow$ `[ACT-04] Stop`).
* **Outcome:** Systematically exposes complex SOTIF triggering conditions (ISO 21448 Clause 7.3) that induce perception or planning failure modes.

### 2.3 Systematic Discovery of Missing Cases (Specification Gap Analysis)
* **Methodology: Exhaustive Matrix Auditing & Unanalyzed Cell Detection**
* **Mechanism:**
  1. Construct an exhaustive $N$-dimensional truth table defined by:
     $$\text{Discovery Matrix} = \text{Actor Sub-Class (26)} \times \text{Compliance Mode (3)} \times \text{ODD Factor Layer (6)} \times \text{Meta-Action (16)}$$
  2. Cross-audit the system requirement specification (`behavioral_refinements-v2.txt`) against every cell in this matrix.
  3. Identify any cell that lacks an explicit behavioral requirement or control sequence.
* **Example Discovered Gap:**
  * *Unanalyzed Cell:* Transit Bus (`actor_category = MOTOR_VEHICLE`) executing `ABUSIVE_TRANSIT_BUS_PULL_OUT` under Layer 6.3 `PASSENGER_LOAD_VIEW_OBSTRUCTION` at a Layer 2.4 `20ft Marked Crosswalk Buffer`.
  * *Resolution:* Prior to this framework, this combination represented an unanalyzed **Missing Case** (SOTIF Area 3). By identifying the empty cell in the matrix, engineers immediately author an explicit requirement (e.g., `ADS-REQ-008A` update) with a deterministic Meta-Action control sequence (`[ACT-05] Yield` $\rightarrow$ `[ACT-03] Decelerate` $\rightarrow$ `[ACT-04] Stop`), converting the unknown scenario into a verified, safe system capability (SOTIF Area 1).
