"""The unified mapping mu_U (rules UM1-UM12).

The implementation calls the InfSys mapping for the local, non-message part
of M1-M8 (rules UM1-UM7).  Its per-observation ``Message`` objects and their
relations are removed from the core; UM9-UM10 replace them with one logical
``Message`` per case-local correlation key and direct ``send``/``receive`` E2O
relations.  UM1 and UM2 also create the case and participant objects that only
exchange events record.
The untouched InfSys result remains attached to :class:`UnifiedResult` only as
the test oracle of the adapter alpha_C (`export_infsys.py`); no output or
criterion reads it.

| Rule | Adds |
|---|---|
| UM8 | one event per exchange event, with its activity, timestamp, and attributes; no `in_orchestration` or `in_participant` relation |
| UM9 | one logical `Message` per case and key; every unkeyed send, receive, request, or response gets its own singleton; `source` / `target` / `exchanged_in` O2O |
| UM10 | direct `send` / `receive` E2O from local message events to the logical `Message` |
| UM11 | the choreography task (the exchange event, or the send if no exchange event records the message), `request` / `response`, `initiator` / `participant`, and `in_choreography` E2O; `part_of` O2O from its `ChoreographyCase` to the `CollaborationCase` |
| UM12 | one `SubChoreographyCase` per recorded scope execution, `contained_by` (E2O) from each task to its innermost scope, `contains` (O2O) to directly nested scopes |

The rules represent the source data as recorded: a reused identifier gives one
logical message with several sends, while every unkeyed observation gets a
distinct singleton. A logical message holds one value per attribute: when its
carriers record different names or contents, the first value in event order is
kept and every value is reported in `stats["conflicting_values"]`.
"""

from __future__ import annotations

import copy
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from infsys import cx
from sources import ExchangeEvent, SourceLog, clean

COL_EID, COL_OID, COL_OID2 = cx.COL_EID, cx.COL_OID, cx.COL_OID2
COL_ACT, COL_TS, COL_TYPE, COL_Q = (cx.COL_ACTIVITY, cx.COL_TIMESTAMP,
                                    cx.COL_OTYPE, cx.COL_QUALIFIER)

# Object types added or reconstructed by UM9-UM12.
OT_MESSAGE = cx.OT_MESSAGE
OT_CHC = "ChoreographyCase"
OT_SUB = "SubChoreographyCase"
NEW_OBJECT_TYPES = (OT_MESSAGE, OT_CHC, OT_SUB)

# Qualifiers added by UM8-UM12.
Q_IN_CHOREOGRAPHY = "in_choreography"
Q_REQUEST = "request"
Q_RESPONSE = "response"
Q_INITIATOR = "initiator"
Q_PARTICIPANT = "participant"
Q_CONTAINED_BY = "contained_by"
Q_SOURCE = "source"
Q_TARGET = "target"
Q_EXCHANGED_IN = cx.Q_EXCHANGED_IN
Q_PART_OF = cx.Q_PART_OF
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


def message_id(case: str, key: str) -> str:
    return f"message::{_esc(case)}::{_esc(key)}"


def singleton_message_id(eid: str) -> str:
    return f"message::@{eid}"


def chc_id(case: str) -> str:
    return f"chc::{case}"


def sub_id(case: str, scope: str) -> str:
    return f"sub::{_esc(case)}::{_esc(scope)}"


@dataclass
class UnifiedResult:
    """The four OCEL tables of mu_U(L), before export, plus the InfSys result
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
    # Each name and content value carries the position (time, event id) of the
    # event that records it, so that the first one in event order is kept (UM9).
    names: List[Tuple[Tuple[pd.Timestamp, str], str]] = field(default_factory=list)
    content: Dict[str, List[Tuple[Tuple[pd.Timestamp, str], Any]]] = field(
        default_factory=dict)
    sends: List[str] = field(default_factory=list)      # event ids
    receives: List[str] = field(default_factory=list)   # event ids
    senders: List[str] = field(default_factory=list)    # all recorded assertions
    receivers: List[str] = field(default_factory=list)


def _utc(t: Any) -> pd.Timestamp:
    """An event time as a UTC timestamp, so that exchange and local times compare."""
    ts = pd.Timestamp(t)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def has_response(x: ExchangeEvent) -> bool:
    """Whether an exchange event records a return message (two-way task)."""
    return (x.response_key is not None or bool(x.response_name) or bool(x.response_content)
            or x.response_senders is not None or x.response_receivers is not None)


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
    """Apply mu_U (UM1-UM12) to a source log."""
    activities = [x.activity for x in src.exchange]
    if src.local is not None:
        activities += list(src.local[cx.ACTIVITY_KEY].unique())
    cx._check_activity_table_collisions(set(activities))

    # ---- M1-M8 local base; omit the per-observation message part --------
    local_msgs = []
    case_of_event: Dict[str, str] = {}
    if src.local is not None:
        res = cx.transform(src.local)
        # tau of the core extends that of M1-M8; a copy keeps res untouched.
        ptypes = copy.deepcopy(res.participant_types)
        ev_rows = res.events_df.to_dict("records")
        raw_objects = {r[COL_OID]: r for r in res.objects_df.to_dict("records")}
        raw_e2o = res.relations_df.to_dict("records")
        raw_o2o = res.o2o_df.to_dict("records")

        case_of_cc = {oid: r.get(A_CASE) for oid, r in raw_objects.items()
                      if r[COL_TYPE] == cx.OT_CC}
        for r in raw_e2o:
            if r[COL_Q] == cx.Q_IN_COLLABORATION:
                case_of_event[r[COL_EID]] = case_of_cc[r[COL_OID]]
        for r in sorted(ev_rows, key=lambda row: row[COL_EID]):
            elem = r.get("elemType")
            if elem not in (cx.ELEM_SEND, cx.ELEM_RECEIVE):
                continue
            name = next((clean(r.get(k)) for k in src.name_attrs
                         if clean(r.get(k)) is not None), None)
            local_msgs.append((
                r[COL_EID], r[COL_TS], case_of_event[r[COL_EID]], elem,
                clean(r.get(src.key_attr)), name,
                clean(r.get("participant")), clean(r.get("fromParticipant")),
                clean(r.get("toParticipant"))))

        legacy_messages = {oid for oid, row in raw_objects.items()
                           if row[COL_TYPE] == cx.OT_MESSAGE}
        ob_rows = {oid: row for oid, row in raw_objects.items()
                   if oid not in legacy_messages}
        e2o_rows = [r for r in raw_e2o if r[COL_OID] not in legacy_messages]
        o2o_rows = [r for r in raw_o2o
                    if r[COL_OID] not in legacy_messages
                    and r[COL_OID2] not in legacy_messages]
    else:
        res = None
        ptypes = cx.ParticipantTypes()
        ev_rows, ob_rows, e2o_rows, o2o_rows = [], {}, [], []
    base_objects = set(ob_rows)

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
        """The UM2 participant object of p, created here if M1-M8 did not create it."""
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

    # ---- UM8: exchange events -----------------------------------------------
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

    # ---- UM9: logical messages ---------------------------------------------
    msgs: Dict[str, _Msg] = {}

    def logical(case: str, key: Optional[str], carrier: str) -> _Msg:
        oid = message_id(case, key) if key is not None else singleton_message_id(carrier)
        if oid not in msgs:
            msgs[oid] = _Msg(oid, case, key)
        return msgs[oid]

    def add_content(m: _Msg, at: Tuple[pd.Timestamp, str], content: Dict[str, Any]) -> None:
        for k, v in content.items():
            if v is not None:              # an empty string is content; None is absent
                m.content.setdefault(k, []).append((at, v))

    task_of: Dict[str, List[Tuple[str, str]]] = {}   # eid -> request/response
    task_roles: Dict[str, Tuple[Tuple[str, ...], Tuple[str, ...]]] = {}
    local_task_initiators: Dict[str, Tuple[str, ...]] = {}
    exchange_recorded = set()   # logical messages recorded by an exchange event (UM11)
    for eid, x in exchange:
        at = (_utc(x.timestamp), eid)
        req = logical(x.case, x.key, eid)
        if x.name:
            req.names.append((at, x.name))
        add_content(req, at, x.content)
        if x.sender:
            req.senders.append(x.sender)
        req.receivers.extend(x.receivers)
        request_senders = (x.sender,) if x.sender else ()
        initiators = x.initiators if x.initiators is not None else request_senders
        participants = x.participants if x.participants is not None else x.receivers
        task_roles[eid] = (initiators, participants)
        exchange_recorded.add(req.oid)
        roles = [(Q_REQUEST, req.oid)]
        if has_response(x):
            resp = logical(x.case, x.response_key, eid + "::response")
            if x.response_name:
                resp.names.append((at, x.response_name))
            add_content(resp, at, x.response_content)
            exchange_recorded.add(resp.oid)
            response_senders = (x.receivers if x.response_senders is None
                                else x.response_senders)
            response_receivers = (request_senders if x.response_receivers is None
                                  else x.response_receivers)
            resp.senders.extend(response_senders)
            resp.receivers.extend(response_receivers)
            roles.append((Q_RESPONSE, resp.oid))
        task_of[eid] = roles

    for eid, ts, case, elem, key, name, executing, frm, to in local_msgs:
        m = logical(case, key, eid)
        if name:
            m.names.append(((_utc(ts), eid), name))
        (m.sends if elem == cx.ELEM_SEND else m.receives).append(eid)
        if elem == cx.ELEM_SEND:
            if executing:
                m.senders.append(executing)
            if to:
                m.receivers.append(to)
        else:
            if frm:
                m.senders.append(frm)
            if executing:
                m.receivers.append(executing)
        if elem == cx.ELEM_SEND and m.oid not in exchange_recorded:
            task_of[eid] = [(Q_REQUEST, m.oid)]  # UM11: the send is the task
            local_task_initiators[eid] = (executing,) if executing else ()

    # A send carrier gets every receiver asserted for its request message,
    # including participants known only through correlated receive events and
    # additional multicast receives.
    for eid, initiators in local_task_initiators.items():
        request_oid = task_of[eid][0][1]
        task_roles[eid] = (initiators, tuple(dict.fromkeys(msgs[request_oid].receivers)))

    # A logical message holds one value per attribute. When its carriers record
    # different names or contents (e.g., a reused identifier), the first value
    # in event order (time, then event id), across exchange and local events,
    # is kept and the conflict is reported with all values in that order, so
    # that nothing is lost silently (diagnostic of the mapping, not repaired).
    conflicts: List[Dict[str, Any]] = []
    for m in msgs.values():
        attrs = {A_CASE: m.case}
        if m.key is not None:
            attrs[A_KEY] = m.key
        values = dict(m.content)
        if m.names:
            values[A_NAME] = m.names
        for k, positioned in values.items():
            if k != A_NAME and (k in attrs or k in (COL_OID, COL_TYPE, A_NAME)):
                raise ValueError(f"message content attribute {k!r} is reserved")
            vs = [v for _, v in sorted(positioned, key=lambda p: p[0])]
            attrs[k] = vs[0]
            distinct = list(dict.fromkeys(str(v) for v in vs))
            if len(distinct) > 1:
                conflicts.append({"logical_message": m.oid, "attribute": k,
                                  "kept": str(vs[0]), "values": distinct})
        ensure(m.oid, OT_MESSAGE, attrs)

    # ---- UM10: direct message events and stored endpoints -------------------
    for m in msgs.values():
        for eid in m.sends:
            e2o(eid, m.oid, cx.Q_SEND)
        for eid in m.receives:
            e2o(eid, m.oid, cx.Q_RECEIVE)
        for p in dict.fromkeys(m.senders):
            o2o(m.oid, participant(p), Q_SOURCE)
        for p in dict.fromkeys(m.receivers):
            o2o(m.oid, participant(p), Q_TARGET)
        o2o(m.oid, collaboration_case(m.case), Q_EXCHANGED_IN)

    # ---- UM11: choreography tasks and instances ------------------------------
    case_of_task = {eid: case_of_event.get(eid) for eid in task_of}
    case_of_task.update({eid: x.case for eid, x in exchange})
    for case in dict.fromkeys(case_of_task[e] for e in sorted(task_of)):
        ensure(chc_id(case), OT_CHC, {A_CASE: case})
        o2o(chc_id(case), collaboration_case(case), Q_PART_OF)
    for eid in sorted(task_of):
        for q, moid in task_of[eid]:
            e2o(eid, moid, q)
        initiators, participants = task_roles[eid]
        for p in dict.fromkeys(initiators):
            e2o(eid, participant(p), Q_INITIATOR)
        for p in dict.fromkeys(participants):
            e2o(eid, participant(p), Q_PARTICIPANT)
        e2o(eid, chc_id(case_of_task[eid]), Q_IN_CHOREOGRAPHY)

    # ---- UM12: sub-choreographies --------------------------------------------
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
        raise ValueError(f"participant types {sorted(clash)} clash with UM9-UM12 types")
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
        "n_new_objects": len(set(ob_rows) - base_objects),
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
