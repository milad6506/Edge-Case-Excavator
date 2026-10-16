#!/usr/bin/env python3
"""P1: parse the Excavator reference specs into machine-readable JSON.

Inputs : actors-factors-list-v6.txt, behavioral_refinements-v2.txt, meta-actions-v2.txt
Outputs: reference/taxonomy_v6.json, reference/expectations_v2.json

Design: section-aware walker. Every bullet line inside a recognized section is
classified (sub-class | kinematic | movement-regime | misbehavior | state-enum |
enum | band | buffer | metric); anything unclassified lands in parse_warnings
so coverage can be driven to 100% iteratively.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "actors-factors-list-v6.txt"
EXP_SRC = ROOT / "behavioral_refinements-v2.txt"
ACT_SRC = ROOT / "meta-actions-v2.txt"
OUT = ROOT / "reference"

NUM = r"(-?[\d.]+)"
WARNINGS = []


def warn(line_no, line, why):
    WARNINGS.append({"line": line_no, "why": why, "text": line.strip()[:160]})


def num(x):
    try:
        return float(x)
    except ValueError:
        return None


def parse_bounds(text):
    """'- Length: 4.0m to 5.2m | Width: 1.7m to 2.1m | Height: 1.4m to 1.9m'"""
    dims = {}
    for part in text.split("|"):
        part = part.strip().lstrip("- ").strip()
        m = re.match(r"([A-Za-z][\w /]*?):\s*" + NUM + r"\s*([a-zµ°/+²³]+)\s*to\s*" + NUM + r"\s*([a-zµ°/+²³]+)", part)
        if m:
            key = m.group(1).strip().lower().replace(" ", "_")
            dims[key] = {"min": num(m.group(2)), "max": num(m.group(4)), "unit": m.group(3)}
        elif part and not part.startswith(("Seated",)):
            dims[part[:40]] = part
    return dims or None


def parse_kv_ranges(text):
    """'mu = 0.70 to 0.85' | 'stopping_distance_multiplier = 2.5x to 4.0x'"""
    out = {}
    for part in text.split("|"):
        part = part.strip()
        m = re.match(r"([\w /]+?)\s*=\s*" + NUM + r"(x?)\s*(?:to\s*" + NUM + r"(x?))?\s*(.*)", part)
        if not m:
            out.setdefault("_raw", []).append(part)
            continue
        key = m.group(1).strip().lower().replace(" ", "_")
        rng = [num(m.group(2))] if m.group(4) is None else [num(m.group(2)), num(m.group(4))]
        if m.group(3) or m.group(5):
            rng = {"range": rng, "per": "x" if (m.group(3) or m.group(5)) else ""}
        out[key] = rng
        tail = m.group(6).strip()
        if tail:
            out.setdefault("_notes", []).append(tail)
    return out


def parse_band_label(label):
    """'Night Unlit (Overcast/Moonless)' -> name + note"""
    m = re.match(r"(.+?)\s*\((.+)\)\s*$", label)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return label.strip(), None


def parse_taxonomy(lines):
    tax = {
        "version": None, "source_file": SRC.name,
        "unit_system": None, "standards": [],
        "architecture": {"compliance_states": [], "compliance_definitions": {}},
        "actor_categories": [], "factor_layers": [], "parse_warnings": WARNINGS,
    }
    cat = layer = section = None
    cur_subclass = cur_misgroup = None
    section_items = None
    skip = set()

    def flush_section():
        nonlocal section, section_items
        if section and section_items is not None:
            section["items"] = section_items
        section, section_items = None, None

    for ln, raw in enumerate(lines, 1):
        if ln in skip:
            continue
        line = raw.rstrip()
        if not line.strip():
            continue
        s = line.strip()
        if s.startswith("Filename:") or re.fullmatch(r"-{10,}", s):
            continue

        m = re.match(r"MASTER UNIFIED .*VERSION (\S+)", s)
        if m:
            tax["version"] = m.group(1)
            continue
        if s.startswith("Unit System:"):
            tax["unit_system"] = s.split(":", 1)[1].strip()
            continue
        if s.startswith("Standards Alignment:"):
            tax["standards"] = [x.strip() for x in re.split(r",\s*", s.split(":", 1)[1]) if x.strip()]
            for off, cont in enumerate(lines[ln:], start=ln + 1):  # off = 1-based line number
                if cont.strip() and not cont.strip().startswith("="):
                    tax["standards"] += [x.strip() for x in re.split(r",\s*", cont.strip()) if x.strip()]
                    skip.add(off)
                else:
                    break
            continue

        m = re.match(r"CATEGORY (\d+): (.+?) \(actor_category = (\w+)\)", s)
        if m:
            flush_section()
            cat = {"category_id": int(m.group(1)), "name": m.group(2).title(),
                   "actor_category": m.group(3), "sub_classes": [],
                   "movement_regime": [], "misbehavior_regime": [],
                   "state_machines": {}, "kinematic_bounds": {}, "sections": []}
            tax["actor_categories"].append(cat)
            layer = None
            cur_subclass = cur_misgroup = None
            continue

        m = re.match(r"LAYER (\d+): (.+)", s)
        if m:
            flush_section()
            layer = {"layer_id": int(m.group(1)), "name": m.group(2), "sections": []}
            tax["factor_layers"].append(layer)
            cat = None
            cur_subclass = cur_misgroup = None
            continue

        # numbered part-level architecture sections (Part I)
        m = re.match(r"^(\d+)\. ([A-Z0-9 3()&,'/-]+)$", s)
        if m and layer is None and cat is None:
            flush_section()
            section = {"id": m.group(1), "title": m.group(2).title(), "part": "architecture"}
            section_items = []
            tax["architecture"].setdefault("_sections", []).append(section)
            continue

        # subsection header, optionally with inline value after the colon
        m = re.match(r"^(\d+\.\d+)\s+(.+?)(?:\s*\(Grounded in (.*)\))?:\s*(.*)$", s)
        if m:
            flush_section()
            title = m.group(2).strip()
            section = {"id": m.group(1), "title": title}
            if m.group(3):
                section["grounding"] = m.group(3).strip()
            section_items = []
            if cat is not None:
                cat["sections"].append(section)
            elif layer is not None:
                layer["sections"].append(section)
            else:
                warn(ln, line, "section outside category/layer")
            if m.group(4):
                section_items.append({"type": "statement", "name": title, "text": m.group(4).strip()})
            cur_subclass = cur_misgroup = None
            continue

        if section is None:
            if not s.startswith("=") and not s.startswith("PART "):
                warn(ln, line, "outside any section")
            continue

        # --- classified bullet forms ---
        if s.startswith("* "):
            body = s[2:].strip()

            m = re.match(r"\[ACT-(\d+)\]\s*([^:]+):\s*(.+)", body)
            if m:
                cat["movement_regime"].append(
                    {"act": f"ACT-{int(m.group(1)):02d}", "name": m.group(2).strip(), "description": m.group(3).strip()})
                continue

            m = re.match(r"(misuse|abuse)_misbehaviors(?:\s*\((.+?)\))?:\s*$", body)
            if m:
                cur_misgroup = {"type": m.group(1), "group": (m.group(2) or "General").strip(), "tokens": []}
                cat["misbehavior_regime"].append(cur_misgroup)
                continue

            m = re.match(r"(.+?):\s*\[([^\]]+)\]\s*$", body)
            if m and ("States" in m.group(1) or "Types" in body.split(":")[0]):
                label, note = parse_band_label(m.group(1))
                vals = [v.strip() for v in re.split(r"[|,]", m.group(2)) if v.strip()]
                rec = {"name": label, "values": vals}
                if note:
                    rec["note"] = note
                if cat is not None:
                    key = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
                    cat["state_machines"][key] = rec
                else:
                    section_items.append({"type": "enum", **rec})
                continue

            # generic enum list (Types:/Categories:/Equipment:/Status:/...)
            m = re.match(r"([\w /()-]+?):\s*\[([^\]]+)\]", body)
            if m:
                label, note = parse_band_label(m.group(1))
                rec = {"type": "enum", "name": label,
                       "values": [v.strip() for v in re.split(r"\|", m.group(2)) if v.strip()]}
                if note:
                    rec["note"] = note
                section_items.append(rec)
                continue

            # buffer lines: '200 ft (60.96m) Crest / ...'
            if re.match(r"^\d+(\.\d+)?\s*(ft|m|km/h|lx|mm/hr)\b", body):
                section_items.append({"type": "buffer", "text": body})
                continue

            # kinematic: 'Forward Velocity (v_fwd): 0.0 m/s to 45.0 m/s (...)'
            m = re.match(r"(.+?)\((\w+)\):\s*" + NUM + r"\s*([\wµ°/²³]+)\s*to\s*" + NUM + r"\s*([\wµ°/²³]+)\s*(.*)", body)
            if m:
                label, note = parse_band_label(m.group(1))
                rec = {"type": "kinematic", "name": label, "param": m.group(2),
                       "min": num(m.group(3)), "max": num(m.group(5)),
                       "unit": m.group(4)}
                if m.group(6):
                    rec["note"] = m.group(6).strip("()")
                section_items.append(rec)
                continue

            # band: 'Dry Asphalt / Concrete: mu = 0.70 to 0.85 | stopping...'
            m = re.match(r"(.+?):\s*(.+)$", body)
            if m and "=" in m.group(2):
                label, note = parse_band_label(m.group(1))
                rec = {"type": "band", "name": label, "params": parse_kv_ranges(m.group(2))}
                if note:
                    rec["note"] = note
                section_items.append(rec)
                continue

            # simple numeric range: 'Light Rain: 0.1 mm/hr to 2.5 mm/hr (note)'
            m = re.match(r"(.+?):\s*" + NUM + r"\s*([\wµ°/²³]+)\s*to\s*" + NUM + r"\s*([\wµ°/²³]+)\s*(.*)", body)
            if m:
                label, note = parse_band_label(m.group(1))
                rec = {"type": "range", "name": label, "min": num(m.group(2)), "max": num(m.group(4)),
                       "unit": m.group(3)}
                if m.group(5):
                    rec["note"] = m.group(5).strip("()")
                if note:
                    rec["note"] = note
                section_items.append(rec)
                continue

            # sub-class header: colon-terminated, or bare inside a Sub-Classes section
            ends_colon = body.endswith(":")
            in_subclass_section = "sub-class" in (section.get("title") or "").lower()
            m = re.match(r"(.+?)(?:\s*\((.+)\))?:?\s*$", body)
            if m and cat is not None and (ends_colon or in_subclass_section) \
                    and "misbehavior" not in (section.get("title") or "").lower() \
                    and "regime" not in (section.get("title") or "").lower():
                cur_subclass = {"name": m.group(1).strip().rstrip(":").strip(), "variants": None, "bounds": None}
                if m.group(2):
                    cur_subclass["variants"] = m.group(2).strip()
                cat["sub_classes"].append(cur_subclass)
                continue

            # labeled statement: 'STATIONARY_VERGE_WAITING: Standing at ...'
            m = re.match(r"(.+?):\s*(.+)$", body)
            if m:
                section_items.append({"type": "statement", "name": m.group(1).strip(), "text": m.group(2).strip()})
                continue

            section_items.append({"type": "prose" if "cross-reference" in (section.get("title") or "").lower()
                                  else "text", "unclassified": "cross-reference" not in (section.get("title") or "").lower(),
                                  "text": body})
            continue

        if s.startswith("- "):
            body = s[2:].strip()
            if cur_misgroup is not None:
                m = re.match(r"([A-Z0-9_]+)\s*\((.*)\)", body)
                if m:
                    cur_misgroup["tokens"].append({"token": m.group(1), "description": m.group(2)})
                else:
                    cur_misgroup["tokens"].append({"token": body, "description": None})
                    warn(ln, line, "misbehavior token without parenthetical")
                continue
            dims = parse_bounds(body)
            if dims and cur_subclass is not None:
                cur_subclass["bounds"] = dims
                continue
            # metric sub-bullet: 'Number of Lanes: 1 to 8 lanes per carriageway'
            m = re.match(r"(.+?):\s*(.+)$", body)
            if m:
                rec = {"type": "metric", "name": m.group(1).strip(), "text": m.group(2).strip()}
                section_items.append(rec)
                continue
            section_items.append({"type": "text", "text": body})
            warn(ln, line, "unclassified '- ' bullet")
            continue

        if not s.startswith(("=", "PART ")):
            if section is not None and section_items is not None:
                if section_items and section_items[-1].get("type") == "prose":
                    section_items[-1]["text"] += " " + s
                else:
                    section_items.append({"type": "prose", "text": s})
            else:
                warn(ln, line, "stray line")

    flush_section()
    # prune helper keys
    tax["architecture"].pop("_sections", None)
    unclassified = [
        {"section": s["id"], "text": it["text"]}
        for cat in tax["actor_categories"] for s in cat.get("sections", [])
        for it in s.get("items", []) if it.get("unclassified")
    ] + [
        {"section": f"L{l['layer_id']}.{s['id']}", "text": it["text"]}
        for l in tax["factor_layers"] for s in l["sections"]
        for it in s.get("items", []) if it.get("unclassified")
    ]
    tax["unclassified_items"] = unclassified
    return tax


def parse_meta_actions(lines):
    acts = []
    for raw in lines:
        m = re.match(r"\s*\[ACT-(\d+)\]\s*(.+)", raw.rstrip())
        if m:
            acts.append({"act": f"ACT-{int(m.group(1)):02d}", "name": m.group(2).strip(), "category": None,
                         "description": None})
            continue
        m2 = re.match(r"\s*Category:\s*(.+)", raw)
        if m2 and acts:
            acts[-1]["category"] = m2.group(1).strip()
            continue
        m3 = re.match(r"\s*Description:\s*(.+)", raw)
        if m3 and acts:
            acts[-1]["description"] = " ".join(str(acts[-1]["description"] or "") .split() + m3.group(1).split()).strip()
    return acts


def parse_expectations(lines):
    txt = "\n".join(lines)
    ids = re.findall(r"^\[([A-Za-z0-9-]+)\]", txt, re.M)
    blocks = re.split(r"^\[[A-Za-z0-9-]+\]", txt, flags=re.M)[1:]
    exps = []
    for eid, b in zip(ids, blocks):
        e = {"id": eid}
        f = lambda label: (re.search(rf"{label}:\s*(.+)", b) or [None, None])[1]
        e["source_framework"] = (f("Source Framework") or "").strip()
        e["applicability_area"] = (f("Applicability Area") or "").strip()
        m = re.search(r"Category:\s*(.+?)\s*\|\s*Sub-Category:\s*(.+)", b)
        e["category"], e["sub_category"] = (m.group(1).strip(), m.group(2).strip()) if m else (None, None)
        e["statutory_ref"] = (f("Statutory / Standard Ref") or "").strip()
        e["triggers"] = [t.strip() for t in (f("Triggering Conditions / Context") or "").split(",") if t.strip()]
        m = re.search(r"Behavioral Expectation Text:\s*(.+?)(?=\n\s*\n|\n\s*Required Meta-Action Sequence)", b, re.S)
        e["text"] = " ".join(m.group(1).split()) if m else None
        seq = []
        for sm in re.finditer(r"^\s*\d+\.\s*\[ACT-(\d+)\]\s*([^(\n]+?)\s*(?:\((.*)\))?\s*$", b, re.M):
            seq.append({"act": f"ACT-{int(sm.group(1)):02d}", "name": sm.group(2).strip(),
                        "note": (sm.group(3) or "").strip() or None})
        e["meta_action_sequence"] = seq
        exps.append(e)
    return exps


def main():
    OUT.mkdir(exist_ok=True)
    tax = parse_taxonomy(SRC.read_text().splitlines())
    tax["meta_actions"] = parse_meta_actions(ACT_SRC.read_text().splitlines())
    exps = parse_expectations(EXP_SRC.read_text().splitlines())

    (OUT / "taxonomy_v6.json").write_text(json.dumps(tax, indent=1, ensure_ascii=False) + "\n")
    (OUT / "expectations_v2.json").write_text(json.dumps(exps, indent=1, ensure_ascii=False) + "\n")

    subs = [(c["name"], len(c["sub_classes"])) for c in tax["actor_categories"]]
    mis = Counter(t["token"] for c in tax["actor_categories"] for g in c["misbehavior_regime"] for t in g["tokens"])
    acts_used = Counter(s["act"] for e in exps for s in e["meta_action_sequence"])
    print(f"taxonomy v{tax['version']}: {len(tax['actor_categories'])} categories, "
          f"{sum(n for _, n in subs)} sub-classes {subs}")
    print(f"  misbehavior tokens: {sum(mis.values())} | movement regimes: "
          f"{[len(c['movement_regime']) for c in tax['actor_categories']]}")
    print(f"  factor layers: {[(l['layer_id'], len(l['sections'])) for l in tax['factor_layers']]}")
    print(f"  meta_actions parsed: {len(tax['meta_actions'])}")
    print(f"expectations: {len(exps)} | with sequence: {sum(1 for e in exps if e['meta_action_sequence'])}")
    print(f"  ACT usage: {dict(sorted(acts_used.items()))}")
    print(f"  unclassified bullets: {len(tax['unclassified_items'])}")
    for u in tax["unclassified_items"][:10]:
        print(f"    [{u['section']}] {u['text'][:90]}")
    print(f"parse_warnings: {len(WARNINGS)}")
    for w in WARNINGS[:12]:
        print(f"  L{w['line']} {w['why']}: {w['text'][:100]}")
    return 0 if not WARNINGS else 1


if __name__ == "__main__":
    sys.exit(main())
