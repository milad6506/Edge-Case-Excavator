# Examples — audit results on real datasets

Committed outputs of running the `excavator/` engine against real scenario
databases. Dataset files themselves are **never** committed — only the audit
results, scrubbed of local filesystem identifiers.

| Example | Dataset | Levels | Contents |
|---|---|---|---|
| `drivelm-full/` | DriveLM-nuScenes (696 scenario sequences, 6 surround cameras) | L1 text + L1c close-reading | `findings.txt`, `excavation_report_slim.json`, `coverage_matrix.html` |

## drivelm-full

Full-corpus L1 textual audit of DriveLM-nuScenes against taxonomy v6.0 + 221
behavioral expectations (352 audited cases). Close-reading by
`z-ai/glm-5.3-flash` filtered keyword false positives.

Headline: COVERED 86 · COVERED_WEAK 55 · FALSE_POSITIVE 121 · TEXT_ABSENT 90.

Notable gaps surfaced (details in `findings.txt`):

- ODD bands unannotated across the board: rain bands, twilight/streetlit
  illuminance, dense fog, snow/ice friction, lane/shoulder width, headways
- Actor classes absent from text: children (as a class), intoxicated/impaired
  pedestrians, grouped processions, shuttle vans, railway crews
- 65 of 221 behavioral expectations have no triggering sequence in the corpus
  (28 Vienna, 17 AVSC-VRU, 11 AVSC-ODD, 6 Texas, 3 First-Responder)
- 200 corner-case candidate pairs from co-occurrence mining

`excavation_report_slim.json` keeps per-case verdicts and close-read reasons;
the full-evidence report (~4.3 MB with snippets and per-case sequence lists)
stays local under gitignored `runs/`.

## Reproducing

```bash
python3 -m excavator.cli excavate \
  --dataset-root <your DriveLM root> \
  --adapter drivelm \
  --levels text \
  --env-file <your .env with OPENROUTER_API_KEY> \
  --out runs/drivelm_full
```

Then copy `runs/drivelm_full/findings.txt`,
`excavation_report_slim.json` and `coverage_matrix.html` here. Add one row per
new dataset (Waymo, CARLA, internal corpora) following the same layout.
