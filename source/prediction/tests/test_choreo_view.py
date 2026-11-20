"""Minimal checks of the choreography-view adapter and of the restated tasks.

- `read_choreography` reads the stored task roles and request endpoints of the
  representation, independently of each other, on a synthetic OCEL 2.0 SQLite log.
- The InfSys label functions, run unchanged on the adapted views, give the hand-computed
  targets of the ten restated tasks.
- The involvement view computes exactly "a task involves p", and the unconditional
  collapses of the paper hold.
- On the mapped ChL of Artificial5 (skipped if `map_all.py` has not run), the adapter
  agrees with the mapping's own index (`index.Index.roles`, `Index.endpoints`).

Run: .venv/bin/python -m pytest source/prediction/tests
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import choreo_view as cv  # noqa: E402
import tasks_chor as tc  # noqa: E402
from tasks.catalog import TASKS  # noqa: E402  (InfSys)
from tasks.labels import BOTTOM, build_context, compute_label_rows  # noqa: E402

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
REPO = Path(__file__).resolve().parents[3]
A5_CHL = REPO / "data" / "artificial5" / "mapped" / "artificial5_chl.sqlite"


# ---- synthetic OCEL 2.0 SQLite -------------------------------------------------
def _write_ocel(path: Path, events, objects, e2o, o2o) -> None:
    """events: [(id, type, time)]; objects: [(id, type, {attr: value})]."""
    con = sqlite3.connect(str(path))
    con.execute("create table event (ocel_id text, ocel_type text)")
    con.execute("create table object (ocel_id text, ocel_type text)")
    con.execute("create table event_map_type (ocel_type text, ocel_type_map text)")
    con.execute("create table object_map_type (ocel_type text, ocel_type_map text)")
    con.execute("create table event_object (ocel_event_id text, ocel_object_id text, ocel_qualifier text)")
    con.execute("create table object_object (ocel_source_id text, ocel_target_id text, ocel_qualifier text)")
    for et in sorted({t for _, t, _ in events}):
        con.execute("insert into event_map_type values (?, ?)", (et, et))
        con.execute(f'create table "event_{et}" (ocel_id text, ocel_time text)')
    for eid, et, t in events:
        con.execute("insert into event values (?, ?)", (eid, et))
        con.execute(f'insert into "event_{et}" values (?, ?)', (eid, t.isoformat(sep=" ")))
    for ot in sorted({t for _, t, _ in objects}):
        con.execute("insert into object_map_type values (?, ?)", (ot, ot))
        con.execute(f'create table "object_{ot}" (ocel_id text, name text)')
    for oid, ot, attrs in objects:
        con.execute("insert into object values (?, ?)", (oid, ot))
        con.execute(f'insert into "object_{ot}" values (?, ?)', (oid, attrs.get("name")))
    con.executemany("insert into event_object values (?, ?, ?)", e2o)
    con.executemany("insert into object_object values (?, ?, ?)", o2o)
    con.commit()
    con.close()


def test_read_choreography_roles_and_endpoints(tmp_path):
    """Roles from initiator/participant, request endpoints from source/target, read
    independently (task C disagrees on purpose); a task without receiver; local
    events, even with send/receive relations, are not tasks."""
    path = tmp_path / "log.sqlite"
    parts = [(f"part::{p}", f"Party{p}", {"name": p}) for p in "PQR"]
    events = [("x::c1::0", "A", T0),
              ("e::c1::1", "Local", T0 + timedelta(seconds=5)),   # receive, no request
              ("x::c1::2", "B", T0 + timedelta(seconds=10)),
              ("x::c1::3", "C", T0 + timedelta(seconds=20))]
    objects = parts + [("chc::c1", "ChoreographyCase", {}),
                       ("message::c1::a", "Message", {}),
                       ("message::c1::b", "Message", {}),
                       ("message::c1::c", "Message", {})]
    e2o = [(e, "chc::c1", "in_choreography") for e in ("x::c1::0", "x::c1::2", "x::c1::3")]
    e2o += [("x::c1::0", "message::c1::a", "request"), ("x::c1::2", "message::c1::b", "request"),
            ("x::c1::3", "message::c1::c", "request"),
            ("e::c1::1", "message::c1::a", "receive"),
            ("x::c1::0", "part::P", "initiator"), ("x::c1::0", "part::Q", "participant"),
            ("x::c1::2", "part::Q", "initiator"),
            ("x::c1::3", "part::R", "initiator"), ("x::c1::3", "part::P", "participant")]
    o2o = [("message::c1::a", "part::P", "source"), ("message::c1::a", "part::Q", "target"),
           ("message::c1::b", "part::Q", "source"),                 # no receiver recorded
           ("message::c1::c", "part::Q", "source"), ("message::c1::c", "part::P", "target")]
    _write_ocel(path, events, objects, e2o, o2o)

    view = cv.read_choreography(path)
    assert list(view.cases) == ["chc::c1"]
    got = [(t.event_id, t.activity, t.initiator, t.participants, t.message_sender,
            t.message_receivers) for t in view.cases["chc::c1"]]
    assert got == [("x::c1::0", "A", "P", ("Q",), "P", ("Q",)),
                   ("x::c1::2", "B", "Q", (), "Q", ()),
                   ("x::c1::3", "C", "R", ("P",), "Q", ("P",))]
    assert view.participants() == ["P", "Q", "R"]


# ---- hand-computed targets ----------------------------------------------------
def _task(i, act, sender, receivers, secs):
    return cv.ChoreographyTask(event_id=f"x::c1::{i}", case_id="chc::c1", activity=act,
                               timestamp=T0 + timedelta(seconds=secs),
                               message=f"message::c1::{i}", initiator=sender,
                               participants=tuple(receivers), message_sender=sender,
                               message_receivers=tuple(receivers))


@pytest.fixture
def view():
    # A: P->Q at 0; B: Q->R at 10; C: P->(none) at 30; D: R->P at 60.
    return cv.ChoreographyView({"chc::c1": [
        _task(0, "A", "P", ["Q"], 0), _task(1, "B", "Q", ["R"], 10),
        _task(2, "C", "P", [], 30), _task(3, "D", "R", ["P"], 60)]})


def _by_k(view, key, param=None):
    return {k: y for _c, _e, k, y in tc.label_rows(view, key, param, drop_bottom=False)}


@pytest.mark.parametrize("key,param,expected", [
    # k = prefix length (cut after the k-th task); k in 1..3.
    ("NE-NEPr", None, {1: "B", 2: "C", 3: "D"}),
    ("NV-TNE", None, {1: 10.0, 2: 20.0, 3: 30.0}),
    ("OB-M", "C", {1: True, 2: True, 3: False}),
    ("NE-NPaA", None, {1: "Q", 2: "P", 3: "R"}),
    ("NV-NMPr", None, {1: 3, 2: 2, 3: 1}),
    ("NV-PrT", None, {1: 60.0, 2: 50.0, 3: 30.0}),
    ("NE-NMPa", "R", {1: "B", 2: "D", 3: "D"}),
    ("NE-NMPa", "Q", {1: "B", 2: BOTTOM, 3: BOTTOM}),
    ("NV-NMPa", "P", {1: 2, 2: 2, 3: 1}),
    ("NV-NMPa", "Q", {1: 1, 2: 0, 3: 0}),
    ("NV-PaT", "R", {1: 60.0, 2: 50.0, 3: 30.0}),
    ("NV-PaT", "Q", {1: 10.0, 2: 0.0, 3: 0.0}),
    ("OB-P", "Q", {1: True, 2: False, 3: False}),
    ("OB-P", "R", {1: True, 2: True, 3: True}),
])
def test_restated_labels(view, key, param, expected):
    assert _by_k(view, key, param) == expected


def test_involvement_view_is_involvement(view):
    """In the involvement view of p, actor == p exactly on the tasks that involve p."""
    for p in view.participants():
        log = cv.involvement_view(view, p)
        for ex in log:
            tasks = view.cases[ex.case_id]
            assert [e.actor == p for e in ex.events] == [t.involves(p) for t in tasks]


def test_unconditional_collapses(view):
    """Send directions of NE-NPaM and NV-TNM coincide with NE-NPaA and NV-TNE."""
    log = cv.sender_view(view)
    ctx = build_context(log)
    rows = lambda key, p=None: [r[3] for r in compute_label_rows(log, TASKS[key], p, ctx, False)]
    assert rows("NE-NPaM", "send") == rows("NE-NPaA")
    assert rows("NV-TNM", "send") == rows("NV-TNE")


# ---- real mapped log ------------------------------------------------------------
def _mapping_env() -> bool:
    """The mapping needs pm4py 2.7; the prediction environment has OCPA's 2.2.32."""
    from importlib.metadata import PackageNotFoundError, version
    try:
        return tuple(int(x) for x in version("pm4py").split(".")[:2]) >= (2, 7)
    except PackageNotFoundError:
        return False


@pytest.mark.skipif(not A5_CHL.exists(), reason="run source/mapping/map_all.py first")
@pytest.mark.skipif(not _mapping_env(), reason="needs the mapping environment (.venv)")
def test_artificial5_chl_matches_mapping_index():
    view = cv.read_choreography(A5_CHL)
    assert len(view.cases) == 100 and len(view.tasks) == 530
    assert sum(1 for t in view.tasks if not t.participants) == 44

    mapping = REPO / "source" / "mapping"
    sys.path.insert(0, str(mapping))
    sources = pytest.importorskip("sources")
    u = pytest.importorskip("unified")
    from index import index_of
    chl = REPO / "data" / "artificial5" / "pena" / "collectivelog_artificial5_chor.xes"
    if not chl.exists():
        chl = next((REPO / "data" / "artificial5" / "pena").glob("*_chor.xes"))
    ix = index_of(u.map_log(sources.read_chl(str(chl), sources.MSG_KEY)))
    for t in view.tasks:
        initiators, participants = ix.roles(t.event_id)
        senders, receivers = ix.endpoints(t.message)
        assert [ix.participant_name(p) for p in initiators] == [t.initiator]
        assert sorted(ix.participant_name(p) for p in participants) == list(t.participants)
        assert [ix.participant_name(p) for p in senders] == [t.message_sender]
        assert sorted(ix.participant_name(p) for p in receivers) == list(t.message_receivers)

    # Every restated task yields labels on the real log.
    p = "PartyA"
    for key in tc.RESTATED:
        param = p if tc.RESTATED[key].view == tc.INVOLVEMENT else (
            "Activity E" if key == "OB-M" else None)
        assert tc.label_rows(view, key, param), key
