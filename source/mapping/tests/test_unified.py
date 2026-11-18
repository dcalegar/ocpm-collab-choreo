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


def test_two_way_exchange_gives_one_task():
    res = u.map_log(two_way_complete())
    assert res.stats["n_tasks"] == 1
    assert res.stats["n_two_way_tasks"] == 1
    c = by_name(criteria.unified_criteria(index_of(res), KEY))
    assert all(x.ok for x in c.values()), {k: x.counts for k, x in c.items() if not x.ok}


def test_u2_detects_a_response_send_as_task():
    res = u.map_log(two_way_complete())
    ix = index_of(res)
    answer = next(e for e, r in ix.events.items() if r[cx.COL_ACTIVITY] == "Answer")
    extra = pd.DataFrame([
        {cx.COL_EID: answer, cx.COL_OID: "cm::c1::r1", cx.COL_OTYPE: u.OT_CM, cx.COL_QUALIFIER: u.Q_REQUEST},
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
    cm = res.objects_df.set_index(cx.COL_OID).loc["cm::c1::k"]
    assert cm["payload"] == "first" and cm[u.A_NAME] == "m"
    found = {(c["attribute"], tuple(c["values"])) for c in res.stats["conflicting_values"]}
    assert found == {("payload", ("first", "second")), (u.A_NAME, ("m", "n"))}
    assert res.stats["n_logical_messages_with_conflicting_values"] == 1


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
    cm = u.map_log(SourceLog("empty", [], exchange=x)).objects_df.set_index(cx.COL_OID).loc["cm::c1::k"]
    assert cm["reason"] == "" and "absent" not in cm.index
