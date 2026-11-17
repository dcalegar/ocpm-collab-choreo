"""Sensitivity of the E2 comparison and the diagnostics of iota_H.

A comparison that always says "equivalent" would make E2 and E2b vacuous, so
each test perturbs one piece of choreography information of a reference log of
Hobeck et al. and checks that the comparison detects it.

Run from the repository root: `.venv/bin/python -m pytest source/experiments/tests`
(needs `OCELCHOR` only for the mapping's Ethereum reader, not here).
"""

from __future__ import annotations

import copy
import json
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.disable(logging.WARNING)

from common import DATA  # noqa: E402
from e2_hobeck import compare  # noqa: E402
import export_hobeck  # noqa: E402
from index import index_of  # noqa: E402
from reverse_hobeck import read_hobeck_ocel  # noqa: E402
import unified as u  # noqa: E402

HC = DATA / "healthcare" / "hobeck" / "healthcare_uniqueInteraction_ocel.json"
ETH = DATA / "eth-tornadocash-governance" / "hobeck" / "0x5e_cd49912_ocel.json"


def load(p):
    if not p.is_file():
        pytest.skip(f"{p} not available")
    return json.load(open(p, encoding="utf-8"))


def first(d, pred):
    return next(x for x in d if pred(x))


def test_identity_is_equivalent():
    h = load(HC)
    assert compare(copy.deepcopy(h), h)["equivalent"]


def test_changed_message_target_is_detected():
    h = load(HC)
    m = copy.deepcopy(h)
    msg = first(m["objects"], lambda o: any(r["qualifier"] == "choreo:target"
                                             for r in o.get("relationships", [])))
    r = first(msg["relationships"], lambda r: r["qualifier"] == "choreo:target")
    r["objectId"] = "Laboratory" if r["objectId"] != "Laboratory" else "Hospital"
    assert not compare(m, h)["equivalent"]


def test_changed_initiator_is_detected():
    h = load(HC)
    m = copy.deepcopy(h)
    r = first(m["events"][0]["relationships"], lambda r: r["qualifier"] == "choreo:initiator")
    r["objectId"] = "Hospital"
    assert not compare(m, h)["equivalent"]


def test_split_message_sharing_is_detected():
    h = load(DATA / "real2" / "hobeck" / "real2_uniqueInteraction_ocel.json")
    shared = {}
    for e in h["events"]:
        for r in e["relationships"]:
            if r["qualifier"] == "choreo:message":
                shared.setdefault(r["objectId"], []).append(e["id"])
    mid, events = next((k, v) for k, v in shared.items() if len(v) > 1)
    m = copy.deepcopy(h)
    clone = copy.deepcopy(first(m["objects"], lambda o: o["id"] == mid))
    clone["id"] = mid + "::copy"
    m["objects"].append(clone)
    ev = first(m["events"], lambda e: e["id"] == events[-1])
    first(ev["relationships"], lambda r: r["objectId"] == mid)["objectId"] = clone["id"]
    assert not compare(m, h)["message_sharing_equal"]


def test_changed_content_and_scope_are_detected():
    h = load(ETH)
    m = copy.deepcopy(h)
    msg = first(m["objects"], lambda o: o.get("attributes") and o["type"].endswith("call"))
    msg["attributes"][0]["value"] = "changed"
    assert not compare(m, h)["equivalent"]
    m = copy.deepcopy(h)
    ev = first(m["events"], lambda e: any(r["qualifier"] == "choreo:contained-by"
                                          for r in e["relationships"]))
    ev["relationships"] = [r for r in ev["relationships"] if r["qualifier"] != "choreo:contained-by"]
    assert not compare(m, h)["equivalent"]


def test_roundtrip_of_a_reference_is_equivalent():
    src, diag = read_hobeck_ocel(ETH)
    exported = export_hobeck.export(index_of(u.map_log(src)))
    assert compare(exported, ETH)["equivalent"] and not any(diag.values())


def test_iota_h_reports_disagreeing_roles(tmp_path):
    h = load(HC)
    m = copy.deepcopy(h)
    r = first(m["events"][0]["relationships"], lambda r: r["qualifier"] == "choreo:participant")
    r["objectId"] = "Hospital"
    p = tmp_path / "mutated.json"
    p.write_text(json.dumps(m))
    _, diag = read_hobeck_ocel(p)
    assert diag.get("tasks_whose_roles_differ_from_the_request") == 1


def test_e2b_fails_on_iota_h_diagnostics_alone(tmp_path):
    """E2b must fail on an iota_H diagnostic even when every other condition
    holds. A message object with endpoints that no task uses is ignored by
    iota_H (and absent from the round trip, which the comparison does not see
    because it reads messages through tasks), so the round trip stays
    equivalent and only the diagnostic can make E2b fail."""
    from e2b_roundtrip import evaluate
    h = load(HC)
    assert evaluate(HC)["passed"]
    m = copy.deepcopy(h)
    m["objects"].append({"id": "message:unused", "type": "disease", "relationships": [
        {"objectId": "Patient", "qualifier": "choreo:source"},
        {"objectId": "Gynecologist", "qualifier": "choreo:target"}]})
    p = tmp_path / "mutated.json"
    p.write_text(json.dumps(m))
    out = evaluate(p)
    assert out["equivalent"] and out["structural_criteria_hold"] and out["p1_7_holds"]
    assert out["no_conflicting_values"]
    assert out["iota_H_diagnostics"]["message_objects_without_task_ignored"] == 1
    assert not out["no_iota_H_diagnostics"] and not out["passed"]
