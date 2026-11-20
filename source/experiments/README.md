# experiments/: E1, E2, E2b, E3, E4

The experiments compare the output of the unified mapping (`../mapping/`) with the
object-centric logs of InfSys and Hobeck et al., and check its consistency. They read the
outputs of `map_all.py` in `data/<dataset>/mapped/` and never change the mapping. The
input/reference pairs are listed in `../../data/README.md`.

E1, E2, and E2b are numbered as in the companion document
([`docs/unified-representation.pdf`](../../docs/unified-representation.pdf)). The paper
(Section 5) reports the round trip E2b within E2, E3 as the consistency experiment, and
E4 as its prediction example.

| Script | Experiment | Inputs → references | Result |
|---|---|---|---|
| `e1_infsys.py` | **E1.** The collaboration view α_C(μ_U(L)) that the mapping writes (`<out>_infsys.sqlite`) equals the InfSys OCEL (exact reconstruction) | `pena/*_collab.xes` (collaboration and complete profiles) of Artificial1, Artificial5, Healthcare, Real4, and the BPIC 2013 CL → `infsys/*.sqlite` | `results/e1_infsys.{md,json}` |
| `e2_hobeck.py` | **E2.** The export η_H of the unified output is equivalent to Hobeck et al.'s OCEL, from the same input | `hobeck/collectivelog_<n>_uniqueInteraction.xes` of the 7 collaborative logs → `hobeck/<n>_uniqueInteraction_ocel.json`; `hobeck/<stem>.json` of the 13 Ethereum files → `hobeck/<stem>_ocel.json` | `results/e2_hobeck.{md,json}` |
| `e2b_roundtrip.py` | **E2b.** Round trip η_H(μ_U(ι_H(H))) ≅ H: every OCEL H of Hobeck et al. is read back into the unified representation by the reverse adapter ι_H (`reverse_hobeck.py`), mapped, exported, and compared with H as in E2; μ_U(ι_H(H)) must also satisfy the structural criteria | the 20 OCEL logs of Hobeck et al. (7 from `xescol2ocelchor`, 13 from `trace2ocelchor`) | `results/e2b_roundtrip.{md,json}` |
| `e3_consistency.py` | **E3.** Consistency per profile: P1.1–P1.7 and U1–U8 on every output; C0–C16 (`ocelchorvalidator`, unmodified) on every η_H export, cross-checked on Hobeck et al.'s references | the 48 outputs (9 scenarios × 3 profiles, 7 Hobeck XES, BPIC 2013, 13 Ethereum files) | `results/e3_consistency.{md,json}` |
| `e4_prediction.py` | **E4.** Example of choreography-level prediction: the ten distinct restated InfSys tasks with the InfSys pipeline (OCPA, `ChoreographyCase` as leading type, random forest, 5-fold CV grouped by case); no comparison. Adapter, tasks, and runner in [`../prediction/`](../prediction/README.md) | ChL profile of Healthcare (`healthcare_chl.sqlite`), participant Hospital, OB-M activity "Communicate the need to hospitalise" | `results/e4_prediction_healthcare.{md,json}` |

## Comparison rules

- **E1** compares sets read from the two SQLite files: events (id, type, time, attributes),
  objects (id, type, attributes), E2O, and O2O. α_C rebuilds the per-event messages that
  the core omits, so the view is compared as written, without projection. The only
  normalization is documented in `data/README.md`:
  the InfSys copy of Real4 drops a trailing non-breaking space in two activity names
  (200 events).
- **E2** compares the choreography information of Def. 2 of Hobeck et al. task by task:
  case, type, time, initiator and participants, messages (type, source, target, content),
  which tasks share a message, instances, and the scope tree. The normalizations are
  explicit and counted (docstring of `e2_hobeck.py`):
  - N1 identifiers;
  - N2 participant object types, up to a consistent renaming;
  - N3 absent content values (`output = "None"` in `trace2ocelchor`);
  - N4 event attributes, compared on the names both logs have.
- **E2b** uses the comparison of E2. ι_H turns each task into an exchange event and each
  message object into one logical message (the message id is the identifier, so shared
  messages stay shared); the request is the message whose source includes the
  initiator. Task roles and message endpoints, including those of the response, are kept
  as recorded, so a disagreement between them survives the round trip and U8 reports it.
  ι_H counts in its diagnostics only what it cannot represent or must choose (ambiguous
  request, request with several sources, ignored event or message; docstring of
  `reverse_hobeck.py`). ι_H lives here, not in the mapping, because the mapping reads the
  original formats. A reference passes only if the round trip is equivalent, the
  structural U criteria and P1.7 hold, ι_H reports no diagnostic, and μ_U reports no
  conflicting values; U4/U6/U8 are only reported.
- **E3** reads the criteria from the `_checks.json` files that the mapping writes, and
  runs the validator through its Python API (`read_ocel`, `build_index`, `validate_all`).
  It needs `ocelchorvalidator` from the ocelchor clone (`OCELCHOR`, or a sibling
  `../ocelchor`); without it, the script stops with a message instead of running.

## Running

```bash
export OCELCHOR=/path/to/ocelchor     # trace2ocelchor (mapping) and ocelchorvalidator (E3)
cd source/mapping && ../../.venv/bin/python map_all.py
cd ../experiments
../../.venv/bin/python e1_infsys.py
../../.venv/bin/python e2_hobeck.py
../../.venv/bin/python e2b_roundtrip.py
../../.venv/bin/python e3_consistency.py
../../.venv-predict/bin/python e4_prediction.py    # E4, prediction environment
```

`tests/test_roundtrip.py` checks that the comparison of E2 is not vacuous: perturbing one
message target, initiator, shared message, content value, or scope relation of a
reference log makes it fail. It also checks the diagnostics of ι_H and, on constructed
logs whose roles or response endpoints disagree with the messages (C1, C9, C10), that the
disagreement survives the round trip and U8 reports it
(`.venv/bin/python -m pytest source/experiments/tests`).

Each script prints its Markdown summary, writes it with the full JSON to `results/`, and
exits with 1 if its property fails.
