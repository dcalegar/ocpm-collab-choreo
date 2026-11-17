"""The unified mapping mu+ (rules M1-M13).

M1-M8 are the InfSys rules, applied unchanged by calling the InfSys
implementation (`infsys.cx.transform`) on the local events of the log.
M9-M13 then add the exchange events, the logical messages, the choreography
view, and the hierarchy. They add events, objects, and relations, but never
change or remove those of M1-M8, so removing the additions gives back the
InfSys output (conservativity, checked in the experiments).

| Rule | Adds |
|---|---|
| M9 | one event per exchange event, with its activity, timestamp, and attributes; no `in_orchestration` or `in_participant` relation |
| M10 | one `ChoreographyMessage` per message identifier and case; a send or exchange event without identifier gets its own |
| M11 | `sent_as` / `received_as` (O2O) to the `Message` of each send / receive with that identifier; `from` / `to` (O2O) only for logical messages without message events |
| M12 | the choreography task (the exchange event, or the send if no exchange event records the message as request or response), `request` / `response` (E2O) to its logical messages, `in_choreography` (E2O) to one `ChoreographyCase` per case with tasks, `part_of` (O2O) to the `CollaborationCase`; case and participant objects when M1-M8 did not create them |
| M13 | one `SubChoreographyCase` per recorded scope execution, `contained_by` (E2O) from each task to its innermost scope, `contains` (O2O) to directly nested scopes |

The rules represent the source data as recorded: a reused identifier gives one
logical message with several sends; a receive without identifier links to no
logical message. A logical message holds one value per attribute: when its
carriers record different names or contents, the first value in event order is
kept and every value is reported in `stats["conflicting_values"]`.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from infsys import cx
from sources import ExchangeEvent, SourceLog, clean

COL_EID, COL_OID, COL_OID2 = cx.COL_EID, cx.COL_OID, cx.COL_OID2
COL_ACT, COL_TS, COL_TYPE, COL_Q = (cx.COL_ACTIVITY, cx.COL_TIMESTAMP,
                                    cx.COL_OTYPE, cx.COL_QUALIFIER)

# Object types added by M10-M13.
OT_CM = "ChoreographyMessage"
OT_CHC = "ChoreographyCase"
OT_SUB = "SubChoreographyCase"
NEW_OBJECT_TYPES = (OT_CM, OT_CHC, OT_SUB)

# Qualifiers added by M9-M13.
Q_IN_CHOREOGRAPHY = "in_choreography"
Q_REQUEST = "request"
Q_RESPONSE = "response"
Q_CONTAINED_BY = "contained_by"
Q_SENT_AS = "sent_as"
Q_RECEIVED_AS = "received_as"
Q_FROM, Q_TO, Q_PART_OF = cx.Q_FROM, cx.Q_TO, cx.Q_PART_OF
Q_CONTAINS = "contains"

# Object attributes of the new objects (bookkeeping).
A_CASE = "caseId"
A_KEY = "msgInstanceId"
A_NAME = "msgName"
A_SCOPE = "scopeId"
A_SCOPE_NAME = "name"
A_ROLE = "role"
BOOKKEEPING = (A_CASE, A_KEY, A_NAME, A_SCOPE)


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace(":", "\\:")


def exchange_event_id(case: str, idx: int, width: int) -> str:
    return f"x::{case}::{str(idx).zfill(width)}"


def cm_id(case: str, key: str) -> str:
    return f"cm::{_esc(case)}::{_esc(key)}"


def singleton_cm_id(eid: str) -> str:
    return f"cm::@{eid}"


def chc_id(case: str) -> str:
    return f"chc::{case}"


def sub_id(case: str, scope: str) -> str:
    return f"sub::{_esc(case)}::{_esc(scope)}"


@dataclass
class UnifiedResult:
    """The four OCEL tables of mu+(L), before export, plus the InfSys result
    of M1-M8 on the local events (None when the log has none)."""
    source: SourceLog
    events_df: pd.DataFrame
    objects_df: pd.DataFrame
    relations_df: pd.DataFrame
    o2o_df: pd.DataFrame
    infsys: Any
    participant_types: Any
    stats: Dict[str, Any] = field(default_factory=dict)


@dataclass
class _Msg:
    """A logical message under construction."""
    oid: str
    case: str
    key: Optional[str]
    names: List[str] = field(default_factory=list)
    content: Dict[str, List[Any]] = field(default_factory=dict)  # attribute -> values, in order
    sends: List[str] = field(default_factory=list)      # Message oids
    receives: List[str] = field(default_factory=list)   # Message oids
    senders: List[str] = field(default_factory=list)    # recorded by exchange events
    receivers: List[str] = field(default_factory=list)


def has_response(x: ExchangeEvent) -> bool:
    """Whether an exchange event records a return message (two-way task)."""
    return x.response_key is not None or bool(x.response_name) or bool(x.response_content)


def profile(src: SourceLog) -> Dict[str, bool]:
    """The dimensions of information that the log records."""
    local = src.local
    internal = messages = False
    keyed = True
    if local is not None and len(local):
        elems = [clean(v) or cx.ELEM_TASK for v in local[cx.ELEMTYPE_KEY]]
        internal = any(e == cx.ELEM_TASK for e in elems)
        messages = any(e in (cx.ELEM_SEND, cx.ELEM_RECEIVE) for e in elems)
        keys = local[src.key_attr] if src.key_attr in local.columns else [None] * len(local)
        keyed = all(clean(k) is not None for e, k in zip(elems, keys)
                    if e in (cx.ELEM_SEND, cx.ELEM_RECEIVE))
    exchange = bool(src.exchange)
    keyed = keyed and all(x.key is not None and (x.response_key is not None or not has_response(x))
                          for x in src.exchange)
    return {
        "internal_tasks": internal,
        "message_events": messages,
        "exchange_events": exchange,
        "correlation": (messages or exchange) and keyed,
        "hierarchy": any(x.scope_path for x in src.exchange),
    }


def map_log(src: SourceLog) -> UnifiedResult:
    """Apply mu+ (M1-M13) to a source log."""
    activities = [x.activity for x in src.exchange]
    if src.local is not None:
        activities += list(src.local[cx.ACTIVITY_KEY].unique())
    cx._check_activity_table_collisions(set(activities))

    # ---- M1-M8: the InfSys mapping, unchanged ---------------------------
    if src.local is not None:
        res = cx.transform(src.local)
        ptypes = res.participant_types
        ev_rows = res.events_df.to_dict("records")
        ob_rows = {r[COL_OID]: r for r in res.objects_df.to_dict("records")}
        e2o_rows = res.relations_df.to_dict("records")
        o2o_rows = res.o2o_df.to_dict("records")
    else:
        res = None
        ptypes = cx.ParticipantTypes()
        ev_rows, ob_rows, e2o_rows, o2o_rows = [], {}, [], []
    infsys_objects = set(ob_rows)

    def ensure(oid: str, otype: str, attrs: Dict[str, Any]) -> None:
        if oid not in ob_rows:
            row = {COL_OID: oid, COL_TYPE: otype}
            row.update(attrs)
            ob_rows[oid] = row

    def otype(oid: str) -> str:
        return ob_rows[oid][COL_TYPE]

    def e2o(eid: str, oid: str, q: str) -> None:
        e2o_rows.append({COL_EID: eid, COL_OID: oid, COL_TYPE: otype(oid), COL_Q: q})

    def o2o(a: str, b: str, q: str) -> None:
        o2o_rows.append({COL_OID: a, COL_OID2: b, COL_Q: q})

    def participant(p: str) -> str:
        """The M2 participant object of p, created if M1-M8 did not."""
        oid = cx._participant_id(p)
        if oid not in ob_rows:
            attrs = {"name": p}
            if p in src.participant_roles:
                attrs[A_ROLE] = src.participant_roles[p]
            ensure(oid, ptypes.register(p), attrs)
        return oid

    def collaboration_case(case: str) -> str:
        oid = cx._cc_id(case)
        ensure(oid, cx.OT_CC, {"caseId": case})   # M1 convention
        return oid

    # ---- local message events of M1-M8 ------------------------------------
    case_of_event: Dict[str, str] = {}
    case_of_cc = {oid: r.get("caseId") for oid, r in ob_rows.items()
                  if r[COL_TYPE] == cx.OT_CC}
    for r in e2o_rows:
        if r[COL_Q] == cx.Q_IN_COLLABORATION:
            case_of_event[r[COL_EID]] = case_of_cc[r[COL_OID]]
    message_of_event = {r[COL_EID]: r[COL_OID] for r in e2o_rows
                        if r[COL_Q] in (cx.Q_SEND, cx.Q_RECEIVE)}
    local_msgs = []   # (eid, case, elem, key, name, message oid), in id order
    for r in sorted(ev_rows, key=lambda r: r[COL_EID]):
        if r.get("elemType") in (cx.ELEM_SEND, cx.ELEM_RECEIVE):
            name = next((clean(r.get(k)) for k in src.name_attrs
                         if clean(r.get(k)) is not None), None)
            local_msgs.append((r[COL_EID], case_of_event[r[COL_EID]], r["elemType"],
                               clean(r.get(src.key_attr)), name,
                               message_of_event[r[COL_EID]]))

    # ---- M9: exchange events -----------------------------------------------
    by_case: Dict[str, List[ExchangeEvent]] = defaultdict(list)
    for x in src.exchange:
        by_case[x.case].append(x)
    exchange: List[Tuple[str, ExchangeEvent]] = []
    for case, xs in by_case.items():
        xs = sorted(xs, key=lambda x: (pd.Timestamp(x.timestamp), x.order))
        width = max(1, len(str(len(xs) - 1)))
        for idx, x in enumerate(xs):
            eid = exchange_event_id(case, idx, width)
            row = {COL_EID: eid, COL_ACT: x.activity, COL_TS: x.timestamp}
            for k, v in x.attributes.items():
                if k in (COL_EID, COL_ACT, COL_TS):
                    raise ValueError(f"exchange event attribute {k!r} is reserved")
                row[k] = v
            ev_rows.append(row)
            exchange.append((eid, x))

    # ---- M10: logical messages ---------------------------------------------
    msgs: Dict[str, _Msg] = {}

    def logical(case: str, key: Optional[str], carrier: str) -> _Msg:
        oid = cm_id(case, key) if key is not None else singleton_cm_id(carrier)
        if oid not in msgs:
            msgs[oid] = _Msg(oid, case, key)
        return msgs[oid]

    def add_content(m: _Msg, content: Dict[str, Any]) -> None:
        for k, v in content.items():
            if v is not None:              # an empty string is content; None is absent
                m.content.setdefault(k, []).append(v)

    task_of: Dict[str, List[Tuple[str, str, Optional[str]]]] = {}   # eid -> request/response
    exchange_recorded = set()   # logical messages recorded by an exchange event (M12)
    for eid, x in exchange:
        req = logical(x.case, x.key, eid)
        if x.name:
            req.names.append(x.name)
        add_content(req, x.content)
        if x.sender:
            req.senders.append(x.sender)
        req.receivers.extend(x.receivers)
        exchange_recorded.add(req.oid)
        roles = [(Q_REQUEST, req.oid)]
        if has_response(x):
            resp = logical(x.case, x.response_key, eid + "::response")
            if x.response_name:
                resp.names.append(x.response_name)
            add_content(resp, x.response_content)
            exchange_recorded.add(resp.oid)
            if x.sender:                       # a response reverses the request
                resp.receivers.append(x.sender)
            resp.senders.extend(x.receivers)
            roles.append((Q_RESPONSE, resp.oid))
        task_of[eid] = roles

    for eid, case, elem, key, name, moid in local_msgs:
        if key is None and elem == cx.ELEM_RECEIVE:
            continue                             # nothing to correlate with
        m = logical(case, key, eid)
        if name:
            m.names.append(name)
        (m.sends if elem == cx.ELEM_SEND else m.receives).append(moid)
        if elem == cx.ELEM_SEND and m.oid not in exchange_recorded:
            task_of[eid] = [(Q_REQUEST, m.oid)]  # M12: the send is the task

    # A logical message holds one value per attribute. When its carriers record
    # different names or contents (e.g., a reused identifier), the first value
    # in event order is kept and the conflict is reported with all values, so
    # that nothing is lost silently (diagnostic of the mapping, not repaired).
    conflicts: List[Dict[str, Any]] = []
    for m in msgs.values():
        attrs = {A_CASE: m.case}
        if m.key is not None:
            attrs[A_KEY] = m.key
        values = dict(m.content)
        if m.names:
            values[A_NAME] = m.names
        for k, vs in values.items():
            if k != A_NAME and (k in attrs or k in (COL_OID, COL_TYPE, A_NAME)):
                raise ValueError(f"message content attribute {k!r} is reserved")
            attrs[k] = vs[0]
            distinct = list(dict.fromkeys(str(v) for v in vs))
            if len(distinct) > 1:
                conflicts.append({"logical_message": m.oid, "attribute": k,
                                  "kept": str(vs[0]), "values": distinct})
        ensure(m.oid, OT_CM, attrs)

    # ---- M11: links to message events; endpoints only without them ---------
    for m in msgs.values():
        for moid in m.sends:
            o2o(m.oid, moid, Q_SENT_AS)
        for moid in m.receives:
            o2o(m.oid, moid, Q_RECEIVED_AS)
        if not m.sends and not m.receives:
            for p in dict.fromkeys(m.senders):
                o2o(m.oid, participant(p), Q_FROM)
            for p in dict.fromkeys(m.receivers):
                o2o(m.oid, participant(p), Q_TO)

    # ---- M12: choreography tasks and instances ------------------------------
    case_of_task = {eid: case_of_event.get(eid) for eid in task_of}
    case_of_task.update({eid: x.case for eid, x in exchange})
    for case in dict.fromkeys(case_of_task[e] for e in sorted(task_of)):
        ensure(chc_id(case), OT_CHC, {A_CASE: case})
        o2o(chc_id(case), collaboration_case(case), Q_PART_OF)
    for eid in sorted(task_of):
        for q, moid in task_of[eid]:
            e2o(eid, moid, q)
        e2o(eid, chc_id(case_of_task[eid]), Q_IN_CHOREOGRAPHY)

    # ---- M13: sub-choreographies --------------------------------------------
    for eid, x in exchange:
        parent = None
        for scope in x.scope_path:
            soid = sub_id(x.case, scope.scope_id)
            attrs = {A_CASE: x.case, A_SCOPE: scope.scope_id}
            if scope.name:
                attrs[A_SCOPE_NAME] = scope.name
            ensure(soid, OT_SUB, attrs)
            if parent is not None:
                o2o(parent, soid, Q_CONTAINS)
            parent = soid
        if parent is not None:
            e2o(eid, parent, Q_CONTAINED_BY)

    # ---- assemble ------------------------------------------------------------
    clash = {t for t in ptypes.types if t in NEW_OBJECT_TYPES
             or cx._pm4py_table_name(t) in {cx._pm4py_table_name(n) for n in NEW_OBJECT_TYPES}}
    if clash:
        raise ValueError(f"participant types {sorted(clash)} clash with M10-M13 types")
    events_df = pd.DataFrame(ev_rows)
    if not events_df.empty:
        events_df[COL_TS] = pd.to_datetime(events_df[COL_TS], utc=True)
        front = [COL_EID, COL_ACT, COL_TS]
        events_df = events_df[front + [c for c in events_df.columns if c not in front]]
    objects_df = pd.DataFrame(list(ob_rows.values()))
    o2o_df = pd.DataFrame(o2o_rows, columns=[COL_OID, COL_OID2, COL_Q]).drop_duplicates()
    relations_df = pd.DataFrame(e2o_rows, columns=[COL_EID, COL_OID, COL_TYPE, COL_Q])

    stats = {
        "profile": profile(src),
        "n_events": len(events_df),
        "n_local_events": len(res.events_df) if res is not None else 0,
        "n_exchange_events": len(exchange),
        "n_tasks": len(task_of),
        "n_two_way_tasks": sum(len(v) > 1 for v in task_of.values()),
        "n_objects": len(objects_df),
        "n_objects_by_type": objects_df[COL_TYPE].value_counts().to_dict(),
        "n_new_objects": len(set(ob_rows) - infsys_objects),
        "n_e2o": len(relations_df),
        "n_o2o": len(o2o_df),
        "n_logical_messages": len(msgs),
        "n_singleton_logical_messages": sum(m.key is None for m in msgs.values()),
        "n_logical_messages_with_conflicting_values": len({c["logical_message"] for c in conflicts}),
        "conflicting_values": conflicts,
        "n_choreography_cases": int((objects_df[COL_TYPE] == OT_CHC).sum()) if len(objects_df) else 0,
    }
    return UnifiedResult(src, events_df, objects_df, relations_df, o2o_df, res,
                         ptypes, stats)
