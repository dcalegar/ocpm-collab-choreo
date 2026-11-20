"""Consistency criteria of the unified representation.

- P1.1-P1.6: the InfSys criteria, evaluated by the InfSys implementation on
  alpha_C(mu_U(L)), the collaboration view rebuilt from the core
  (`export_infsys.py`); P1.7 (export reachability) on the E2O table handed to
  the exporters, for the serialized core and for alpha_C(mu_U(L)).
- U1-U8: the criteria for what M9-M13 add (paper, Section 3.3). They read the
  log through `index.Index`, so they apply to any log in the representation.

Structural criteria (U1-U3, U5, U7) must hold; a violation is an
implementation error. Diagnostic criteria (U4, U6, U8) report the quality of
the source data and the agreement between its claims as counts, and never
fail. C0-C16 of Hobeck et al. are checked by their validator on the exported
view (`export_hobeck.py`).
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from infsys import cx
from index import Index
import unified as u

STRUCTURAL, DIAGNOSTIC = "structural", "diagnostic"
MESSAGE_ROLES = (cx.Q_SEND, cx.Q_RECEIVE, u.Q_REQUEST, u.Q_RESPONSE)
EXPECTED_LINK = {cx.ELEM_SEND: cx.Q_SEND, cx.ELEM_RECEIVE: cx.Q_RECEIVE}
FROM_ATTR, TO_ATTR = "fromParticipant", "toParticipant"   # M8 / M9 event attributes
EXECUTING_ATTR = "participant"                            # M8: who executes a local event


@dataclass
class Criterion:
    name: str
    kind: str
    ok: bool
    counts: Dict[str, Any] = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)


def _crit(name, kind, counts, examples, violations=()):
    ok = kind == DIAGNOSTIC or not any(counts[k] for k in violations)
    return Criterion(name, kind, ok, counts, examples[:5])


def _clean(v: Any) -> Optional[str]:
    if v is None or v != v:
        return None
    s = str(v).strip()
    return s or None


def _attr(ix: Index, e: str, k: Optional[str]) -> Optional[str]:
    return _clean(ix.events[e].get(k)) if k else None


def _carriers(ix: Index, m: str) -> set:
    return {e for q in MESSAGE_ROLES for e in ix.events_of(m, q)}


def u1_instance(ix: Index) -> Criterion:
    bad_inst, bad_case, bad_part, other_parent, empty = [], [], [], [], []
    for t in ix.tasks():
        chcs = ix.targets(t, u.Q_IN_CHOREOGRAPHY)
        if len(chcs) != 1 or ix.objects[chcs[0]][cx.COL_OTYPE] != u.OT_CHC:
            bad_inst.append(t)
            continue
        cases = {ix.objects[m].get(u.A_CASE) for m in ix.targets(t, u.Q_REQUEST)}
        if cases != {ix.objects[chcs[0]].get(u.A_CASE)}:
            bad_case.append(t)
    for c in ix.of_type(u.OT_CHC):
        parents = ix.o2o_targets(c, u.Q_PART_OF)
        if len(parents) != 1 or ix.objects[parents[0]][cx.COL_OTYPE] != cx.OT_CC:
            bad_part.append(c)
        elif ix.objects[parents[0]].get(u.A_CASE) != ix.objects[c].get(u.A_CASE):
            other_parent.append(c)      # M12: part of the CollaborationCase of its case
        if not ix.events_of(c, u.Q_IN_CHOREOGRAPHY):
            empty.append(c)
    counts = {"tasks": len(ix.tasks()), "choreography_cases": len(ix.of_type(u.OT_CHC)),
              "tasks_without_exactly_one_case": len(bad_inst),
              "tasks_in_another_case_than_their_request": len(bad_case),
              "cases_without_exactly_one_part_of": len(bad_part),
              "cases_part_of_another_case": len(other_parent),
              "cases_without_tasks": len(empty)}
    return _crit("U1 Instance", STRUCTURAL, counts,
                 bad_inst + bad_case + bad_part + other_parent + empty,
                 [k for k in counts if k not in ("tasks", "choreography_cases")])


def u2_task(ix: Index) -> Criterion:
    """Each mapped exchange has one task carrier: its exchange event when
    present, otherwise its send, whose request is its own message."""
    tasks = set(ix.tasks())
    exchange = ix.exchange_events()
    recorded = {m for x in exchange for q in (u.Q_REQUEST, u.Q_RESPONSE)
                for m in ix.targets(x, q)}
    x_not_task = [x for x in exchange if x not in tasks]
    send_wrong, other = [], []
    for e in ix.events:
        if not ix.is_local(e):
            continue
        sent = ix.targets(e, cx.Q_SEND)
        if sent:
            should = not (set(sent) & recorded)
            if should != (e in tasks) or (e in tasks and ix.targets(e, u.Q_REQUEST) != sent):
                send_wrong.append(e)
        elif e in tasks:
            other.append(e)
    counts = {"tasks": len(tasks), "exchange_events": len(exchange),
              "exchange_events_not_tasks": len(x_not_task),
              "sends_with_wrong_task_status": len(send_wrong),
              "other_local_events_as_tasks": len(other)}
    return _crit("U2 Task", STRUCTURAL, counts, x_not_task + send_wrong + other,
                 ["exchange_events_not_tasks", "sends_with_wrong_task_status",
                  "other_local_events_as_tasks"])


def u3_message_identity(ix: Index, key_attr: Optional[str]) -> Criterion:
    """Every correlation key of a case gives one logical message, exchanged in
    its CollaborationCase; every send or receive relates to exactly one
    logical message of its own case, the one of its key, or its own singleton
    when it has none."""
    msgs = ix.messages()
    keys = Counter((ix.objects[m].get(u.A_CASE), _clean(ix.objects[m].get(u.A_KEY)))
                   for m in msgs if _clean(ix.objects[m].get(u.A_KEY)) is not None)
    dup = [f"{k}" for k, n in keys.items() if n > 1]
    cc_of: Dict[str, Optional[str]] = {}
    bad_case_link, no_carrier = [], []
    for m in msgs:
        ccs = ix.o2o_targets(m, u.Q_EXCHANGED_IN)
        cc_of[m] = ccs[0] if len(ccs) == 1 else None
        if (len(ccs) != 1 or ix.objects[ccs[0]][cx.COL_OTYPE] != cx.OT_CC
                or ix.objects[ccs[0]].get(u.A_CASE) != ix.objects[m].get(u.A_CASE)):
            bad_case_link.append(m)
        if not _carriers(ix, m):
            no_carrier.append(m)
    not_one, wrong_kind, wrong_case, wrong_key = [], [], [], []
    for e in ix.events:
        links = [(m, q) for m, q in ix.e2o.get(e, []) if q in (cx.Q_SEND, cx.Q_RECEIVE)]
        expected = EXPECTED_LINK.get(ix.events[e].get("elemType")) if ix.is_local(e) else None
        if expected is None:
            if links:
                wrong_kind.append(e)        # a send/receive relation of another event
            continue
        if len(links) != 1:
            not_one.append(e)
            continue
        m, q = links[0]
        if q != expected or ix.objects.get(m, {}).get(cx.COL_OTYPE) != u.OT_MESSAGE:
            wrong_kind.append(e)
            continue
        if cc_of.get(m) not in ix.targets(e, cx.Q_IN_COLLABORATION):
            wrong_case.append(e)
        if key_attr:
            key, mkey = _attr(ix, e, key_attr), _clean(ix.objects[m].get(u.A_KEY))
            if (key != mkey) or (key is None and _carriers(ix, m) != {e}):
                wrong_key.append(e)
    no_request = [x for x in ix.exchange_events() if not ix.targets(x, u.Q_REQUEST)]
    counts = {"logical_messages": len(msgs), "duplicate_identifiers": len(dup),
              "messages_without_exactly_one_case": len(bad_case_link),
              "messages_without_events": len(no_carrier),
              "message_events_without_exactly_one_message": len(not_one),
              "links_of_the_wrong_kind": len(wrong_kind),
              "message_events_in_another_case": len(wrong_case),
              "message_events_with_another_identifier": len(wrong_key),
              "exchange_events_without_logical_message": len(no_request)}
    return _crit("U3 Message identity", STRUCTURAL, counts,
                 dup + bad_case_link + no_carrier + not_one + wrong_kind + wrong_case
                 + wrong_key + no_request,
                 [k for k in counts if k != "logical_messages"])


def _endpoint_findings(ix: Index, m: str) -> Dict[str, bool]:
    """Disagreements among the claims of the carriers of a logical message.
    The stored senders join every sender claim (the executing participant of
    each send, the sender named by each receive or exchange event). The
    stored receivers join every receiver claim (the receivers that sends
    name, those that an exchange event names for its request or its response,
    and the executing participant of each receive); each must be among those
    that the receives observe, when there are any. A receive observes only
    its executing participant (M10), not the receiver it names, which is one
    more claim. An additional receive is a valid multicast."""
    sends, receives = ix.message_events(m)
    senders, receivers = ix.endpoints(m)
    out = {"sender": len(senders) > 1, "receiver": False}
    if receives:
        pid = cx._participant_id
        observed = {pid(p) for r in receives for p in [_attr(ix, r, EXECUTING_ATTR)] if p}
        # The toParticipant of an exchange event names its request receiver.
        naming = sends + [x for x in ix.events_of(m, u.Q_REQUEST) if not ix.is_local(x)]
        declared = set(receivers) | {pid(p) for e in naming
                                     for p in [_attr(ix, e, TO_ATTR)] if p}
        out["receiver"] = bool(declared - observed)
    return out


def u4_endpoint_coherence(ix: Index) -> Criterion:
    c = Counter()
    ex = []
    for m in ix.messages():
        f = _endpoint_findings(ix, m)
        if f["sender"]:
            c["sender"] += 1
        if f["receiver"]:
            c["receiver"] += 1
        if any(f.values()):
            ex.append(m)
    counts = {"logical_messages": len(ix.messages()),
              "several_senders": c["sender"],
              "declared_receiver_not_among_receives": c["receiver"]}
    return _crit("U4 Endpoint coherence", DIAGNOSTIC, counts, ex)


def u5_task_roles(ix: Index) -> Criterion:
    bad_req, bad_resp, bad_init = [], [], []
    for t in ix.tasks():
        if len(ix.targets(t, u.Q_REQUEST)) != 1:
            bad_req.append(t)
        if len(ix.targets(t, u.Q_RESPONSE)) > 1:
            bad_resp.append(t)
        if len(ix.roles(t)[0]) != 1:
            bad_init.append(t)
    counts = {"tasks": len(ix.tasks()),
              "two_way_tasks": sum(bool(ix.targets(t, u.Q_RESPONSE)) for t in ix.tasks()),
              "tasks_without_exactly_one_request": len(bad_req),
              "tasks_with_several_responses": len(bad_resp),
              "tasks_without_exactly_one_initiator": len(bad_init)}
    return _crit("U5 Task roles", STRUCTURAL, counts, bad_req + bad_resp + bad_init,
                 ["tasks_without_exactly_one_request", "tasks_with_several_responses",
                  "tasks_without_exactly_one_initiator"])


U6_CLASSES = ("correct", "correct_multicast", "send_only", "receive_only", "uncorrelated",
              "incoherent", "incoherent_several_tasks", "no_message_events")


def u6_correlation_status(ix: Index) -> Criterion:
    """A logical message is incoherent when several tasks carry it (a reused
    identifier, visible in every profile, also without message events), when
    it has several sends, or when its endpoints disagree (U4). Otherwise one
    with message events is correct (one send, at least one receive; several
    receives are a multicast), send-only or receive-only when it lacks one
    side, and uncorrelated when it has no identifier (an unkeyed singleton,
    whose counterpart cannot be identified). One without message events has
    no correlation status."""
    c = Counter()
    ex = []
    for m in ix.messages():
        sends, receives = ix.message_events(m)
        tasks = set(ix.events_of(m, u.Q_REQUEST)) | set(ix.events_of(m, u.Q_RESPONSE))
        if len(tasks) > 1:
            c["incoherent"] += 1
            c["incoherent_several_tasks"] += 1
            ex.append(m)
            continue
        if not sends and not receives:
            c["no_message_events"] += 1
            continue
        if len(sends) > 1 or any(_endpoint_findings(ix, m).values()):
            c["incoherent"] += 1
            ex.append(m)
        elif _clean(ix.objects[m].get(u.A_KEY)) is None:
            c["uncorrelated"] += 1
        elif not sends:
            c["receive_only"] += 1
        elif not receives:
            c["send_only"] += 1
        else:
            c["correct"] += 1
            if len(receives) > 1:
                c["correct_multicast"] += 1
    return _crit("U6 Correlation status", DIAGNOSTIC, {k: c[k] for k in U6_CLASSES}, ex)


def u7_hierarchy(ix: Index) -> Criterion:
    scopes = ix.of_type(u.OT_SUB)
    multi_task, mixed, empty, multi_parent, cyclic = [], [], [], [], []
    for t in ix.tasks():
        if len(ix.targets(t, u.Q_CONTAINED_BY)) > 1:
            multi_task.append(t)

    def case_of(e):
        chc = ix.targets(e, u.Q_IN_CHOREOGRAPHY)
        return chc[0] if chc else None

    def subtree_tasks(s, seen):
        if s in seen:
            return []
        seen.add(s)
        out = list(ix.events_of(s, u.Q_CONTAINED_BY))
        for c in ix.o2o_targets(s, u.Q_CONTAINS):
            out += subtree_tasks(c, seen)
        return out

    for s in scopes:
        if len(ix.o2o_sources(s, u.Q_CONTAINS)) > 1:
            multi_parent.append(s)
        tasks = subtree_tasks(s, set())
        if not tasks:
            empty.append(s)
        if len({case_of(t) for t in tasks}) > 1:
            mixed.append(s)
        # cycle: s reachable from itself through contains
        stack, seen = list(ix.o2o_targets(s, u.Q_CONTAINS)), set()
        while stack:
            n = stack.pop()
            if n == s:
                cyclic.append(s)
                break
            if n not in seen:
                seen.add(n)
                stack += ix.o2o_targets(n, u.Q_CONTAINS)
    counts = {"scopes": len(scopes),
              "tasks_in_several_innermost_scopes": len(multi_task),
              "scopes_with_tasks_of_several_cases": len(mixed),
              "empty_scopes": len(empty), "scopes_with_several_parents": len(multi_parent),
              "scopes_in_a_cycle": len(cyclic)}
    return _crit("U7 Hierarchy", STRUCTURAL, counts,
                 multi_task + mixed + empty + multi_parent + cyclic,
                 [k for k in counts if k != "scopes"])


def u8_role_coherence(ix: Index) -> Criterion:
    """The initiators of a task are the senders of its request and its
    participants the receivers; a response is sent by the participants to the
    initiators. Roles and endpoints are both stored, so they are compared,
    not derived from each other."""
    bad_init, bad_part, not_reversed = [], [], []
    for t in ix.tasks():
        initiators, participants = (set(r) for r in ix.roles(t))
        req, resp = ix.targets(t, u.Q_REQUEST), ix.targets(t, u.Q_RESPONSE)
        if len(req) == 1:
            senders, receivers = ix.endpoints(req[0])
            if initiators != set(senders):
                bad_init.append(t)
            if participants != set(receivers):
                bad_part.append(t)
        if len(resp) == 1:
            senders, receivers = ix.endpoints(resp[0])
            if set(senders) != participants or set(receivers) != initiators:
                not_reversed.append(t)
    counts = {"tasks": len(ix.tasks()),
              "initiators_not_request_senders": len(bad_init),
              "participants_not_request_receivers": len(bad_part),
              "responses_not_reversing_the_roles": len(not_reversed)}
    return _crit("U8 Role coherence", DIAGNOSTIC, counts, bad_init + bad_part + not_reversed)


def unified_criteria(ix: Index, key_attr: Optional[str]) -> List[Criterion]:
    return [u1_instance(ix), u2_task(ix), u3_message_identity(ix, key_attr),
            u4_endpoint_coherence(ix), u5_task_roles(ix), u6_correlation_status(ix),
            u7_hierarchy(ix), u8_role_coherence(ix)]


def p1_7(label: str, objects_df: pd.DataFrame, export_relations_df: pd.DataFrame) -> Criterion:
    """P1.7 on one serialization, which also rejects an exported E2O relation
    to an object that the serialization does not contain (e.g., a witness
    edge computed on other tables)."""
    c = cx.check_export_reachability(objects_df, export_relations_df)
    known = set(objects_df[cx.COL_OID]) if len(objects_df) else set()
    dangling = (sorted(set(export_relations_df[cx.COL_OID]) - known)
                if len(export_relations_df) else [])
    detail = c.detail + f"; E2O to unknown objects={len(dangling)}" + (
        f"; e.g. {dangling[:5]}" if dangling else "")
    return Criterion(f"{c.name} ({label})", STRUCTURAL, bool(c.passed) and not dangling,
                     {"detail": detail})


def read_serialization(path: str) -> Dict[str, set]:
    """Event and object ids, E2O, and O2O of a written OCEL 2.0 file (pm4py's
    SQLite layout or its .jsonocel)."""
    if str(path).endswith(".sqlite"):
        con = sqlite3.connect(str(path))
        try:
            q = lambda sql: con.execute(sql).fetchall()  # noqa: E731
            return {"events": {i for (i,) in q("select ocel_id from event")},
                    "objects": {i for (i,) in q("select ocel_id from object")},
                    "e2o": set(q("select ocel_event_id, ocel_object_id, ocel_qualifier "
                                 "from event_object")),
                    "o2o": set(q("select ocel_source_id, ocel_target_id, ocel_qualifier "
                                 "from object_object"))}
        finally:
            con.close()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    rel = lambda items: {(it["id"], r["objectId"], r.get("qualifier", ""))  # noqa: E731
                         for it in items for r in it.get("relationships") or []}
    return {"events": {e["id"] for e in data.get("events", [])},
            "objects": {o["id"] for o in data.get("objects", [])},
            "e2o": rel(data.get("events", [])), "o2o": rel(data.get("objects", []))}


def _triples(df: Optional[pd.DataFrame], a: str, b: str) -> set:
    if df is None or df.empty:
        return set()
    return {(r[a], r[b], r[cx.COL_QUALIFIER]) for r in df.to_dict("records")}


def p1_7_file(label: str, path: str, events_df: pd.DataFrame, objects_df: pd.DataFrame,
              export_relations_df: pd.DataFrame, o2o_df: pd.DataFrame) -> Criterion:
    """P1.7 on a written file: the file is read back, P1.7 is checked on what
    it contains, and its events, objects, E2O, and O2O must be those handed to
    the exporter, so that the reachability checked before writing survives the
    serialization."""
    got = read_serialization(path)
    want = {"events": set(events_df[cx.COL_EID]) if len(events_df) else set(),
            "objects": set(objects_df[cx.COL_OID]) if len(objects_df) else set(),
            "e2o": _triples(export_relations_df, cx.COL_EID, cx.COL_OID),
            "o2o": _triples(o2o_df, cx.COL_OID, cx.COL_OID2)}
    reach = p1_7(label, pd.DataFrame({cx.COL_OID: sorted(got["objects"])}),
                 pd.DataFrame(sorted(got["e2o"]),
                              columns=[cx.COL_EID, cx.COL_OID, cx.COL_QUALIFIER]))
    counts: Dict[str, Any] = {"detail": reach.counts["detail"]}
    for k in ("events", "objects", "e2o", "o2o"):
        counts[f"{k}_missing_in_file"] = len(want[k] - got[k])
        counts[f"{k}_added_in_file"] = len(got[k] - want[k])
    ok = reach.ok and not any(v for k, v in counts.items() if k != "detail")
    suffix = Path(path).name
    return Criterion(f"{reach.name.rsplit(' (', 1)[0]} ({label}, {suffix})", STRUCTURAL, ok,
                     counts)


def infsys_criteria(res: "u.UnifiedResult", core_export_relations: pd.DataFrame,
                    view: Optional["cx.TransformResult"] = None,
                    view_export_relations: Optional[pd.DataFrame] = None) -> List[Criterion]:
    """P1.1-P1.6 on alpha_C(mu_U(L)) when the log has local events; P1.7 on the
    exported E2O table of alpha_C(mu_U(L)) and of the core."""
    out = []
    if view is not None and len(view.events_df):
        for c in cx.run_consistency_checks(res.source.local, view):
            out.append(Criterion(c.name, STRUCTURAL, bool(c.passed), {"detail": c.detail}))
        out.append(p1_7("alpha_C", view.objects_df, view_export_relations))
    out.append(p1_7("core", res.objects_df, core_export_relations))
    return out


def as_json(criteria: List[Criterion]) -> List[dict]:
    return [asdict(c) for c in criteria]
