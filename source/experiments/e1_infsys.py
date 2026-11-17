#!/usr/bin/env python3
"""E1: the unified mapping reproduces InfSys (conservativity).

For each log that InfSys maps (Artificial1, Artificial5, Healthcare, Real4, and
BPIC 2013), the collaboration projection pi_C of the unified output must equal
the OCEL that InfSys published (`data/<n>/infsys/*.sqlite`). It is checked on
the collaboration profile (CL) and, where a ChL exists, on the complete profile
(CL + ChL), so the additions of M9-M13 are shown not to change the InfSys part.

pi_C removes, by structure only:
- the events without `in_collaboration` (exchange events, M9);
- the objects of the types added by M10-M13;
- the E2O relations with a qualifier added by M12-M13 or to a removed object or
  from a removed event, and the O2O relations that touch a removed object.

Both files are compared as sets: events (id, type, time, attributes), objects
(id, type, attributes), E2O, and O2O, read from the SQLite files. The only
normalization is the documented one: the InfSys copy of Real4 drops a trailing
non-breaking space in two activity names, so event types (and the
`ocel:activity` attribute that pm4py repeats) are compared without trailing
whitespace, and the affected events are counted.
"""

from __future__ import annotations

from typing import Any, Dict

from common import DATA, INFSYS_LOGS, md_table, read_sqlite, require, write_results
import unified as u

NEW_QUALIFIERS = {u.Q_IN_CHOREOGRAPHY, u.Q_REQUEST, u.Q_RESPONSE, u.Q_CONTAINED_BY}


def project(log: Dict[str, Any]) -> Dict[str, Any]:
    local = {e for e, _, q in log["e2o"] if q == "in_collaboration"}
    keep_o = {o for o, r in log["objects"].items() if r["type"] not in u.NEW_OBJECT_TYPES}
    return {
        "events": {e: r for e, r in log["events"].items() if e in local},
        "objects": {o: r for o, r in log["objects"].items() if o in keep_o},
        "e2o": {(e, o, q) for e, o, q in log["e2o"]
                if e in local and o in keep_o and q not in NEW_QUALIFIERS},
        "o2o": {(a, b, q) for a, b, q in log["o2o"] if a in keep_o and b in keep_o},
    }


def compare(ours: Dict[str, Any], ref: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    renamed = 0
    ev_diff = []
    for e in set(ours["events"]) | set(ref["events"]):
        a, b = ours["events"].get(e), ref["events"].get(e)
        if a is None or b is None:
            ev_diff.append(e)
            continue
        if a["type"] != b["type"]:
            if a["type"].rstrip() == b["type"].rstrip():
                renamed += 1
            else:
                ev_diff.append(e)
                continue
        strip = lambda at: {k: (v.rstrip() if k == "ocel:activity" else v) for k, v in at.items()}
        if a.get("time") != b.get("time") or strip(a["attrs"]) != strip(b["attrs"]):
            ev_diff.append(e)
    ob_diff = [o for o in set(ours["objects"]) | set(ref["objects"])
               if ours["objects"].get(o) != ref["objects"].get(o)]
    out["events"] = [len(ours["events"]), len(ref["events"])]
    out["objects"] = [len(ours["objects"]), len(ref["objects"])]
    out["e2o"] = [len(ours["e2o"]), len(ref["e2o"])]
    out["o2o"] = [len(ours["o2o"]), len(ref["o2o"])]
    out["events_differing"] = len(ev_diff)
    out["events_with_trailing_space_only"] = renamed
    out["objects_differing"] = len(ob_diff)
    out["e2o_differing"] = len(ours["e2o"] ^ ref["e2o"])
    out["o2o_differing"] = len(ours["o2o"] ^ ref["o2o"])
    out["examples"] = sorted(ev_diff)[:3] + sorted(ob_diff)[:3] + \
        [str(x) for x in sorted(ours["e2o"] ^ ref["e2o"])[:3]] + \
        [str(x) for x in sorted(ours["o2o"] ^ ref["o2o"])[:3]]
    out["equal"] = not (ev_diff or ob_diff or out["e2o_differing"] or out["o2o_differing"])
    out["equal_without_normalization"] = out["equal"] and renamed == 0
    return out


def main() -> int:
    cases = []
    for n in INFSYS_LOGS:
        ref = DATA / n / "infsys" / f"collectivelog_{n}_collab.sqlite"
        for p in ("cl", "complete"):
            cases.append((n, p, DATA / n / "mapped" / f"{n}_{p}.sqlite", ref))
    cases.append(("bpic2013", "cl", DATA / "bpic2013" / "mapped" / "bpic2013_cl.sqlite",
                  DATA / "bpic2013" / "infsys" / "BPI2013_incidents_collaborative.sqlite"))
    results, rows = {}, []
    for n, p, ours, ref in cases:
        r = compare(project(read_sqlite(require(ours))), read_sqlite(require(ref)))
        results[f"{n}_{p}"] = r
        rows.append([n, p, "yes" if r["equal"] else "**no**",
                     "{}/{}".format(*r["events"]), "{}/{}".format(*r["objects"]),
                     "{}/{}".format(*r["e2o"]), "{}/{}".format(*r["o2o"]),
                     r["events_differing"], r["events_with_trailing_space_only"]])
    md_note = ("\nEqual: after the documented normalization (trailing non-breaking space in two "
               "Real4 activity names of the InfSys copy).\n")
    md = ("# E1: reproduction of InfSys (pi_C(mu+(L)) = InfSys OCEL)\n\n"
          + md_table(["Log", "Profile", "Equal", "Events (ours/ref)", "Objects", "E2O", "O2O",
                      "Events differing", "Only trailing space"], rows) + "\n" + md_note)
    write_results("e1_infsys", results, md)
    return 0 if all(r["equal"] for r in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
