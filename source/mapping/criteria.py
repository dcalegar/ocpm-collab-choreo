"""Consistency criteria of the unified representation.

- P1.1-P1.6: the InfSys criteria, evaluated by the InfSys implementation on the
  local events and the output of M1-M8; P1.7 (export reachability) on the
  E2O table handed to the exporters, including the new objects.
- U1-U7: the criteria for what M9-M13 add (paper, Section 3.3). They read the
  log through `index.Index`, so they apply to any log in the representation.

Structural criteria (U1-U3, U5, U7) must hold; a violation is an
implementation error. Diagnostic criteria (U4, U6) report the quality of the
source data as counts and never fail. C0-C16 of Hobeck et al. are checked by
their validator on the exported view (`export_hobeck.py`).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from infsys import cx
from index import Index
import unified as u

STRUCTURAL, DIAGNOSTIC = "structural", "diagnostic"


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


def u1_instance(ix: Index) -> Criterion:
    bad_inst, bad_case, bad_part, empty = [], [], [], []
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
        if not ix.events_of(c, u.Q_IN_CHOREOGRAPHY):
            empty.append(c)
    counts = {"tasks": len(ix.tasks()), "choreography_cases": len(ix.of_type(u.OT_CHC)),
              "tasks_without_exactly_one_case": len(bad_inst),
              "tasks_in_another_case_than_their_request": len(bad_case),
              "cases_without_exactly_one_part_of": len(bad_part),
              "cases_without_tasks": len(empty)}
    return _crit("U1 Instance", STRUCTURAL, counts, bad_inst + bad_case + bad_part + empty,
                 [k for k in counts if k not in ("tasks", "choreography_cases")])


def u2_task(ix: Index) -> Criterion:
    tasks = set(ix.tasks())
    exchange = ix.exchange_events()
    recorded = {m for x in exchange for q in (u.Q_REQUEST, u.Q_RESPONSE)
                for m in ix.targets(x, q)}
    x_not_task = [x for x in exchange if x not in tasks]
    send_wrong, other = [], []
    for e in ix.events:
        if not ix.is_local(e):
            continue
        sends = ix.targets(e, cx.Q_SEND)
        if sends:
            cms = ix.o2o_sources(sends[0], u.Q_SENT_AS)
            should = not (set(cms) & recorded)
            if should != (e in tasks):
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
    cms = ix.of_type(u.OT_CM)
    keys = Counter((ix.objects[c].get(u.A_CASE), ix.objects[c].get(u.A_KEY))
                   for c in cms if ix.objects[c].get(u.A_KEY) is not None)
    dup = [f"{k}" for k, n in keys.items() if n > 1]
    links = Counter(m for c in cms for m, q in ix.o2o.get(c, [])
                    if q in (u.Q_SENT_AS, u.Q_RECEIVED_AS))
    multi = [m for m, n in links.items() if n > 1]
    wrong_kind, unlinked, wrong_key = [], [], []
    for e in ix.events:
        for q, link in ((cx.Q_SEND, u.Q_SENT_AS), (cx.Q_RECEIVE, u.Q_RECEIVED_AS)):
            for m in ix.targets(e, q):
                srcs = [c for c, qq in ix.o2o_in.get(m, []) if qq in (u.Q_SENT_AS, u.Q_RECEIVED_AS)]
                if any(qq != link for c, qq in ix.o2o_in.get(m, [])
                       if qq in (u.Q_SENT_AS, u.Q_RECEIVED_AS)):
                    wrong_kind.append(m)
                key = None
                if key_attr:
                    v = ix.events[e].get(key_attr)
                    key = None if v is None or v != v or str(v).strip() == "" else str(v).strip()
                if key is None and q == cx.Q_RECEIVE:
                    if srcs:
                        wrong_key.append(m)
                    continue
                if not srcs:
                    unlinked.append(m)
                elif key is not None and any(ix.objects[c].get(u.A_KEY) != key for c in srcs):
                    wrong_key.append(m)
    no_request = [x for x in ix.exchange_events() if not ix.targets(x, u.Q_REQUEST)]
    counts = {"logical_messages": len(cms), "duplicate_identifiers": len(dup),
              "messages_linked_more_than_once": len(multi),
              "links_of_the_wrong_kind": len(wrong_kind),
              "keyed_or_sent_messages_not_linked": len(unlinked),
              "messages_linked_to_another_identifier": len(wrong_key),
              "exchange_events_without_logical_message": len(no_request)}
    return _crit("U3 Message identity", STRUCTURAL, counts,
                 dup + multi + wrong_kind + unlinked + wrong_key + no_request,
                 [k for k in counts if k != "logical_messages"])


def _endpoint_findings(ix: Index, cm: str) -> Dict[str, bool]:
    """Disagreements among the recorded endpoints of a logical message."""
    sends, receives = ix.message_events(cm)
    local = sends + receives
    out = {"sender": False, "receiver": False, "exchange": False}
    senders, receivers = ix.endpoints(cm)
    if len(senders) > 1:
        out["sender"] = True
    if local and receives:
        observed = {p for m in receives for p in ix.o2o_targets(m, cx.Q_TO)}
        recorded = {p for m in sends for p in ix.o2o_targets(m, cx.Q_TO)}
        if recorded - observed:
            out["receiver"] = True
    if local:
        names_s = {ix.participant_name(p) for p in senders}
        names_r = {ix.participant_name(p) for p in receivers}
        for x in ix.events_of(cm, u.Q_REQUEST):
            if ix.is_local(x):
                continue
            ev = ix.events[x]
            f, t = ev.get("fromParticipant"), ev.get("toParticipant")
            if (isinstance(f, str) and f not in names_s) or \
               (isinstance(t, str) and t not in names_r):
                out["exchange"] = True
    return out


def u4_endpoint_coherence(ix: Index) -> Criterion:
    c = Counter()
    ex = []
    for cm in ix.of_type(u.OT_CM):
        f = _endpoint_findings(ix, cm)
        for k, v in f.items():
            if v:
                c[k] += 1
                ex.append(cm)
    counts = {"logical_messages": len(ix.of_type(u.OT_CM)),
              "several_senders": c["sender"],
              "recorded_receiver_not_among_receives": c["receiver"],
              "exchange_event_endpoints_disagree": c["exchange"]}
    return _crit("U4 Endpoint coherence", DIAGNOSTIC, counts, ex)


def u5_task_roles(ix: Index) -> Criterion:
    bad_req, bad_resp, not_reversed = [], [], []
    for t in ix.tasks():
        req, resp = ix.targets(t, u.Q_REQUEST), ix.targets(t, u.Q_RESPONSE)
        if len(req) != 1:
            bad_req.append(t)
        if len(resp) > 1:
            bad_resp.append(t)
        if len(req) == 1 and len(resp) == 1:
            s1, r1 = ix.endpoints(req[0])
            s2, r2 = ix.endpoints(resp[0])
            if set(s2) != set(r1) or set(r2) != set(s1):
                not_reversed.append(t)
    counts = {"tasks": len(ix.tasks()),
              "two_way_tasks": sum(bool(ix.targets(t, u.Q_RESPONSE)) for t in ix.tasks()),
              "tasks_without_exactly_one_request": len(bad_req),
              "tasks_with_several_responses": len(bad_resp),
              "responses_not_reversing_the_request": len(not_reversed)}
    return _crit("U5 Task roles", STRUCTURAL, counts, bad_req + bad_resp + not_reversed,
                 ["tasks_without_exactly_one_request", "tasks_with_several_responses",
                  "responses_not_reversing_the_request"])


def u6_correlation_status(ix: Index) -> Criterion:
    """A logical message is incoherent when several tasks carry it (a reused
    identifier, visible in every profile, also without message events), when
    it has several sends, or when its endpoints disagree."""
    c = Counter()
    ex = []
    for cm in ix.of_type(u.OT_CM):
        sends, receives = ix.message_events(cm)
        carriers = set(ix.events_of(cm, u.Q_REQUEST)) | set(ix.events_of(cm, u.Q_RESPONSE))
        if len(carriers) > 1:
            c["incoherent"] += 1
            c["incoherent_several_tasks"] += 1
            ex.append(cm)
            continue
        if not sends and not receives:
            c["no_message_events"] += 1
            continue
        f = _endpoint_findings(ix, cm)
        if len(sends) > 1 or f["sender"] or f["receiver"]:
            c["incoherent"] += 1
            ex.append(cm)
        elif not sends or not receives:
            c["absent"] += 1
            c["absent_no_send" if not sends else "absent_no_receive"] += 1
        else:
            c["correct"] += 1
            if len(receives) > 1:
                c["correct_multicast"] += 1
    counts = {k: c[k] for k in ("correct", "correct_multicast", "absent", "absent_no_send",
                                "absent_no_receive", "incoherent",
                                "incoherent_several_tasks", "no_message_events")}
    return _crit("U6 Correlation status", DIAGNOSTIC, counts, ex)


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


def unified_criteria(ix: Index, key_attr: Optional[str]) -> List[Criterion]:
    return [u1_instance(ix), u2_task(ix), u3_message_identity(ix, key_attr),
            u4_endpoint_coherence(ix), u5_task_roles(ix), u6_correlation_status(ix),
            u7_hierarchy(ix)]


def infsys_criteria(res: "u.UnifiedResult", export_relations_df) -> List[Criterion]:
    """P1.1-P1.6 on the local part (InfSys implementation); P1.7 on the
    exported E2O table of the whole log."""
    out = []
    if res.infsys is not None:
        for c in cx.run_consistency_checks(res.source.local, res.infsys):
            out.append(Criterion(c.name, STRUCTURAL, bool(c.passed), {"detail": c.detail}))
    p17 = cx.check_export_reachability(res.objects_df, export_relations_df)
    out.append(Criterion(p17.name, STRUCTURAL, bool(p17.passed), {"detail": p17.detail}))
    return out


def as_json(criteria: List[Criterion]) -> List[dict]:
    return [asdict(c) for c in criteria]
