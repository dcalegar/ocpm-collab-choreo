"""Synthetic cases that the corpus in data/ does not exercise.

Run from the repository root: `.venv/bin/python -m pytest source/mapping/tests`.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.disable(logging.WARNING)

from infsys import cx  # noqa: E402
import criteria  # noqa: E402
from index import build_index, index_of  # noqa: E402
from sources import ExchangeEvent, SourceLog  # noqa: E402
import unified as u  # noqa: E402

T = lambda s: pd.Timestamp(s, tz="UTC")  # noqa: E731
KEY = "msgInstanceId"


def local_event(act, minute, elem, participant, key=None, frm=None, to=None):
    row = {cx.CASE_KEY: "c1", cx.ACTIVITY_KEY: act, cx.TIMESTAMP_KEY: T(f"2020-01-01 10:{minute:02d}"),
           cx.ELEMTYPE_KEY: elem, cx.PARTICIPANT_KEY: participant}
    if key:
        row[KEY] = key
    if frm:
        row[cx.FROM_KEY] = frm
    if to:
        row[cx.TO_KEY] = to
    return row


def two_way_complete() -> SourceLog:
    """A two-way task (request q1 from A to B, response r1 back) recorded by one
    exchange event, with the four message events of both messages."""
    local = pd.DataFrame([
        local_event("Ask", 0, cx.ELEM_SEND, "A", "q1", to="B"),
        local_event("Get ask", 1, cx.ELEM_RECEIVE, "B", "q1", frm="A"),
        local_event("Answer", 2, cx.ELEM_SEND, "B", "r1", to="A"),
        local_event("Get answer", 3, cx.ELEM_RECEIVE, "A", "r1", frm="B"),
    ])
    x = [ExchangeEvent("c1", "Ask", T("2020-01-01 10:00"), 0, "A", ("B",), "q1",
                       response_key="r1")]
    return SourceLog("two_way", [], local=local, exchange=x)


def by_name(crits):
    return {c.name.split(" ")[0]: c for c in crits}


def core_tables(res):
    objects = res.objects_df.set_index(cx.COL_OID).to_dict("index")
    events = res.events_df.set_index(cx.COL_EID).to_dict("index")
    e2o = {(r[cx.COL_EID], r[cx.COL_OID], r[cx.COL_QUALIFIER])
           for r in res.relations_df.to_dict("records")}
    o2o = {(r[cx.COL_OID], r[cx.COL_OID2], r[cx.COL_QUALIFIER])
           for r in res.o2o_df.to_dict("records")}
    return events, objects, e2o, o2o


def event_with_activity(events, activity):
    return next(eid for eid, row in events.items() if row[cx.COL_ACTIVITY] == activity)


def test_two_way_exchange_gives_one_task():
    res = u.map_log(two_way_complete())
    assert res.stats["n_tasks"] == 1
    assert res.stats["n_two_way_tasks"] == 1
    events, objects, e2o, o2o = core_tables(res)
    assert {oid for oid, row in objects.items() if row[cx.COL_OTYPE] == cx.OT_MESSAGE} == {
        "message::c1::q1", "message::c1::r1"}
    assert not any(oid.startswith("msg::") for oid in objects)
    ask, get_ask = event_with_activity(events, "Ask"), event_with_activity(events, "Get ask")
    answer = event_with_activity(events, "Answer")
    get_answer = event_with_activity(events, "Get answer")
    assert (ask, "message::c1::q1", "send") in e2o
    assert (get_ask, "message::c1::q1", "receive") in e2o
    assert (answer, "message::c1::r1", "send") in e2o
    assert (get_answer, "message::c1::r1", "receive") in e2o
    task = next(e for e, _, q in e2o if q == u.Q_REQUEST)
    assert (task, "part::A", u.Q_INITIATOR) in e2o
    assert (task, "part::B", u.Q_PARTICIPANT) in e2o
    assert ("message::c1::q1", "part::A", u.Q_SOURCE) in o2o
    assert ("message::c1::q1", "part::B", u.Q_TARGET) in o2o
    assert ("message::c1::r1", "part::B", u.Q_SOURCE) in o2o
    assert ("message::c1::r1", "part::A", u.Q_TARGET) in o2o
    assert not any(q in ("sent_as", "received_as", "from", "to") for _, _, q in o2o)


def test_u2_detects_a_response_send_as_task():
    res = u.map_log(two_way_complete())
    ix = index_of(res)
    answer = next(e for e, r in ix.events.items() if r[cx.COL_ACTIVITY] == "Answer")
    extra = pd.DataFrame([
        {cx.COL_EID: answer, cx.COL_OID: "message::c1::r1", cx.COL_OTYPE: u.OT_MESSAGE,
         cx.COL_QUALIFIER: u.Q_REQUEST},
        {cx.COL_EID: answer, cx.COL_OID: "chc::c1", cx.COL_OTYPE: u.OT_CHC,
         cx.COL_QUALIFIER: u.Q_IN_CHOREOGRAPHY}])
    bad = build_index(res.events_df, res.objects_df,
                      pd.concat([res.relations_df, extra], ignore_index=True), res.o2o_df)
    u2 = criteria.u2_task(bad)
    assert not u2.ok and u2.counts["sends_with_wrong_task_status"] == 1


def test_conflicting_content_is_reported_not_lost():
    x = [ExchangeEvent("c1", "S", T("2020-01-01 10:00"), 0, "A", ("B",), "k",
                       name="m", content={"payload": "first"}),
         ExchangeEvent("c1", "S", T("2020-01-01 10:05"), 1, "A", ("B",), "k",
                       name="n", content={"payload": "second"})]
    res = u.map_log(SourceLog("reused", [], exchange=x))
    cm = res.objects_df.set_index(cx.COL_OID).loc["message::c1::k"]
    assert cm["payload"] == "first" and cm[u.A_NAME] == "m"
    found = {(c["attribute"], tuple(c["values"])) for c in res.stats["conflicting_values"]}
    assert found == {("payload", ("first", "second")), (u.A_NAME, ("m", "n"))}
    assert res.stats["n_logical_messages_with_conflicting_values"] == 1


@pytest.mark.parametrize("send_minute,kept,values", [
    (0, "from send", ("from send", "from exchange")),     # the send at 10:00 comes first
    (9, "from exchange", ("from exchange", "from send")),  # the exchange at 10:04 comes first
])
def test_conflicting_names_keep_the_first_in_event_order(send_minute, kept, values):
    """UM9: the first value in event order is kept, across exchange and local
    events, whichever kind the mapping reads first."""
    send = local_event("Send", send_minute, cx.ELEM_SEND, "A", "k", to="B")
    send["msgName"] = "from send"
    x = [ExchangeEvent("c1", "S", T("2020-01-01 10:04"), 0, "A", ("B",), "k",
                       name="from exchange")]
    res = u.map_log(SourceLog("mixed", [], local=pd.DataFrame([send]), exchange=x))
    assert res.objects_df.set_index(cx.COL_OID).loc["message::c1::k", u.A_NAME] == kept
    assert [(c["kept"], tuple(c["values"])) for c in res.stats["conflicting_values"]] == [
        (kept, values)]


def test_u6_diagnoses_a_reused_key_without_message_events():
    """Choreography profile: two exchange events reuse one identifier, so one
    logical message has two tasks and no message events."""
    x = [ExchangeEvent("c1", "S", T("2020-01-01 10:00"), i, "A", ("B",), "k")
         for i in range(2)]
    c = by_name(criteria.unified_criteria(index_of(u.map_log(SourceLog("reused", [], exchange=x))), KEY))
    assert c["U6"].counts["incoherent"] == 1
    assert c["U6"].counts["incoherent_several_tasks"] == 1
    assert c["U6"].counts["no_message_events"] == 0
    assert all(c[k].ok for k in ("U1", "U2", "U3", "U5", "U7"))


def test_u6_two_way_task_is_not_several_tasks():
    x = [ExchangeEvent("c1", "S", T("2020-01-01 10:00"), 0, "A", ("B",), "k",
                       response_key="r")]
    c = by_name(criteria.unified_criteria(index_of(u.map_log(SourceLog("tw", [], exchange=x))), KEY))
    assert c["U6"].counts["incoherent"] == 0 and c["U6"].counts["no_message_events"] == 2


def test_equal_values_are_not_conflicts():
    x = [ExchangeEvent("c1", "S", T("2020-01-01 10:00"), i, "A", ("B",), "k",
                       content={"payload": "same"}) for i in range(2)]
    assert u.map_log(SourceLog("same", [], exchange=x)).stats["conflicting_values"] == []


@pytest.mark.parametrize("response_key,expected", [("r", True), (None, False)])
def test_correlation_requires_the_response_identifier(response_key, expected):
    x = [ExchangeEvent("c1", "S", T("2020-01-01 10:00"), 0, "A", ("B",), "k",
                       response_key=response_key, response_name="resp")]
    assert u.profile(SourceLog("p", [], exchange=x))["correlation"] is expected


def test_one_way_exchange_needs_no_response_identifier():
    x = [ExchangeEvent("c1", "S", T("2020-01-01 10:00"), 0, "A", ("B",), "k")]
    assert u.profile(SourceLog("p", [], exchange=x))["correlation"] is True


def test_empty_content_values_are_kept():
    x = [ExchangeEvent("c1", "S", T("2020-01-01 10:00"), 0, "A", ("B",), "k",
                       content={"reason": "", "absent": None})]
    cm = u.map_log(SourceLog("empty", [], exchange=x)).objects_df.set_index(cx.COL_OID).loc[
        "message::c1::k"]
    assert cm["reason"] == "" and "absent" not in cm.index


def test_unkeyed_send_and_receive_get_distinct_singletons():
    local = pd.DataFrame([
        local_event("Send", 0, cx.ELEM_SEND, "A", to="B"),
        local_event("Receive", 1, cx.ELEM_RECEIVE, "B", frm="A"),
    ])
    res = u.map_log(SourceLog("unkeyed", [], local=local))
    events, objects, e2o, o2o = core_tables(res)
    send = event_with_activity(events, "Send")
    receive = event_with_activity(events, "Receive")
    send_mid, receive_mid = f"message::@{send}", f"message::@{receive}"
    assert send_mid != receive_mid
    assert objects[send_mid][cx.COL_OTYPE] == cx.OT_MESSAGE
    assert objects[receive_mid][cx.COL_OTYPE] == cx.OT_MESSAGE
    assert (send, send_mid, cx.Q_SEND) in e2o
    assert (receive, receive_mid, cx.Q_RECEIVE) in e2o
    assert (send_mid, "cc::c1", u.Q_EXCHANGED_IN) in o2o
    assert (receive_mid, "cc::c1", u.Q_EXCHANGED_IN) in o2o
    assert res.stats["n_singleton_logical_messages"] == 2


def test_unkeyed_two_way_exchange_gets_request_and_response_singletons():
    x = ExchangeEvent("c1", "Call", T("2020-01-01 10:00"), 0, "A", ("B",), None,
                      response_name="return")
    res = u.map_log(SourceLog("unkeyed_two_way", [], exchange=[x]))
    events, objects, e2o, o2o = core_tables(res)
    task = event_with_activity(events, "Call")
    req, response = f"message::@{task}", f"message::@{task}::response"
    assert {req, response} <= set(objects)
    assert (task, req, u.Q_REQUEST) in e2o
    assert (task, response, u.Q_RESPONSE) in e2o
    assert (req, "part::A", u.Q_SOURCE) in o2o
    assert (req, "part::B", u.Q_TARGET) in o2o
    assert (response, "part::B", u.Q_SOURCE) in o2o
    assert (response, "part::A", u.Q_TARGET) in o2o


def test_explicit_roles_and_response_endpoints_are_not_derived():
    x = ExchangeEvent(
        "c1", "Call", T("2020-01-01 10:00"), 0, "A", ("B",), "q",
        response_key="r", initiators=("C",), participants=("D",),
        response_senders=("E",), response_receivers=("F",))
    res = u.map_log(SourceLog("claims", [], exchange=[x]))
    events, _objects, e2o, o2o = core_tables(res)
    task = event_with_activity(events, "Call")
    assert (task, "part::C", u.Q_INITIATOR) in e2o
    assert (task, "part::D", u.Q_PARTICIPANT) in e2o
    assert ("message::c1::q", "part::A", u.Q_SOURCE) in o2o
    assert ("message::c1::q", "part::B", u.Q_TARGET) in o2o
    assert ("message::c1::r", "part::E", u.Q_SOURCE) in o2o
    assert ("message::c1::r", "part::F", u.Q_TARGET) in o2o


def test_send_task_participants_include_correlated_receivers():
    """Hobeck's XES-like case: neither event names its counterparty, so the
    request receiver and task participant come from the receive execution."""
    local = pd.DataFrame([
        local_event("Send", 0, cx.ELEM_SEND, "A", key="k"),
        local_event("Receive", 1, cx.ELEM_RECEIVE, "B", key="k"),
        local_event("Receive multicast", 2, cx.ELEM_RECEIVE, "C", key="k"),
    ])
    res = u.map_log(SourceLog("receivers", [], local=local))
    events, _objects, e2o, o2o = core_tables(res)
    send = event_with_activity(events, "Send")
    assert (send, "part::A", u.Q_INITIATOR) in e2o
    assert {(oid, q) for eid, oid, q in e2o
            if eid == send and q == u.Q_PARTICIPANT} == {
                ("part::B", u.Q_PARTICIPANT), ("part::C", u.Q_PARTICIPANT)}
    assert {(target, q) for source, target, q in o2o
            if source == "message::c1::k" and q == u.Q_TARGET} == {
                ("part::B", u.Q_TARGET), ("part::C", u.Q_TARGET)}


def test_eta_h_exports_stored_roles_and_endpoints():
    import export_hobeck
    x = ExchangeEvent(
        "c1", "Call", T("2020-01-01 10:00"), 0, "A", ("B",), "q",
        response_key="r", initiators=("C",), participants=("D",),
        response_senders=("E",), response_receivers=("F",))
    out = export_hobeck.export(index_of(u.map_log(SourceLog("claims", [], exchange=[x]))))
    (ev,) = out["events"]
    rel = {(r["qualifier"], r["objectId"]) for r in ev["relationships"]}
    assert {("choreo:initiator", "part::C"), ("choreo:participant", "part::D")} <= rel
    assert not any(q in ("choreo:initiator", "choreo:participant") and o in ("part::A", "part::B")
                   for q, o in rel)
    objs = {o["id"]: o for o in out["objects"]}
    ends = lambda m: {(r["qualifier"], r["objectId"]) for r in objs[m]["relationships"]}  # noqa: E731
    assert ends("message::c1::q") == {("choreo:source", "part::A"), ("choreo:target", "part::B")}
    assert ends("message::c1::r") == {("choreo:source", "part::E"), ("choreo:target", "part::F")}
