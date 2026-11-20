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


def _write(tmp_path, m):
    p = tmp_path / "mutated.json"
    p.write_text(json.dumps(m))
    return p


@pytest.mark.parametrize("role,u8_count", [
    ("choreo:participant", "participants_not_request_receivers"),
    ("choreo:initiator", "initiators_not_request_senders"),
])
def test_disagreeing_roles_survive_the_roundtrip(tmp_path, role, u8_count):
    """Proposition 2 without C1/C9/C10: a task role that its request does not
    name survives eta_H(mu_U(iota_H(H))), and U8 reports it."""
    from e2b_roundtrip import evaluate
    m = copy.deepcopy(load(HC))
    r = first(m["events"][0]["relationships"], lambda r: r["qualifier"] == role)
    r["objectId"] = "Hospital" if r["objectId"] != "Hospital" else "Laboratory"
    out = evaluate(_write(tmp_path, m))
    assert out["passed"] and out["equivalent"] and not any(out["iota_H_diagnostics"].values())
    assert out["U8"][u8_count] == 1
    assert sum(v for k, v in out["U8"].items() if k != "tasks") == 1


def test_a_response_not_reversing_the_request_survives_the_roundtrip(tmp_path):
    from e2b_roundtrip import evaluate
    h = load(ETH)
    m = copy.deepcopy(h)
    objects = {o["id"]: o for o in m["objects"]}
    two_way = first(m["events"], lambda e: sum(r["qualifier"] == "choreo:message"
                                               for r in e["relationships"]) == 2)
    initiator = first(two_way["relationships"],
                      lambda r: r["qualifier"] == "choreo:initiator")["objectId"]
    resp = first((objects[r["objectId"]] for r in two_way["relationships"]
                  if r["qualifier"] == "choreo:message"),
                 lambda o: initiator not in {x["objectId"] for x in o["relationships"]
                                             if x["qualifier"] == "choreo:source"})
    other = first(m["objects"], lambda o: o["id"] != initiator and o["type"] not in (
        "choreographyInstance", "subchoreographyInstance") and not o.get("relationships")
        and any(o["id"] == r["objectId"] for e in m["events"] for r in e["relationships"]
                if r["qualifier"] in ("choreo:initiator", "choreo:participant")))
    first(resp["relationships"], lambda x: x["qualifier"] == "choreo:target")["objectId"] = other["id"]
    out = evaluate(_write(tmp_path, m))
    assert out["equivalent"] and not any(out["iota_H_diagnostics"].values())
    assert out["U8"]["responses_not_reversing_the_roles"] >= 1
    assert not compare(m, h)["equivalent"]       # the mutation is visible to the comparison


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
