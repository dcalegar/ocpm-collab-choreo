"""The criteria P1.7 and U1-U8 on synthetic logs and on tampered tables.

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
import export_infsys  # noqa: E402
from index import build_index, index_of  # noqa: E402
import map_log  # noqa: E402
from sources import ExchangeEvent, SourceLog  # noqa: E402
import unified as u  # noqa: E402
from test_unified import KEY, T, by_name, local_event, two_way_complete  # noqa: E402

STRUCTURAL = ("U1", "U2", "U3", "U5", "U7")


def crits(log: SourceLog):
    return by_name(criteria.unified_criteria(index_of(u.map_log(log)), KEY))


def cl(*rows) -> SourceLog:
    return SourceLog("cl", [], local=pd.DataFrame(list(rows)))


def tampered(res, add=(), drop=lambda r: False):
    rel = res.relations_df[[not drop(r) for r in res.relations_df.to_dict("records")]]
    rel = pd.concat([rel, pd.DataFrame(list(add))], ignore_index=True)
    return build_index(res.events_df, res.objects_df, rel, res.o2o_df)


def eid(res, activity):
    ev = res.events_df
    return ev.loc[ev[cx.COL_ACTIVITY] == activity, cx.COL_EID].iloc[0]


# ---- structural criteria hold on what the mapping builds -------------------

@pytest.mark.parametrize("log", [
    two_way_complete(),
    cl(local_event("Send", 0, cx.ELEM_SEND, "A", to="B"),
       local_event("Receive", 1, cx.ELEM_RECEIVE, "B", frm="A")),
    SourceLog("x", [], exchange=[ExchangeEvent("c1", "Call", T("2020-01-01 10:00"), 0, "A",
                                               ("B",), None, response_name="r")]),
], ids=["two_way_complete", "unkeyed_cl", "unkeyed_two_way_exchange"])
def test_structural_criteria_hold(log):
    c = crits(log)
    assert all(c[k].ok for k in STRUCTURAL), {k: c[k].counts for k in STRUCTURAL}
    assert c["U3"].counts["messages_without_events"] == 0


# ---- U1 -------------------------------------------------------------------

def test_u1_detects_a_choreography_case_part_of_another_case():
    res = u.map_log(two_way_complete())
    objects = pd.concat([res.objects_df, pd.DataFrame([{
        cx.COL_OID: "cc::other", cx.COL_OTYPE: cx.OT_CC, u.A_CASE: "other"}])],
        ignore_index=True)
    o2o = res.o2o_df.copy()
    redirect = (o2o[cx.COL_OID] == "chc::c1") & (o2o[cx.COL_QUALIFIER] == u.Q_PART_OF)
    assert redirect.sum() == 1
    o2o.loc[redirect, cx.COL_OID2] = "cc::other"
    u1 = criteria.u1_instance(build_index(res.events_df, objects, res.relations_df, o2o))
    assert not u1.ok and u1.counts["cases_part_of_another_case"] == 1
    assert u1.counts["cases_without_exactly_one_part_of"] == 0


# ---- U3 -------------------------------------------------------------------

def test_u3_detects_a_message_event_with_two_messages():
    res = u.map_log(two_way_complete())
    ask = eid(res, "Ask")
    ix = tampered(res, add=[{cx.COL_EID: ask, cx.COL_OID: "message::c1::r1",
                             cx.COL_OTYPE: u.OT_MESSAGE, cx.COL_QUALIFIER: cx.Q_SEND}])
    u3 = criteria.u3_message_identity(ix, KEY)
    assert not u3.ok and u3.counts["message_events_without_exactly_one_message"] == 1


def test_u3_detects_a_receive_linked_as_a_send_and_an_unlinked_message():
    res = u.map_log(two_way_complete())
    get = eid(res, "Get ask")
    ix = tampered(res, drop=lambda r: r[cx.COL_EID] == get and r[cx.COL_QUALIFIER] == cx.Q_RECEIVE,
                  add=[{cx.COL_EID: get, cx.COL_OID: "message::c1::q1",
                        cx.COL_OTYPE: u.OT_MESSAGE, cx.COL_QUALIFIER: cx.Q_SEND}])
    assert criteria.u3_message_identity(ix, KEY).counts["links_of_the_wrong_kind"] == 1


def test_u3_detects_a_keyed_event_on_another_identifier():
    res = u.map_log(two_way_complete())
    get = eid(res, "Get ask")
    ix = tampered(res, drop=lambda r: r[cx.COL_EID] == get and r[cx.COL_QUALIFIER] == cx.Q_RECEIVE,
                  add=[{cx.COL_EID: get, cx.COL_OID: "message::c1::r1",
                        cx.COL_OTYPE: u.OT_MESSAGE, cx.COL_QUALIFIER: cx.Q_RECEIVE}])
    assert criteria.u3_message_identity(ix, KEY).counts[
        "message_events_with_another_identifier"] == 1


def test_u3_unkeyed_events_must_have_their_own_singleton():
    res = u.map_log(cl(local_event("Send", 0, cx.ELEM_SEND, "A", to="B"),
                       local_event("Receive", 1, cx.ELEM_RECEIVE, "B", frm="A")))
    send, recv = eid(res, "Send"), eid(res, "Receive")
    ix = tampered(res, drop=lambda r: r[cx.COL_EID] == recv and r[cx.COL_QUALIFIER] == cx.Q_RECEIVE,
                  add=[{cx.COL_EID: recv, cx.COL_OID: f"message::@{send}",
                        cx.COL_OTYPE: u.OT_MESSAGE, cx.COL_QUALIFIER: cx.Q_RECEIVE}])
    u3 = criteria.u3_message_identity(ix, KEY)
    assert u3.counts["message_events_with_another_identifier"] == 2   # both now share one
    assert u3.counts["messages_without_events"] == 1                  # the orphaned singleton


# ---- U4 and U6 -------------------------------------------------------------

def test_u4_u6_multicast_is_correct():
    c = crits(cl(local_event("Send", 0, cx.ELEM_SEND, "A", "k", to="B"),
                 local_event("Receive", 1, cx.ELEM_RECEIVE, "B", "k", frm="A"),
                 local_event("Receive too", 2, cx.ELEM_RECEIVE, "C", "k", frm="A")))
    assert c["U4"].counts["declared_receiver_not_among_receives"] == 0
    assert c["U6"].counts["correct"] == 1 and c["U6"].counts["correct_multicast"] == 1


def test_u4_u6_declared_receiver_not_observed():
    c = crits(cl(local_event("Send", 0, cx.ELEM_SEND, "A", "k", to="B"),
                 local_event("Receive", 1, cx.ELEM_RECEIVE, "C", "k", frm="A")))
    assert c["U4"].counts["declared_receiver_not_among_receives"] == 1
    assert c["U6"].counts["incoherent"] == 1


def test_u4_exchange_declared_receiver_not_observed():
    log = cl(local_event("Send", 0, cx.ELEM_SEND, "A", "k"),
             local_event("Receive", 1, cx.ELEM_RECEIVE, "C", "k"))
    log.exchange = [ExchangeEvent("c1", "Send", T("2020-01-01 10:00"), 0, "A", ("B",), "k",
                                  attributes={"toParticipant": "B"})]
    assert crits(log)["U4"].counts["declared_receiver_not_among_receives"] == 1


@pytest.mark.parametrize("response_receivers,findings", [(("C",), 1), (None, 0)],
                         ids=["declared_C_observed_A", "default_reversal"])
def test_u4_u6_response_receiver_that_the_exchange_event_declares(response_receivers,
                                                                  findings):
    """The exchange event declares the receiver of its response; a receive
    observes A. Only a declared C is a U4 finding (the default is the request
    sender, A)."""
    log = cl(local_event("Get answer", 5, cx.ELEM_RECEIVE, "A", "r", frm="B"))
    log.exchange = [ExchangeEvent("c1", "Call", T("2020-01-01 10:00"), 0, "A", ("B",), "q",
                                  response_key="r", response_receivers=response_receivers)]
    c = crits(log)
    assert c["U4"].counts["declared_receiver_not_among_receives"] == findings
    assert c["U6"].counts["incoherent"] == findings
    assert all(c[k].ok for k in STRUCTURAL)


def test_u4_u6_receiver_named_by_a_receive_is_not_observed():
    """The exchange event declares C as the receiver of its response; the
    receive is executed by A and still names toParticipant=C. Only the
    executing participant is observed (UM9), so C remains a U4 finding."""
    log = cl(local_event("Get answer", 5, cx.ELEM_RECEIVE, "A", "r", frm="B", to="C"))
    log.exchange = [ExchangeEvent("c1", "Call", T("2020-01-01 10:00"), 0, "A", ("B",), "q",
                                  response_key="r", response_receivers=("C",))]
    res = u.map_log(log)
    recv = res.events_df.set_index(cx.COL_EID).loc[eid(res, "Get answer")]
    assert recv["participant"] == "A" and recv["toParticipant"] == "C"
    c = by_name(criteria.unified_criteria(index_of(res), KEY))
    assert c["U4"].counts["declared_receiver_not_among_receives"] == 1
    assert c["U6"].counts["incoherent"] == 1
    assert all(c[k].ok for k in STRUCTURAL)


def test_u4_u6_several_senders():
    c = crits(cl(local_event("Send", 0, cx.ELEM_SEND, "A", "k", to="B"),
                 local_event("Receive", 1, cx.ELEM_RECEIVE, "B", "k", frm="C")))
    assert c["U4"].counts["several_senders"] == 1
    assert c["U6"].counts["incoherent"] == 1 and c["U6"].counts["incoherent_several_tasks"] == 0


def test_u6_classes():
    c = crits(cl(local_event("Only sent", 0, cx.ELEM_SEND, "A", "s", to="B"),
                 local_event("Only received", 1, cx.ELEM_RECEIVE, "B", "r", frm="A"),
                 local_event("Unkeyed send", 2, cx.ELEM_SEND, "A", to="B"),
                 local_event("Unkeyed receive", 3, cx.ELEM_RECEIVE, "B", frm="A")))
    u6 = c["U6"].counts
    assert (u6["send_only"], u6["receive_only"], u6["uncorrelated"], u6["correct"]) == (1, 1, 2, 0)
    x = [ExchangeEvent("c1", "S", T("2020-01-01 10:00"), 0, "A", ("B",), "k")]
    assert crits(SourceLog("chl", [], exchange=x))["U6"].counts["no_message_events"] == 1


# ---- U5 and U8 -------------------------------------------------------------

def test_u5_requires_one_initiator():
    x = [ExchangeEvent("c1", "S", T("2020-01-01 10:00"), 0, None, ("B",), "k")]
    u5 = crits(SourceLog("chl", [], exchange=x))["U5"]
    assert not u5.ok and u5.counts["tasks_without_exactly_one_initiator"] == 1


def test_u8_holds_with_the_bpmn_fallback():
    assert not any(v for k, v in crits(two_way_complete())["U8"].counts.items() if k != "tasks")


def test_u8_reports_stored_roles_that_disagree_with_endpoints():
    x = ExchangeEvent("c1", "Call", T("2020-01-01 10:00"), 0, "A", ("B",), "q",
                      response_key="r", initiators=("C",), participants=("D",),
                      response_senders=("E",), response_receivers=("F",))
    c = crits(SourceLog("claims", [], exchange=[x]))
    assert c["U8"].ok and c["U8"].counts == {
        "tasks": 1, "initiators_not_request_senders": 1,
        "participants_not_request_receivers": 1, "responses_not_reversing_the_roles": 1}
    assert all(c[k].ok for k in STRUCTURAL)


def test_u8_reports_a_multicast_that_the_exchange_event_does_not_name():
    """Smart Agriculture's case: the ChL names one receiver, the CL observes two."""
    log = cl(local_event("Publish", 0, cx.ELEM_SEND, "A", "k"),
             local_event("Get", 1, cx.ELEM_RECEIVE, "B", "k"),
             local_event("Get too", 2, cx.ELEM_RECEIVE, "C", "k"))
    log.exchange = [ExchangeEvent("c1", "Publish", T("2020-01-01 10:00"), 0, "A", ("B",), "k")]
    c = crits(log)
    assert c["U8"].counts["participants_not_request_receivers"] == 1
    assert c["U4"].counts["declared_receiver_not_among_receives"] == 0


# ---- P1 ---------------------------------------------------------------------

def test_p1_on_alpha_c_and_p1_7_on_both_serializations():
    res = u.map_log(two_way_complete())
    view = export_infsys.of(res)
    out = criteria.infsys_criteria(res, map_log.export_relations(res), view,
                                   export_infsys.export_relations(view))
    names = [c.name for c in out]
    assert names[-2:] == ["P1.7 Export reachability (alpha_C)", "P1.7 Export reachability (core)"]
    assert [n.split(" ")[0] for n in names] == [
        "P1.1", "P1.2", "P1.2b", "P1.3", "P1.4", "P1.5", "P1.6", "P1.7", "P1.7"]
    assert all(c.ok for c in out)


def test_p1_7_only_on_the_core_without_local_events():
    x = [ExchangeEvent("c1", "S", T("2020-01-01 10:00"), 0, "A", ("B",), "k")]
    res = u.map_log(SourceLog("chl", [], exchange=x))
    out = criteria.infsys_criteria(res, map_log.export_relations(res), export_infsys.of(res), None)
    assert [c.name for c in out] == ["P1.7 Export reachability (core)"] and out[0].ok


def test_core_witnesses_reference_only_core_objects():
    res = u.map_log(two_way_complete())
    rel = map_log.export_relations(res)
    assert set(rel[cx.COL_OID]) <= set(res.objects_df[cx.COL_OID])
    assert not any(o.startswith("msg::") for o in rel[cx.COL_OID])


def test_p1_7_holds_on_the_written_files(tmp_path):
    report = map_log.write_outputs(u.map_log(two_way_complete()), str(tmp_path / "tw"))
    files = [c for c in report["criteria"] if c["name"].startswith("P1.7") and "," in c["name"]]
    assert [c["name"] for c in files] == [
        "P1.7 Export reachability (core, tw.jsonocel)",
        "P1.7 Export reachability (core, tw.sqlite)",
        "P1.7 Export reachability (alpha_C, tw_infsys.sqlite)"]
    assert all(c["ok"] for c in files) and report["structural_criteria_hold"]


def test_p1_7_file_detects_what_the_serialization_lost(tmp_path):
    import sqlite3
    res = u.map_log(two_way_complete())
    map_log.write_outputs(res, str(tmp_path / "tw"))
    con = sqlite3.connect(str(tmp_path / "tw.sqlite"))
    con.execute("delete from event_object where ocel_object_id = 'chc::c1'")
    con.commit()
    con.close()
    p = criteria.p1_7_file("core", str(tmp_path / "tw.sqlite"), res.events_df, res.objects_df,
                           map_log.export_relations(res), res.o2o_df)
    assert not p.ok
    assert p.counts["e2o_missing_in_file"] >= 1 and "unreachable in the exported E2O table=1" \
        in p.counts["detail"]


def test_p1_7_rejects_an_edge_to_an_unknown_object():
    res = u.map_log(two_way_complete())
    rel = pd.concat([map_log.export_relations(res), pd.DataFrame([{
        cx.COL_EID: eid(res, "Ask"), cx.COL_OID: "msg::gone", cx.COL_OTYPE: cx.OT_MESSAGE,
        cx.COL_QUALIFIER: cx.Q_FROM}])], ignore_index=True)
    p = criteria.p1_7("core", res.objects_df, rel)
    assert not p.ok and "unknown objects=1" in p.counts["detail"]
