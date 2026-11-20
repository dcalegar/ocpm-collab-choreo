# mapping/: unified mapping from the original log formats to OCEL 2.0

The unified mapping μ_U populates the unified representation of the paper (Section 3) from
the logs in `../../data/`, read in their original formats. No intermediate file format is
used: each reader builds an in-memory `SourceLog`, and μ_U maps it.

```
original file ──reader (sources.py)──▶ SourceLog ──μ_U (unified.py)──▶ core (OCEL 2.0 tables)
                                                         │
                                 criteria.py (P1.x, U1–U8) ◀──┤
                          export_infsys.py (α_C, InfSys) ◀──┤
                         export_hobeck.py (η_H, Hobeck et al.) ◀──┘
```

The core follows the BPMN concepts that both views share: one logical `Message` per
case-local correlation key, related directly to its send and receive events, and
choreography tasks related to their initiator and participants. Each prior
representation is produced by an adapter: α_C rebuilds the representation of InfSys
exactly (α_C(μ_U(L)) = μ(L_C), E1), and η_H exports that of Hobeck et al. (E2, E2b).

## Modules

| File | Content |
|---|---|
| `infsys.py` | Imports the InfSys mapping μ (M1–M8, P1.1–P1.7), `src/mapping/collab_xes_to_ocel.py` of `ocpm-collab-ppm`, unchanged. |
| `sources.py` | Readers of the original formats (table below). They rename and regroup, and never repair. |
| `unified.py` | μ_U: M1–M8 by calling the InfSys `transform()` on the local events, without its per-event messages, then M9–M13. |
| `index.py` | Lookups over any log in the representation: classification of events, the send and receive events of a logical message, its stored endpoints (`source`, `target`), and the stored roles of a task (`initiator`, `participant`). |
| `criteria.py` | P1.1–P1.6 (InfSys implementation, on α_C(μ_U(L))), P1.7 (on the exported E2O tables of the core and of α_C), and U1–U8. |
| `export_infsys.py` | α_C: the collaboration view in the representation of InfSys, rebuilt from the core tables only (one `msg::<event>` per send or receive, with the endpoints that the event records). |
| `export_hobeck.py` | η_H: the choreography view in the representation of Hobeck et al., as OCEL 2.0 JSON for `ocelchorvalidator`; roles and endpoints exported as stored. |
| `map_log.py` | Maps one log. |
| `map_all.py` | Maps every log in `data/` into `data/<dataset>/mapped/` (not versioned). |
| `tests/` | Synthetic cases the corpus does not exercise: two-way tasks with message events, conflicting values under a reused identifier, unkeyed singletons, explicit roles; α_C against its oracle `cx.transform`; each U criterion and P1.7 on built and tampered tables (`.venv/bin/python -m pytest source/mapping/tests`). |

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
  of a message then come from its correlated receives (M10).
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
| M10 | One logical `Message` per identifier and case (`message::<case>::<id>`, attributes `caseId`, `msgInstanceId`, `msgName`, content). Every unkeyed message that an event carries gets its own singleton (`message::@<event>`, and `message::@<event>::response` for the response of a two-way exchange event). `exchanged_in` (O2O) to the `CollaborationCase`; `source` / `target` (O2O) to every sender and receiver that a carrier records. If the carriers of one logical message record different names or contents (a reused identifier), the first value in event order is kept and all values are reported under `mapping_diagnostics` in `_checks.json`. |
| M11 | `send` / `receive` (E2O) from each send / receive to its logical `Message`. The per-event `Message` objects of M4 are not part of the core; α_C rebuilds them. |
| M12 | Task = the exchange event, or the send if no exchange event records the message, as request or as response. `request` / `response` (E2O) to the logical messages; `initiator` / `participant` (E2O) to the roles that the exchange event records, or else the sender and receivers of its request (for a send carrier: its executing participant and all receivers of its message); `in_choreography` (E2O) to `ChoreographyCase` (`chc::<case>`), which is `part_of` the `CollaborationCase`. Case and participant objects are created by the M1/M2 conventions when M1–M8 did not create them. |
| M13 | One `SubChoreographyCase` per scope execution (`sub::<case>::<scope>`), `contained_by` (E2O) from each task to its innermost scope, `contains` (O2O) to directly nested scopes. |

Participant objects created by M12 for Ethereum keep the role assigned by
`trace2ocelchor` in the attribute `role`, which η_H uses as their type.

## Export details (serialization only)

- **Outputs.** `map_log.py` writes the core (`<out>.jsonocel`, `<out>.sqlite`), the α_C
  view when the log has local events (`<out>_infsys.sqlite`), the η_H export
  (`<out>_hobeck.json`), and the criteria (`<out>_checks.json`).
- **Witness edges.** pm4py's exporters drop objects without an E2O relation. Each
  O2O-only object of the core (e.g., the `CollaborationCase` of a choreography-only log,
  outer scopes) gets one E2O edge that reuses the O2O qualifier, computed on the core
  tables only. α_C adds its own witnesses on its view, exactly as InfSys does. Criteria
  other than P1.7 are evaluated without them.
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
