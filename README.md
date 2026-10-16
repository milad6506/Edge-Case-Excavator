# Autonomous Driving System (ADS) Behavioral Taxonomy & Testable Scenario Framework

This repository provides a comprehensive, mathematically grounded, and statutory-compliant framework for defining, parameterizing, and evaluating **Automated Driving System (ADS)** behavioral competencies and Operational Design Domains (ODDs). 

Derived from international treaties, state traffic codes, NHTSA pre-crash typologies, ISO safety standards, and AVSC best practices, this repository provides the structural foundation required for **automated scenario generation, SOTIF safety case engineering, sim-to-real testing, and perception log auto-labeling**.

---

## 📁 Repository Structure & Core Specifications

The repository consists of three core specification files that form an end-to-end taxonomy for autonomous vehicle testing:

| File Name | Description | Key Specifications |
| :--- | :--- | :--- |
| **`meta-actions-v2.txt`** | **Control Action Primitives Framework** | Defines **16 standardized control primitives (`[ACT-01]` through `[ACT-16]`)** grounded in USDOT/NHTSA Report DOT HS 812 623 (Table 42). Establishes standardized longitudinal, lateral, fallback handover, and directional reversing primitives. |
| **`actors-factors-list-v6.txt`** | **Unified Actor & 6-Layer ODD Taxonomy** | Establishes a **Universal 3-State Compliance Architecture (`[NONE \| MISUSE \| ABUSE]`)**, 42 actor sub-classes across 5 categories, 49 misuse/abuse misbehavior primitives, differentiated vehicle vs. non-vehicle movement regimes, and a **6-Layer ODD Factor Catalog** with SI metrics and statutory clearance thresholds — every section grounded in named standards (ISO, AVSC, NHTSA, Vienna, Texas Code, Waymo labeling spec). |
| **`behavioral_refinements-v2.txt`** | **Refined ADS Behavioral Expectations Catalog** | Contains **221 refined ADS Behavioral Requirements**. Each requirement maps 1-to-1 to a structured 4-step control response sequence composed of the 16 Meta-Actions. Fully covers proactive driving, reactive responses to external misuse/abuse (106 reactive items), emergency MRC transitions, and reversing controls. |

---

## 🔬 Derivation Methodology & Process

The specifications in this repository were derived through a rigorous 5-stage synthesis and formalization pipeline:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Stage 1: Statutory & Consortium Behavioral Requirement Extraction               │
│ Extract 221 rules from UN Vienna Convention, Texas Code, AVSC & ISO standards   │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Stage 2: Meta-Action Control Primitive Normalization                            │
│ Ground control primitives in NHTSA DOT HS 812 623 (Table 42) & extend [ACT-16] │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Stage 3: Universal Compliance & 6-Layer ODD Decoupled Modeling                  │
│ Establish 3-State Compliance (COMPLIANT/MISUSE/ABUSE) & SI metric ODD layers    │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Stage 4: 1-to-1 Control Sequence Mapping & Reactive Misuse/Abuse Synthesis      │
│ Map 221 rules to 4-step Meta-Action sequences; formalize 106 reactive responses │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Stage 5: Exhaustive Cross-Audit & Combinatorial Verification                    │
│ Verify 100% coverage across 109 multi-actor & 181 multi-factor interaction cases  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Stage 1: Requirement Extraction & Formalization
* Extracted and formalized requirements from international laws (**UN Vienna Convention on Road Traffic 1968**), state statutes (**Texas Transportation Code Ch. 545**), safety frameworks (**ISO 21448 / SOTIF**, **ISO/AWI TS 5083**), and consortium guidelines (**AVSC** VRU, First Responder, and ODD lexicon standards).
* Filtered out ambiguous phrasing to produce deterministic, testable requirement statements.

### Stage 2: Control Primitive Normalization (`meta-actions-v2.txt`)
* Grounded all dynamic vehicle maneuvers in the USDOT/NHTSA 15-action control framework (USDOT Report DOT HS 812 623, Page 59, Table 42).
* Extended the framework with **`[ACT-16] Reverse / Back Up`** to provide explicit coverage for backward longitudinal motion ($v < 0$) grounded in Vienna Convention Art. 14/25 and Texas Transportation Code Sec. 545.415.

### Stage 3: Decoupled Taxonomy Construction (`actors-factors-list-v6.txt`)
* Separated dynamic actor capabilities from environmental factor layers.
* Formulated a **Universal 3-State Compliance Engine** applicable across all road users:
  1. `COMPLIANT` (`non_compliance_type = NONE`): Strict statutory rule adherence.
  2. `MISUSE` (`non_compliance_type = MISUSE`): Inadvertent, passive, negligent, or confused non-compliance without active hostile intent (e.g., forgotten signals, stop-line overshoots, passive jaywalking).
  3. `ABUSE` (`non_compliance_type = ABUSE`): Active, aggressive, or severe statutory violations (e.g., running red lights/stop signs, wrong-way driving, unlawful backing on highways/tunnels, sudden child dart-ins).
* Differentiated movement regimes: **Motor vehicles** are driven strictly by the 16 Meta-Actions, while **non-vehicles** (VRUs, animals, static hazards) use domain-specific physical trajectory patterns.
* Structured a **6-Layer ODD Taxonomy** (ISO 21448 / AVSC alignment) using SI metric units ($m$, $m/s$, $m/s^2$, $mm/hr$, $lx$, $km/h$, $\mu$) and statutory clearance buffers ($200\text{ft}$ crest, $100\text{ft}$ rail, $30\text{ft}$ signal, $20\text{ft}$ crosswalk, $15\text{ft}$ hydrant, $1.5\text{m}$ VRU berth).

### Stage 4: 1-to-1 Control Sequence Refinement (`behavioral_refinements-v2.txt`)
* Mapped each of the 221 requirements to a structured 4-step control response sequence composed of the 16 Meta-Actions.
* Resolved template over-generalizations by assigning explicit primitives for aborted passes (`[ACT-09]`), aborted lane changes (`[ACT-07]`), emergency shoulder encroachments (`[ACT-12]`), human fallback handovers (`[ACT-14]`), and directional reversing (`[ACT-16]`).
* Mapped 106 explicit reactive sequences defining how the ADS must defensively respond to surrounding road user **Misuse** and **Abuse**.

### Stage 5: Exhaustive Cross-Audit & Validation
* Verified that the taxonomy completely covers all **109 multi-actor interaction cases** (e.g., lead vehicle + oncoming traffic + trailing overtaker), **181 multi-factor co-occurrence cases** (e.g., heavy rain + ice friction $\mu=0.15$ + dense fog), and **105 simultaneous multi-actor/multi-factor test cases**.

---

## 📚 Complete Source References & Grounding

The frameworks in this repository are grounded in and traceable to the following 12 foundational sources:

1. **UN Vienna Convention on Road Traffic (1968)**
   * *Grounding:* Core rules of the road, right-of-way, mountain passes (Art. 12), level crossings (Art. 19), tunnels (Art. 25 bis), vehicle lighting (Art. 32), reversing prohibitions (Art. 14/25), and VRU protections.
2. **Texas Transportation Code — Chapter 545 ("Rules of the Road")**
   * *Grounding:* State legal requirements, Move-Over law (Sec. 545.157), school bus stop-arms (Sec. 545.066), shoulder backing prohibitions (Sec. 545.415), passenger cabin interference (Sec. 545.417), and statutory clearance buffers.
3. **USDOT / NHTSA Technical Report DOT HS 812 623**
   * *Title:* *A Framework for Automated Driving System Testable Cases and Scenarios* (2018).
   * *Grounding:* Table 42 control response sequences, 15 baseline meta-actions, OEDR tactical maneuver evaluation.
4. **AVSC Best Practice for Interactions Between ADS-DVs and VRUs (`AVSC00009202208`)**
   * *Grounding:* Vulnerable Road User perception, kinesthetic tracking, child/preteen behavioral envelopes, and non-drivable boundary monitoring.
5. **AVSC Best Practice for Describing an Operational Design Domain (`AVSC00002202004`)**
   * *Grounding:* Bottom-up ODD lexicon, metric environmental variables (rain rates, fog severity, surface distress), and non-permissive weather suspension thresholds.
6. **AVSC Best Practice for First Responder Interactions (`AVSC-I-01-2024`)**
   * *Grounding:* Traffic stops, emergency scene stabilization, manual officer gestures/flashlights, high-voltage de-powering, and vehicle immobilization.
7. **ISO 21448:2022 — Safety of the Intended Functionality (SOTIF)**
   * *Grounding:* Triggering condition identification, functional insufficiencies, sensor glare/noise, and hazardous scenario mitigation.
8. **ISO/AWI TS 5083 — Safety of Automated Driving Systems (L3/L4)**
   * *Grounding:* Safety case architecture, conflict avoidance principles, and Dynamic Driving Task (DDT) fallback procedures.
9. **NHTSA Pre-Crash Scenario Typology (DOT HS 810 767)**
   * *Grounding:* 37 pre-crash scenario families, vehicle control loss, junction conflicts, and lead-vehicle rear-end typologies.
10. **UC PATH Autonomous Vehicle Behavioral Competencies Peer Review**
    * *Grounding:* Functional safety testing transitions, ODD flexibility, and low-speed shuttle/valet competency definitions.
11. **Waymo Open Dataset Labeling Specifications**
    * *Grounding:* 3D Lidar / 2D camera bounding box conventions, actor classification transitions, and No Label Zone protocols.
12. **NHTSA / Autonomous Driving Model Prompting & Perception Studies**
    * *Grounding:* Chain-of-Thought error cascade mitigation and conservative perception thresholding.

---

## 🎯 Target Use Cases & Applications

This repository is designed to serve as an actionable dataset and specification for multiple engineering and regulatory workflows:

```
                                  ┌─────────────────────────────────────────┐
                                  │   Repository Specifications & Data      │
                                  │ meta-actions | actors-factors | reqs    │
                                  └────────────────────┬────────────────────┘
                                                       │
         ┌──────────────────────┬──────────────────────┼──────────────────────┬──────────────────────┐
         ▼                      ▼                      ▼                      ▼                      ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   Automated      │  │  Safety Case &   │  │ Auto-Labeling &  │  │ Sim-to-Real Edge │  │  Regulatory      │
│ Scenario Gen.    │  │ SOTIF Validation │  │ Perception Logs  │  │ Stress Testing   │  │ Compliance       │
│ (CARLA/OpenSCEN) │  │ (ISO 21448/5083) │  │ (Waymo/NuScenes) │  │ (Adversarial)    │  │ (NHTSA/UNECE)    │
└──────────────────┘  └──────────────────┘  └──────────────────┘  └──────────────────┘  └──────────────────┘
```

### 1. Automated Scenario Generation & Synthetic Test Synthesis
* **OpenSCENARIO & Simulator Ingestion:** Programmatically map `behavioral_refinements-v2.txt` control sequences and `actors-factors-list-v6.txt` ODD layers into simulator test scripts (CARLA, SVL, Metadrive, Applied Intuition).
* **Combinatorial Test Matrix Generation:** Instantiate combinations by pairing any of the 221 requirement baselines with the 42 actor sub-classes, 49 misbehavior modes, and 6 ODD factor layers to generate millions of unique executable scenario variants.

### 2. SOTIF & Functional Safety Case Engineering (ISO 21448 / ISO 5083)
* **Triggering Condition Mapping:** Use the 6-Layer ODD factor catalog to define known hazardous triggering conditions (e.g., solar glare + dense fog + low friction $\mu=0.15$).
* **Traceable Safety Arguments:** Provide deterministic evidence for ISO 5083 safety cases by demonstrating that the ADS executes compliant meta-action sequences (`[ACT-01]`–`[ACT-16]`) under all statutory and adverse conditions.

### 3. Perception Log Auto-Labeling & Dataset Structuring
* **Ground-Truth Data Annotation:** Apply the **Universal 3-State Compliance Engine (`COMPLIANT` / `MISUSE` / `ABUSE`)** to auto-label real-world driving logs (e.g., Waymo Open Dataset, nuScenes, Argoverse).
* **Behavioral Tagging:** Label trajectories with exact meta-action primitives (e.g., tagging a vehicle trajectory as executing `[ACT-11] Shift Within Lane` or `[ACT-16] Reverse`).

### 4. Sim-to-Real Benchmark & Adversarial Edge-Case Stress Testing
* **Adversarial Injection:** Combine high-risk ODD factors (e.g., mountain pass grade $> \pm 10\%$, narrow lane $<3.5\text{m}$) with severe road user **Abuse** (e.g., wrong-way driving `ADS-REQ-024B`, child dart-ins `ADS-REQ-016A`, or school bus stop-arm bypasses `ADS-REQ-TX-012A`) to evaluate ADS Minimal Risk Condition (MRC) fallback boundaries (`[ACT-14]` / `[ACT-15]`).

### 5. Regulatory Certification & Verification Framework
* **Statutory Compliance Validation:** Serves as a standardized benchmark for regulatory agencies (NHTSA, UNECE, state DOTs) to systematically evaluate whether an ADS model complies with local statutory traffic codes (e.g., Texas Transportation Code Ch. 545 or UN Vienna Convention).

---

## 📊 Summary Statistics & Metrics

```text
================================================================================
REPOSITORY METRICS SUMMARY
================================================================================
• Total Refined Behavioral Expectations : 221
  - Proactive Driving Competencies     : 115 Requirements
  - Reactive Misuse/Abuse Responses    : 106 Requirements
  - Minimal Risk Condition (MRC) Fallbacks: 27 Requirements

• Universal Control Actions            : 16 Meta-Actions ([ACT-01] to [ACT-16])
• Universal Compliance States          : 3 Modes (COMPLIANT, MISUSE, ABUSE)
• Actor Taxonomy Catalog               : 5 Categories | 42 Sub-Classes
• Misbehavior Primitives               : 49 Items (Misuse & Abuse)
• Operational Design Domain Layers     : 6 Layers | 22 Sub-Sections | 80+ SI Metrics
• Total Base Statutory Sources         : 10 Grounding Frameworks
================================================================================
```

---

## 📜 License & Citation

This framework and taxonomy specification are open-source and structured for industry collaboration, academic research, and regulatory benchmarking. 

If you utilize this repository in your research or autonomous system safety architecture, please cite:

```bibtex
@database{ads_behavioral_taxonomy_2026,
  title={Unified ADS Behavioral Taxonomy, 6-Layer ODD Architecture, and Testable Scenario Framework},
  author={Gemini Notebook ADS Safety Working Group},
  year={2026},
  publisher={GitHub Repository},
  note={Grounded in UN Vienna Convention, Texas Transportation Code Ch. 545, USDOT DOT HS 812 623, AVSC, and ISO 21448}
}
```
