"""The export adapter alpha_C against its oracle, the InfSys mapping (M1-M8).

`UnifiedResult.infsys` is used here only as the oracle: alpha_C is built from
the core tables and must give exactly the tables of `cx.transform`.

Run from the repository root: `.venv/bin/python -m pytest source/mapping/tests`.
"""

from __future__ import annotations

import dataclasses
import logging
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "experiments"))
logging.disable(logging.WARNING)

from infsys import cx  # noqa: E402
from sources import ExchangeEvent, SourceLog  # noqa: E402
import export_infsys  # noqa: E402
import unified as u  # noqa: E402
from test_unified import T, local_event, two_way_complete  # noqa: E402

TABLES = ("events_df", "objects_df", "relations_df", "o2o_df")
CORE_ONLY_QUALIFIERS = {u.Q_REQUEST, u.Q_RESPONSE, u.Q_INITIATOR, u.Q_PARTICIPANT,
                        u.Q_SOURCE, u.Q_TARGET, u.Q_IN_CHOREOGRAPHY, u.Q_CONTAINED_BY,
                        u.Q_CONTAINS}


def rows(df: pd.DataFrame) -> Counter:
    """The rows of a table as a multiset, with the type of every present value."""
    out = Counter()
    for r in df.to_dict("records"):
        out[tuple(sorted((k, type(v).__name__, repr(v)) for k, v in r.items()
                         if v is not None and not pd.isna(v)))] += 1
    return out


def assert_same_as_infsys(view, ref) -> None:
    for t in TABLES:
        a, b = getattr(view, t), getattr(ref, t)
        assert set(a.columns) == set(b.columns), t
        assert rows(a) == rows(b), t
        assert {c: str(a[c].dtype) for c in a.columns} == {c: str(b[c].dtype) for c in b.columns}, t
    assert view.stats == ref.stats
    assert ({p: view.participant_types.type_of(p) for p in view.participant_types.participants}
            == {p: ref.participant_types.type_of(p) for p in ref.participant_types.participants})


def multicast() -> SourceLog:
    """Neither event names its counterparty; the logical message gets both
    receivers as targets, but no observation records them."""
    local = pd.DataFrame([
        local_event("Send", 0, cx.ELEM_SEND, "A", key="k"),
        local_event("Receive", 1, cx.ELEM_RECEIVE, "B", key="k"),
        local_event("Receive multicast", 2, cx.ELEM_RECEIVE, "C", key="k"),
    ])
    return SourceLog("multicast", [], local=local)


def reused_key() -> SourceLog:
    """Two sends reuse one identifier towards different receivers."""
    local = pd.DataFrame([
        local_event("Send", 0, cx.ELEM_SEND, "A", key="k", to="B"),
        local_event("Send again", 1, cx.ELEM_SEND, "A", key="k", to="C"),
        local_event("Receive", 2, cx.ELEM_RECEIVE, "B", key="k", frm="A"),
    ])
    return SourceLog("reused", [], local=local)


def unkeyed() -> SourceLog:
    local = pd.DataFrame([
        local_event("Send", 0, cx.ELEM_SEND, "A", to="B"),
        local_event("Work", 1, cx.ELEM_TASK, "B"),
        local_event("Receive", 2, cx.ELEM_RECEIVE, "B", frm="A"),
    ])
    return SourceLog("unkeyed", [], local=local)


def complete_with_choreography_only_parts() -> SourceLog:
    """The exchange events name a participant (E), a case (c2), explicit roles
    (F), and response endpoints (G) that no local event records."""
    log = two_way_complete()
    log.exchange += [
        ExchangeEvent("c1", "Notify", T("2020-01-01 10:04"), 1, "A", ("E",), "n",
                      initiators=("F",), response_key="nr", response_receivers=("G",)),
        ExchangeEvent("c2", "Ask", T("2020-01-01 11:00"), 2, "A", ("B",), "q9",
                      attributes={"channel": "web"}),
    ]
    return log


def task_endpoint() -> SourceLog:
    """A task event that records an endpoint: M1-M8 create the participant,
    which no relation reaches and M8 does not preserve."""
    local = pd.DataFrame([local_event("Work", 0, cx.ELEM_TASK, "A", to="Z"),
                          local_event("Send", 1, cx.ELEM_SEND, "A", key="k", to="B")])
    return SourceLog("task_endpoint", [], local=local)


LOGS = [two_way_complete, multicast, reused_key, unkeyed,
        complete_with_choreography_only_parts, task_endpoint]


@pytest.mark.parametrize("log", LOGS, ids=lambda f: f.__name__)
def test_alpha_c_equals_infsys(log):
    res = u.map_log(log())
    assert_same_as_infsys(export_infsys.of(res), res.infsys)


@pytest.mark.parametrize("log", LOGS, ids=lambda f: f.__name__)
def test_alpha_c_reads_only_the_core(log):
    res = u.map_log(log())
    without = export_infsys.of(dataclasses.replace(res, infsys=None))
    assert_same_as_infsys(without, res.infsys)


@pytest.mark.parametrize("log", LOGS, ids=lambda f: f.__name__)
def test_alpha_c_removes_the_choreography_part(log):
    view = export_infsys.of(u.map_log(log()))
    assert not set(view.relations_df[cx.COL_QUALIFIER]) & CORE_ONLY_QUALIFIERS
    assert not set(view.o2o_df[cx.COL_QUALIFIER]) & CORE_ONLY_QUALIFIERS
    assert not set(view.objects_df[cx.COL_OTYPE]) & {u.OT_CHC, u.OT_SUB}
    assert not any(o.startswith(("message::", "chc::", "sub::"))
                   for o in view.objects_df[cx.COL_OID])
    assert not any(e.startswith("x::") for e in view.events_df[cx.COL_EID])


def test_endpoints_are_per_observation():
    res = u.map_log(multicast())
    view = export_infsys.of(res)
    o2o = {(a, b, q) for a, b, q in view.o2o_df.itertuples(index=False)}
    ev = view.events_df.set_index(cx.COL_ACTIVITY)[cx.COL_EID]
    send, recv = f"msg::{ev['Send']}", f"msg::{ev['Receive']}"
    # The logical message aggregates both receivers ...
    assert {("message::c1::k", "part::B", u.Q_TARGET),
            ("message::c1::k", "part::C", u.Q_TARGET)} <= set(
        res.o2o_df.itertuples(index=False, name=None))
    # ... but the send records none, and each receive only itself.
    assert (send, "part::A", cx.Q_FROM) in o2o
    assert not any(a == send and q == cx.Q_TO for a, _, q in o2o)
    assert (recv, "part::B", cx.Q_TO) in o2o
    assert not any(a == recv and q == cx.Q_FROM for a, _, q in o2o)


def test_reused_key_gives_one_observation_per_send():
    view = export_infsys.of(u.map_log(reused_key()))
    msgs = view.objects_df[view.objects_df[cx.COL_OTYPE] == cx.OT_MESSAGE]
    assert sorted(msgs["receiver"]) == ["B", "B", "C"]
    assert len(msgs) == 3


def test_choreography_only_log_gives_an_empty_view():
    x = [ExchangeEvent("c1", "S", T("2020-01-01 10:00"), 0, "A", ("B",), "k")]
    view = export_infsys.of(u.map_log(SourceLog("chl", [], exchange=x)))
    assert all(getattr(view, t).empty for t in TABLES)
    assert view.stats["n_events"] == 0 and len(view.participant_types) == 0


@pytest.mark.parametrize("log", [two_way_complete, multicast, task_endpoint,
                                 complete_with_choreography_only_parts],
                         ids=lambda f: f.__name__)
def test_sqlite_equals_the_infsys_export(log, tmp_path):
    from common import read_sqlite
    res = u.map_log(log())
    export_infsys.write_sqlite(export_infsys.of(res), str(tmp_path / "view.sqlite"))
    ref = res.infsys
    rel = cx._add_export_reachability_witnesses(ref.objects_df, ref.relations_df, ref.o2o_df)
    cx.write_ocel2_sqlite(cx.build_ocel_object(ref.events_df, ref.objects_df, rel, ref.o2o_df),
                          str(tmp_path / "ref.sqlite"))
    assert read_sqlite(tmp_path / "view.sqlite") == read_sqlite(tmp_path / "ref.sqlite")
