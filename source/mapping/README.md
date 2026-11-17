# mapping/: unified mapping from the original log formats to OCEL 2.0

The unified mapping μ⁺ populates the unified representation of the paper (Section 3) from
the logs in `../../data/`, read in their original formats. No intermediate file format is
used: each reader builds an in-memory `SourceLog`, and μ⁺ maps it.

```
original file ──reader (sources.py)──▶ SourceLog ──μ⁺ (unified.py)──▶ OCEL 2.0 tables
                                                         │
                                 criteria.py (P1.x, U1–U7) ◀──┤
                         export_hobeck.py (η_H, Hobeck et al.) ◀──┘
```

## Modules

| File | Content |
|---|---|
| `infsys.py` | Imports the InfSys mapping μ (M1–M8, P1.1–P1.7), `src/mapping/collab_xes_to_ocel.py` of `ocpm-collab-ppm`, unchanged. |
| `sources.py` | Readers of the original formats (table below). They rename and regroup, and never repair. |
| `unified.py` | μ⁺: M1–M8 by calling the InfSys `transform()` on the local events, then M9–M13. |
| `index.py` | Lookups over any log in the representation: classification of events, derived sender and receivers of a logical message. |
| `criteria.py` | P1.1–P1.6 (InfSys implementation, on the local part), P1.7 (on the exported E2O table), and U1–U7. |
| `export_hobeck.py` | η_H: the choreography view in the representation of Hobeck et al., as OCEL 2.0 JSON for `ocelchorvalidator`. |
| `map_log.py` | Maps one log. |
| `map_all.py` | Maps every log in `data/` into `data/<dataset>/mapped/` (not versioned). |
| `tests/` | Synthetic cases the corpus does not exercise: two-way tasks with message events, conflicting values under a reused identifier, correlation of return messages (`.venv/bin/python -m pytest source/mapping/tests`). |

The mapping only transforms and checks its own output. The comparison with the reference
logs of InfSys and Hobeck et al. belongs to `../experiments/`.

## Readers

| Reader | Original file | Local events | Exchange events |
|---|---|---|---|
| `read_cl` | Peña et al.'s CL (`pena/*_collab.xes`); InfSys's BPIC 2013 CL (identifier `msgId`) | yes | — |
| `read_chl` | Peña et al.'s ChL (`pena/*_chor.xes`) | — | yes |
| `combine` | a CL and its ChL (complete profile) | from the CL | from the ChL |
| `read_hobeck_xes` | Hobeck et al.'s XES input (`hobeck/*_uniqueInteraction.xes`) | yes | — |
| `read_eth_traces` | Ethereum traces (`hobeck/<stem>.json`) | — | yes, with return messages and scopes |

- **CL and BPIC 2013** are read with the InfSys reader (`read_collaborative_xes`, which
  also corrects pm4py's UTC-offset parsing), exactly as InfSys reads them. One addition
  applies to every XES reader: the InfSys reader infers one timestamp format from the
  first value and sets the values written with another precision to NaT (one event in
  Hobeck et al.'s Real3 XES). `read_xes` parses the raw timestamps again with
  `format="ISO8601"` and checks that they agree with the InfSys reader wherever it parsed
  them. On the CLs nothing changes.
- **Hobeck et al.'s XES** has no `collab:*` attributes. As `xescol2ocelchor` does, the
  reader takes the executing participant from `org:group` and the kind of event from
  `msgType` (`send` → `SendTask`, `receive` → `ReceiveTask`, absent → `task`). The
  counterparty of a send or receive is not recorded, so it stays undefined. The receivers
  of a message then come from its correlated receives (M11).
- **Ethereum traces** are read and interpreted with the code of `trace2ocelchor`,
  imported unmodified: its parser (DELEGATECALL rewrite, address normalization) and its
  naming helpers (event types, participant roles, message names and content, timestamps).
  Only the walk from the call tree to exchange events is redone in `read_eth_traces`,
  with the structure of `trace2ocelchor`:
  - each transaction is a case;
  - the root call is a one-way task;
  - a call without nested calls is a two-way task;
  - a call with nested calls is a request task and a response task, which open and close
    its scope.

  This way the output can be compared with that of `trace2ocelchor` on the same input.

## Rules M9–M13 (summary)

| Rule | Adds |
|---|---|
| M9 | One event per exchange event (id `x::<case>::<i>`), with its activity, timestamp, and attributes; `collab:*` keys renamed as in M8. No `in_collaboration`, `in_orchestration`, or `in_participant`. |
| M10 | One `ChoreographyMessage` per identifier and case (`cm::<case>::<id>`, attributes `caseId`, `msgInstanceId`, `msgName`, content). A send or exchange event without identifier gets its own (`cm::@<event>`); a receive without identifier links to none. If the carriers of one logical message record different names or contents (a reused identifier), the first value in event order is kept and all values are reported under `mapping_diagnostics` in `_checks.json`. |
| M11 | `sent_as` / `received_as` (O2O) to the `Message` of each send / receive with the identifier. `from` / `to` (O2O) only when the logical message has no message events. |
| M12 | Task = the exchange event, or the send if no exchange event records the message, as request or as response. `request` / `response` (E2O) to the logical messages; `in_choreography` (E2O) to `ChoreographyCase` (`chc::<case>`), which is `part_of` the `CollaborationCase`. Case and participant objects are created by the M1/M2 conventions when M1–M8 did not create them. |
| M13 | One `SubChoreographyCase` per scope execution (`sub::<case>::<scope>`), `contained_by` (E2O) from each task to its innermost scope, `contains` (O2O) to directly nested scopes. |

Participant objects created by M12 for Ethereum keep the role assigned by
`trace2ocelchor` in the attribute `role`, which η_H uses as their type.

## Export details (serialization only)

- **Witness edges.** pm4py's exporters drop objects without an E2O relation. The InfSys
  witnesses are added as in InfSys; then each remaining O2O-only object (e.g., the
  `CollaborationCase` of a choreography-only log, outer scopes, logical messages that are
  only received) gets one E2O edge that reuses the O2O qualifier. Criteria other than P1.7
  are evaluated without them.
- **Unnamed attributes.** The pm4py SQLite exporter rejects empty column names, which
  unnamed ABI parameters of 8 Ethereum logs produce (already so in Hobeck et al.'s logs).
  In the pm4py exports only, an empty attribute name becomes `unnamed`; `_hobeck.json`
  keeps it empty.
- **Sub-second times.** pm4py's JSON exporter truncates event times to seconds; the
  `.jsonocel` times are restored from the event table, with one precision per log. The
  `.sqlite` keeps them natively.

## Setup and use

```bash
python3.10 -m venv .venv
.venv/bin/pip install -r source/requirements.txt
.venv/bin/pip install --no-deps -e ../ocpm-collab-ppm   # InfSys, commit 98d5e697
export OCELCHOR=/path/to/ocelchor                       # only for the Ethereum logs
cd source/mapping
../../.venv/bin/python map_log.py --cl CL.xes [--chl ChL.xes] out/base
../../.venv/bin/python map_log.py --hobeck-xes X.xes out/base
../../.venv/bin/python map_log.py --eth traces.json out/base
../../.venv/bin/python map_all.py
```

`map_log.py` exits with 1 if a structural criterion fails.
