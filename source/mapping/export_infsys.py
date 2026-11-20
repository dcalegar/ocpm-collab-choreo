"""Export adapter alpha_C: the collaboration view of the neutral core in the
representation of InfSys (`CalegariDPR26`, rules M1-M8).

It reads only the four OCEL tables of the core, never the InfSys result kept
in `UnifiedResult.infsys`, and returns them as a `cx.TransformResult`, so that
the InfSys checks and exporters apply unchanged.

| InfSys | Core | Derivation |
|---|---|---|
| events | local events (`in_collaboration`) | selection; attributes unchanged |
| `CollaborationCase`, `OrchestrationCase`, participants | the same objects | selection (reached from a local event, or related to nothing) |
| `in_collaboration`, `in_orchestration`, `in_participant` | the same E2O | selection |
| `part_of`, `for_participant` of an `OrchestrationCase` | the same O2O | selection |
| `msg::<event>` and its `send` / `receive` E2O | `send` / `receive` E2O to the logical `Message` | one object per message event (M4) |
| `sender` / `receiver`, `from` / `to` of `msg::<event>` | `fromParticipant` / `toParticipant` of the event (M8) | per observation |
| `exchanged_in` of `msg::<event>` | `in_collaboration` of the event | per observation |

Exchange events, logical messages, choreography and sub-choreography cases,
and the relations added by M10-M13 (`source`, `target`, `request`, `response`,
`initiator`, `participant`, `in_choreography`, `contained_by`, `contains`) are
removed. The endpoints of an observation are read from its own event, not
from the aggregated `source` / `target` of its logical message, which may
join several observations. No data is normalized: the trailing non-breaking
space of two Real4 activity names is handled by E1 only.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

import pandas as pd

from infsys import cx
import unified as u

COL_EID, COL_OID, COL_OID2 = cx.COL_EID, cx.COL_OID, cx.COL_OID2
COL_TYPE, COL_Q = cx.COL_OTYPE, cx.COL_QUALIFIER

# The InfSys vocabulary that survives the selection.
LOCAL_E2O = (cx.Q_IN_COLLABORATION, cx.Q_IN_ORCHESTRATION, cx.Q_IN_PARTICIPANT)
MESSAGE_E2O = (cx.Q_SEND, cx.Q_RECEIVE)
ORCHESTRATION_O2O = (cx.Q_PART_OF, cx.Q_FOR_PARTICIPANT)
# M8 event attributes holding the endpoints of a message observation.
FROM_ATTR, TO_ATTR = "fromParticipant", "toParticipant"


def _clean(v: Any) -> Optional[str]:
    if v is None or (not isinstance(v, (list, tuple, dict)) and pd.isna(v)):
        return None
    return v


def _records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    return df.to_dict("records") if df is not None and len(df) else []


def _drop_empty_columns(df: pd.DataFrame, keep: tuple) -> pd.DataFrame:
    """Drop the attribute columns that only removed rows filled."""
    if df.empty:
        return df
    empty = [c for c in df.columns if c not in keep and df[c].isna().all()]
    return df.drop(columns=empty).infer_objects().reset_index(drop=True)


def export(events_df: pd.DataFrame, objects_df: pd.DataFrame,
           relations_df: pd.DataFrame, o2o_df: pd.DataFrame) -> "cx.TransformResult":
    """alpha_C over the four tables of a log in the neutral representation."""
    e2o = _records(relations_df)
    o2o = _records(o2o_df)
    objects = {r[COL_OID]: r for r in _records(objects_df)}

    # ---- events: the local ones (M5), in core order -------------------------
    case_of = {r[COL_EID]: r[COL_OID] for r in e2o if r[COL_Q] == cx.Q_IN_COLLABORATION}
    events = events_df[events_df[COL_EID].isin(case_of)] if len(events_df) else events_df
    event_rows = {r[COL_EID]: r for r in _records(events)}

    # ---- message observations (M4): one per send / receive event ------------
    observations = [(r[COL_EID], r[COL_Q]) for r in e2o
                    if r[COL_EID] in case_of and r[COL_Q] in MESSAGE_E2O
                    and objects.get(r[COL_OID], {}).get(COL_TYPE) == u.OT_MESSAGE]
    if len({eid for eid, _ in observations}) != len(observations):
        raise ValueError("a local event has more than one send/receive relation")

    # ---- retained E2O and the objects they reach ------------------------------
    rel_rows = [r for r in e2o if r[COL_EID] in case_of and r[COL_Q] in LOCAL_E2O]
    keep: Set[str] = {r[COL_OID] for r in rel_rows}
    o2o_rows = [r for r in o2o if r[COL_OID] in keep and r[COL_Q] in ORCHESTRATION_O2O
                and objects[r[COL_OID]][COL_TYPE] == cx.OT_OC]
    keep |= {r[COL_OID2] for r in o2o_rows}
    # An object of the core without relations comes from M1-M8 (every object
    # that M10-M13 add is related), e.g. a participant recorded only as the
    # endpoint of a task event, which M8 does not preserve.
    related = ({r[COL_OID] for r in e2o} | {r[COL_OID] for r in o2o}
               | {r[COL_OID2] for r in o2o})
    keep |= {oid for oid, r in objects.items()
             if oid not in related and r[COL_TYPE] != u.OT_MESSAGE}

    msg_rows: List[Dict[str, Any]] = []
    for eid, q in observations:
        ev = event_rows[eid]
        moid = cx._message_id(eid)
        sender, receiver = _clean(ev.get(FROM_ATTR)), _clean(ev.get(TO_ATTR))
        msg_rows.append({COL_OID: moid, COL_TYPE: cx.OT_MESSAGE,
                         "sender": sender, "receiver": receiver})
        rel_rows.append({COL_EID: eid, COL_OID: moid, COL_TYPE: cx.OT_MESSAGE, COL_Q: q})
        for p, pq in ((sender, cx.Q_FROM), (receiver, cx.Q_TO)):
            if p is not None:
                poid = cx._participant_id(p)
                if poid not in objects:
                    raise ValueError(f"endpoint {p!r} of {eid} has no participant object")
                o2o_rows.append({COL_OID: moid, COL_OID2: poid, COL_Q: pq})
                keep.add(poid)
        o2o_rows.append({COL_OID: moid, COL_OID2: case_of[eid], COL_Q: cx.Q_EXCHANGED_IN})

    # ---- objects, and tau restricted to the retained participants (M2) ------
    ob_rows = [r for oid, r in objects.items() if oid in keep] + msg_rows
    structural = (cx.OT_CC, cx.OT_OC, cx.OT_MESSAGE)
    ptypes = cx.ParticipantTypes()
    for r in ob_rows:
        if r[COL_TYPE] not in structural:
            got = ptypes.register(r["name"])
            if got != r[COL_TYPE]:
                raise ValueError(f"participant {r['name']!r} has type {r[COL_TYPE]!r}, "
                                 f"but tau gives {got!r}")

    ev_df = _drop_empty_columns(events.copy(), (COL_EID, cx.COL_ACTIVITY, cx.COL_TIMESTAMP))
    ob_df = _drop_empty_columns(pd.DataFrame(ob_rows), (COL_OID, COL_TYPE))
    rel_df = pd.DataFrame(rel_rows, columns=[COL_EID, COL_OID, COL_TYPE, COL_Q])
    o2o_df_out = pd.DataFrame(o2o_rows, columns=[COL_OID, COL_OID2, COL_Q])

    stats = {
        "n_events": len(ev_df),
        "n_objects": len(ob_df),
        "n_objects_by_type": ob_df[COL_TYPE].value_counts().to_dict() if len(ob_df) else {},
        "n_e2o": len(rel_df),
        "n_o2o": len(o2o_df_out),
        "n_messages": len(msg_rows),
        "n_messages_missing_sender": sum(r["sender"] is None for r in msg_rows),
        "n_messages_missing_receiver": sum(r["receiver"] is None for r in msg_rows),
        "n_cases": len(set(case_of.values())),
        "n_participant_types": len(ptypes),
    }
    return cx.TransformResult(ev_df, ob_df, rel_df, o2o_df_out, stats, ptypes)


def of(res: "u.UnifiedResult") -> "cx.TransformResult":
    """alpha_C(mu_U(L)), from the core tables of a mapping result."""
    return export(res.events_df, res.objects_df, res.relations_df, res.o2o_df)


def write_sqlite(view: "cx.TransformResult", path: str) -> pd.DataFrame:
    """Persist the view as InfSys does (`cx.convert`): its own export
    witnesses, computed on the view, then the pm4py SQLite exporter. Returns
    the E2O table handed to the exporter."""
    rel = cx._add_export_reachability_witnesses(view.objects_df, view.relations_df,
                                                view.o2o_df)
    cx.write_ocel2_sqlite(cx.build_ocel_object(view.events_df, view.objects_df, rel,
                                               view.o2o_df), path)
    return rel
