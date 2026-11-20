#!/usr/bin/env python3
"""E1: the unified mapping reproduces InfSys (conservativity).

For each log that InfSys maps (Artificial1, Artificial5, Healthcare, Real4, and
BPIC 2013), the collaboration view alpha_C(mu_U(L)) that the mapping writes
(`<out>_infsys.sqlite`, see `export_infsys.py`) must equal the OCEL that InfSys
published (`data/<n>/infsys/*.sqlite`). It is checked on the collaboration
profile (CL) and, where a ChL exists, on the complete profile (CL + ChL), so
the additions of M9-M13 are shown not to change the InfSys part. alpha_C
rebuilds the per-event messages that the core omits, so the comparison reads
the view as written, without any projection.

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
            cases.append((n, p, DATA / n / "mapped" / f"{n}_{p}_infsys.sqlite", ref))
    cases.append(("bpic2013", "cl", DATA / "bpic2013" / "mapped" / "bpic2013_cl_infsys.sqlite",
                  DATA / "bpic2013" / "infsys" / "BPI2013_incidents_collaborative.sqlite"))
    results, rows = {}, []
    for n, p, ours, ref in cases:
        r = compare(read_sqlite(require(ours)), read_sqlite(require(ref)))
        results[f"{n}_{p}"] = r
        rows.append([n, p, "yes" if r["equal"] else "**no**",
                     "{}/{}".format(*r["events"]), "{}/{}".format(*r["objects"]),
                     "{}/{}".format(*r["e2o"]), "{}/{}".format(*r["o2o"]),
                     r["events_differing"], r["events_with_trailing_space_only"]])
    md_note = ("\nEqual: after the documented normalization (trailing non-breaking space in two "
               "Real4 activity names of the InfSys copy).\n")
    md = ("# E1: reproduction of InfSys (alpha_C(mu_U(L)) = InfSys OCEL)\n\n"
          + md_table(["Log", "Profile", "Equal", "Events (ours/ref)", "Objects", "E2O", "O2O",
                      "Events differing", "Only trailing space"], rows) + "\n" + md_note)
    write_results("e1_infsys", results, md)
    return 0 if all(r["equal"] for r in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
