"""Checks of the runner that do not run any log through OCPA or the learner.

Needs the prediction environment (`.venv-predict`, with OCPA and the InfSys evaluation);
skipped elsewhere.

Run: .venv-predict/bin/python -m pytest source/prediction/tests
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

rq3_pipeline = pytest.importorskip("evaluation.rq3_pipeline")

import choreo_view as cv  # noqa: E402
import run_prediction as rp  # noqa: E402
import tasks_chor as tc  # noqa: E402
from test_choreo_view import view  # noqa: E402,F401  (fixture: P, Q, R; activities A-D)

INVOLVEMENT_TASKS = ["NE-NMPa", "NV-NMPa", "NV-PaT", "OB-P"]


def test_plan_with_both_parameters_runs_every_restated_task(view):
    runs, skipped = rp.plan(view, "Q", "C")
    assert skipped == []
    assert [r.view for r in runs] == [tc.SENDER, tc.INVOLVEMENT]
    assert sorted(runs[1].tasks) == INVOLVEMENT_TASKS
    assert sorted(runs[0].tasks + runs[1].tasks) == sorted(tc.RESTATED)
    # The involvement run uses the view of the given participant.
    assert [e.actor for e in runs[1].log.executions[0].events] == ["Q", "Q", "P", "R"]


def test_plan_without_parameters_skips_the_parameterized_tasks(view):
    runs, skipped = rp.plan(view, None, None)
    assert [r.view for r in runs] == [tc.SENDER]
    assert sorted(skipped) == sorted(INVOLVEMENT_TASKS + ["OB-M"])
    assert "OB-M" not in runs[0].tasks


def test_plan_rejects_parameters_absent_from_the_log(view):
    with pytest.raises(ValueError, match="participant 'Z'"):
        rp.plan(view, "Z", None)
    with pytest.raises(ValueError, match="activity 'Z'"):
        rp.plan(view, None, "Z")


def test_label_reader_replaces_and_restores_the_infsys_reader():
    original = rq3_pipeline.read_ocel2_labels
    sentinel = object()
    with rp._label_reader(sentinel):
        assert rq3_pipeline.read_ocel2_labels("any.sqlite", None, ocpa_ocel=None) is sentinel
    assert rq3_pipeline.read_ocel2_labels is original


def test_label_reader_restores_on_error():
    original = rq3_pipeline.read_ocel2_labels
    with pytest.raises(RuntimeError):
        with rp._label_reader(object()):
            raise RuntimeError
    assert rq3_pipeline.read_ocel2_labels is original


def test_config_uses_choreography_case_as_leading_type():
    cfg = rp.config(["OB-P", "OB-M"], participant="P", activity="A")
    assert cfg.schema.ot_cc == "ChoreographyCase"
    assert cfg.schema.ot_message == "Message"
    assert cfg.predictor == "random_forest" and cfg.n_folds == 5
    assert cfg.obp_target_participant == "P" and cfg.obm_target_activity == "A"
    assert cfg.rq3_tasks == ["OB-P", "OB-M"]
    assert Path(cfg.folds_dir) == rp.FOLDS


def test_markdown_formats_rows():
    rows = [{"dataset": "x", "task": "NE-NEPr", "kind": "direct", "samples": 10,
             "n_labels": 3, "degenerate": False, "metric_name": "f1_macro",
             "metric_mean": 0.5, "metric_sd": 0.1, "baseline_mean": 0.2, "folds": 5},
            {"dataset": "x", "task": "OB-P", "kind": "redefined", "samples": 0,
             "note": "skipped: no participant given"}]
    md = rp.markdown(rows)
    assert "| x | NE-NEPr | direct |  | 10 | 3 | False | f1_macro | 0.500 | 0.100 | 0.200 | 5 |  |" in md
    assert "| x | OB-P | redefined |  | 0 | – | – | – | – | – | – | – | skipped: no participant given |" in md


def _e2o(path):
    import sqlite3
    con = sqlite3.connect(str(path))
    try:
        return con.execute("select ocel_event_id, ocel_object_id, ocel_qualifier "
                           "from event_object").fetchall()
    finally:
        con.close()


def test_role_relations_are_filtered_in_a_copy(tmp_path):
    from test_choreo_view import _write_ocel, T0
    path = tmp_path / "log.sqlite"
    events = [(f"x::c{i}::0", "A", T0) for i in (1, 2)]
    objects = [("part::P", "PartyP", {"name": "P"}), ("part::Q", "PartyQ", {"name": "Q"}),
               ("chc::c1", "ChoreographyCase", {}), ("chc::c2", "ChoreographyCase", {})]
    e2o = [(f"x::c{i}::0", f"chc::c{i}", "in_choreography") for i in (1, 2)]
    e2o += [(f"x::c{i}::0", "part::P", "initiator") for i in (1, 2)]
    e2o += [(f"x::c{i}::0", "part::Q", "participant") for i in (1, 2)]
    _write_ocel(path, events, objects, e2o, [])
    before = _e2o(path)
    with rp.without_role_relations(path) as copy:
        rows = _e2o(copy)
    assert _e2o(path) == before and not copy.exists()
    assert {r for r in rows if r[2] == "in_choreography"} == set(e2o[:2])
    roles = [r for r in rows if r[2] in ("initiator", "participant")]
    assert sorted(r[1] for r in roles) == ["part::P", "part::Q"]     # one witness per object


HC_CHL = Path(__file__).resolve().parents[3] / "data" / "healthcare" / "mapped" / "healthcare_chl.sqlite"


@pytest.mark.skipif(not HC_CHL.exists(), reason="run source/mapping/map_all.py first")
def test_healthcare_executions_with_and_without_the_role_filter():
    """With the task roles, every execution reaches every task through the shared
    participants; without them, 100 executions of 5.5 tasks on average."""
    from features.io_ocel import load_ocpa_ocel
    with rp.without_role_relations(HC_CHL) as copy:
        ocel = load_ocpa_ocel(rp.CHOREOGRAPHY_SCHEMA, str(copy))
    sizes = [len(x) for x in ocel.process_executions]
    assert len(sizes) == 100 and sum(sizes) == 550 and max(sizes) < 550
    unfiltered = load_ocpa_ocel(rp.CHOREOGRAPHY_SCHEMA, str(HC_CHL))
    assert {len(x) for x in unfiltered.process_executions} == {550}
